import { useCallback, useEffect, useState } from 'react';
import {
  ApiError,
  THREAT_REFRESH_INTERVAL_MS,
  fetchThreatLogs,
  fetchThreatStats,
  mapThreatLogToViewModel,
  type ThreatLogQuery,
  type ThreatLogViewModel,
  type ThreatStats,
} from '@/lib/api';

const DEFAULT_PAGE_SIZE = 10;

export function useThreatLogs() {
  const [logs, setLogs] = useState<ThreatLogViewModel[]>([]);
  const [stats, setStats] = useState<ThreatStats | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [severityFilter, setSeverityFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [severityFilter, categoryFilter, debouncedSearch]);

  const buildQuery = useCallback(
    (): ThreatLogQuery => ({
      page,
      page_size: DEFAULT_PAGE_SIZE,
      severity: severityFilter !== 'all' ? severityFilter : undefined,
      category: categoryFilter !== 'all' ? categoryFilter : undefined,
      search: debouncedSearch.trim() || undefined,
    }),
    [page, severityFilter, categoryFilter, debouncedSearch],
  );

  const loadThreatData = useCallback(
    async (options?: { silent?: boolean }) => {
      const silent = options?.silent ?? false;
      if (silent) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      try {
        const [logsResponse, statsResponse] = await Promise.all([
          fetchThreatLogs(buildQuery()),
          fetchThreatStats(),
        ]);

        setLogs(logsResponse.logs.map(mapThreatLogToViewModel));
        setTotal(logsResponse.total);
        setTotalPages(logsResponse.total_pages);
        setStats(statsResponse);
      } catch (err) {
        const message =
          err instanceof ApiError
            ? err.message
            : err instanceof Error
              ? err.message
              : 'Failed to load threat logs';
        setError(message);
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [buildQuery],
  );

  useEffect(() => {
    void loadThreatData();
    const intervalId = window.setInterval(() => {
      void loadThreatData({ silent: true });
    }, THREAT_REFRESH_INTERVAL_MS);
    return () => window.clearInterval(intervalId);
  }, [loadThreatData]);

  const goToPage = useCallback((nextPage: number) => {
    setPage(Math.max(1, nextPage));
  }, []);

  return {
    logs,
    stats,
    page,
    total,
    totalPages,
    pageSize: DEFAULT_PAGE_SIZE,
    severityFilter,
    setSeverityFilter,
    categoryFilter,
    setCategoryFilter,
    search,
    setSearch,
    isLoading,
    isRefreshing,
    error,
    reload: loadThreatData,
    goToPage,
  };
}
