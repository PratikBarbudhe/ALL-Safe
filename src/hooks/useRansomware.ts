import { useCallback, useEffect, useState } from 'react';
import {
  ApiError,
  RANSOMWARE_REFRESH_INTERVAL_MS,
  fetchRansomwareEvents,
  fetchRansomwareSettings,
  fetchRansomwareStatus,
  startRansomwareProtection,
  stopRansomwareProtection,
  updateRansomwareSettings,
  type RansomwareEvent,
  type RansomwareSettings,
  type RansomwareSettingsUpdate,
  type RansomwareStatus,
} from '@/lib/api';

export function useRansomware() {
  const [status, setStatus] = useState<RansomwareStatus | null>(null);
  const [events, setEvents] = useState<RansomwareEvent[]>([]);
  const [settings, setSettings] = useState<RansomwareSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isToggling, setIsToggling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(
    null,
  );

  const showNotice = useCallback((type: 'success' | 'error', message: string) => {
    setNotice({ type, message });
    window.setTimeout(() => setNotice(null), 4000);
  }, []);

  const loadRansomware = useCallback(async (options?: { silent?: boolean }) => {
    const silent = options?.silent ?? false;
    if (silent) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const [statusData, eventsData, settingsData] = await Promise.all([
        fetchRansomwareStatus(),
        fetchRansomwareEvents(20),
        fetchRansomwareSettings(),
      ]);
      setStatus(statusData);
      setEvents(eventsData.events);
      setSettings(settingsData);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Failed to load ransomware protection data';
      setError(message);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadRansomware();
    const intervalId = window.setInterval(() => {
      void loadRansomware({ silent: true });
    }, RANSOMWARE_REFRESH_INTERVAL_MS);
    return () => window.clearInterval(intervalId);
  }, [loadRansomware]);

  const toggleProtection = useCallback(async () => {
    setIsToggling(true);
    setError(null);
    try {
      const active = status?.monitoring_active ?? false;
      const result = active
        ? await stopRansomwareProtection()
        : await startRansomwareProtection();
      showNotice('success', result.message);
      await loadRansomware({ silent: true });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Failed to toggle protection';
      showNotice('error', message);
    } finally {
      setIsToggling(false);
    }
  }, [status?.monitoring_active, loadRansomware, showNotice]);

  const saveSettings = useCallback(
    async (patch: RansomwareSettingsUpdate) => {
      setIsToggling(true);
      try {
        const updated = await updateRansomwareSettings(patch);
        setSettings(updated);
        showNotice('success', 'Ransomware settings updated');
        await loadRansomware({ silent: true });
      } catch (err) {
        const message =
          err instanceof ApiError
            ? err.message
            : err instanceof Error
              ? err.message
              : 'Failed to update settings';
        showNotice('error', message);
      } finally {
        setIsToggling(false);
      }
    },
    [loadRansomware, showNotice],
  );

  return {
    status,
    events,
    settings,
    isLoading,
    isRefreshing,
    isToggling,
    error,
    notice,
    reload: loadRansomware,
    toggleProtection,
    saveSettings,
  };
}
