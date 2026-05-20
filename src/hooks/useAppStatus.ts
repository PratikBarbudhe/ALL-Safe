import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ApiError,
  checkBackendHealth,
  fetchAppPerformance,
  fetchAppStatus,
  restartAppMonitors,
  setBackgroundMode,
  setWindowVisibility,
  shutdownApp,
  type AppHealthState,
  type AppPerformance,
  type AppStatus,
} from '@/lib/api';

const STATUS_POLL_MS = 8000;
const RECONNECT_INTERVAL_MS = 3000;
const MAX_RECONNECT_ATTEMPTS = 20;

export function useAppStatus() {
  const [healthState, setHealthState] = useState<AppHealthState>('reconnecting');
  const [appStatus, setAppStatus] = useState<AppStatus | null>(null);
  const [performance, setPerformance] = useState<AppPerformance | null>(null);
  const [isStartupLoading, setIsStartupLoading] = useState(true);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  const mapHealthState = useCallback(
    (online: boolean, status: AppStatus | null): AppHealthState => {
      if (!online) return 'offline';
      if (!status) return 'reconnecting';
      if (status.background_mode && !status.window_visible) return 'background';
      if (status.status === 'healthy') return 'healthy';
      if (status.status === 'degraded' || status.status === 'background') return 'degraded';
      if (status.status === 'critical') return 'degraded';
      return 'healthy';
    },
    [],
  );

  const pollStatus = useCallback(async (options?: { silent?: boolean }) => {
    const silent = options?.silent ?? false;
    if (!silent) setError(null);

    const online = await checkBackendHealth();
    if (!online) {
      setHealthState('offline');
      setReconnectAttempt((n) => n + 1);
      if (!silent) {
        setError('Backend API unreachable — retrying connection');
      }
      return false;
    }

    try {
      const [status, perf] = await Promise.all([
        fetchAppStatus(),
        fetchAppPerformance(),
      ]);
      if (!mountedRef.current) return true;
      setAppStatus(status);
      setPerformance(perf);
      setHealthState(mapHealthState(true, status));
      setReconnectAttempt(0);
      setIsStartupLoading(false);
      return true;
    } catch (err) {
      if (!mountedRef.current) return false;
      setHealthState('reconnecting');
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Failed to load application status';
      setError(message);
      return false;
    }
  }, [mapHealthState]);

  useEffect(() => {
    mountedRef.current = true;
    void pollStatus();

    const statusInterval = window.setInterval(() => {
      void pollStatus({ silent: true });
    }, STATUS_POLL_MS);

    return () => {
      mountedRef.current = false;
      window.clearInterval(statusInterval);
    };
  }, [pollStatus]);

  useEffect(() => {
    if (healthState !== 'offline' && healthState !== 'reconnecting') return;
    if (reconnectAttempt >= MAX_RECONNECT_ATTEMPTS) return;

    const reconnectId = window.setInterval(() => {
      void pollStatus({ silent: true });
    }, RECONNECT_INTERVAL_MS);

    return () => window.clearInterval(reconnectId);
  }, [healthState, reconnectAttempt, pollStatus]);

  const enterBackgroundMode = useCallback(async () => {
    await setBackgroundMode(true);
    await setWindowVisibility(false);
    await pollStatus({ silent: true });
  }, [pollStatus]);

  const showWindow = useCallback(async () => {
    await setBackgroundMode(false);
    await setWindowVisibility(true);
    await pollStatus({ silent: true });
  }, [pollStatus]);

  return {
    healthState,
    appStatus,
    performance,
    isStartupLoading,
    error,
    reconnectAttempt,
    reload: pollStatus,
    restartMonitors: restartAppMonitors,
    shutdown: shutdownApp,
    enterBackgroundMode,
    showWindow,
  };
}
