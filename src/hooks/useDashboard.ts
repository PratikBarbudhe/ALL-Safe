import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ApiError,
  REFRESH_INTERVAL_MS,
  fetchDashboardOverview,
  fetchProcesses,
  fetchThreatStats,
  mapProcessesResponse,
  type DashboardOverview,
  type ProcessViewModel,
} from '@/lib/api';

const HISTORY_LENGTH = 7;

export interface ChartPoint {
  time: string;
  cpu: number;
  ram: number;
}

export interface ThreatChartPoint {
  time: string;
  threats: number;
}

export interface DashboardChanges {
  securityScore?: number;
  activeThreats?: number;
  blockedThreats?: number;
}

function formatChartTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function computePercentChange(current: number, previous: number | undefined): number | undefined {
  if (previous === undefined || previous === 0) {
    return undefined;
  }
  return Math.round(((current - previous) / previous) * 100);
}

export function useDashboard() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [recentProcesses, setRecentProcesses] = useState<ProcessViewModel[]>([]);
  const [performanceHistory, setPerformanceHistory] = useState<ChartPoint[]>([]);
  const [threatHistory, setThreatHistory] = useState<ThreatChartPoint[]>([]);
  const [networkThroughput, setNetworkThroughput] = useState(0);
  const [changes, setChanges] = useState<DashboardChanges>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const previousOverview = useRef<DashboardOverview | null>(null);
  const previousNetworkBytes = useRef<number | null>(null);
  const previousFetchTime = useRef<number | null>(null);

  const loadDashboard = useCallback(async (options?: { silent?: boolean }) => {
    const silent = options?.silent ?? false;
    if (silent) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const [overviewData, processData, threatStats] = await Promise.all([
        fetchDashboardOverview(),
        fetchProcesses(),
        fetchThreatStats().catch(() => null),
      ]);

      const now = Date.now();
      const totalNetworkBytes =
        overviewData.network_activity.sent + overviewData.network_activity.received;

      if (previousNetworkBytes.current !== null && previousFetchTime.current !== null) {
        const elapsedSeconds = (now - previousFetchTime.current) / 1000;
        if (elapsedSeconds > 0) {
          const deltaBytes = Math.max(0, totalNetworkBytes - previousNetworkBytes.current);
          setNetworkThroughput(deltaBytes / elapsedSeconds);
        }
      }

      previousNetworkBytes.current = totalNetworkBytes;
      previousFetchTime.current = now;

      const chartTime = formatChartTime(new Date(now));
      setPerformanceHistory((prev) =>
        [...prev, { time: chartTime, cpu: overviewData.cpu_usage, ram: overviewData.ram_usage }].slice(
          -HISTORY_LENGTH,
        ),
      );
      const threatChartValue =
        threatStats?.events_last_24h ?? overviewData.active_threats;
      setThreatHistory((prev) =>
        [...prev, { time: chartTime, threats: threatChartValue }].slice(-HISTORY_LENGTH),
      );

      if (previousOverview.current) {
        setChanges({
          securityScore: computePercentChange(
            overviewData.security_score,
            previousOverview.current.security_score,
          ),
          activeThreats: computePercentChange(
            overviewData.active_threats,
            previousOverview.current.active_threats,
          ),
          blockedThreats: computePercentChange(
            overviewData.blocked_threats,
            previousOverview.current.blocked_threats,
          ),
        });
      }

      previousOverview.current = overviewData;
      setOverview(overviewData);
      setRecentProcesses(mapProcessesResponse(processData).slice(0, 5));
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Failed to load dashboard';
      setError(message);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
    const intervalId = window.setInterval(() => {
      void loadDashboard({ silent: true });
    }, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(intervalId);
  }, [loadDashboard]);

  return {
    overview,
    recentProcesses,
    performanceHistory,
    threatHistory,
    networkThroughput,
    changes,
    isLoading,
    isRefreshing,
    error,
    reload: loadDashboard,
  };
}
