import { useCallback, useEffect, useState } from 'react';
import {
  ApiError,
  QUARANTINE_REFRESH_INTERVAL_MS,
  addToQuarantine,
  clearQuarantine,
  deleteQuarantineItem,
  fetchQuarantineItems,
  fetchQuarantineStats,
  mapQuarantineItemToViewModel,
  restoreQuarantineItem,
  uploadToQuarantine,
  type QuarantineItemViewModel,
  type QuarantineStats,
} from '@/lib/api';

export function useQuarantine() {
  const [items, setItems] = useState<QuarantineItemViewModel[]>([]);
  const [stats, setStats] = useState<QuarantineStats | null>(null);
  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isActing, setIsActing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(
    null,
  );

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  const loadQuarantine = useCallback(
    async (options?: { silent?: boolean }) => {
      const silent = options?.silent ?? false;
      if (silent) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      try {
        const [itemsResponse, statsResponse] = await Promise.all([
          fetchQuarantineItems({
            status: 'quarantined',
            severity: severityFilter !== 'all' ? severityFilter : undefined,
            search: debouncedSearch.trim() || undefined,
          }),
          fetchQuarantineStats(),
        ]);
        setItems(itemsResponse.items.map(mapQuarantineItemToViewModel));
        setStats(statsResponse);
      } catch (err) {
        const message =
          err instanceof ApiError
            ? err.message
            : err instanceof Error
              ? err.message
              : 'Failed to load quarantine data';
        setError(message);
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [severityFilter, debouncedSearch],
  );

  useEffect(() => {
    void loadQuarantine();
    const intervalId = window.setInterval(() => {
      void loadQuarantine({ silent: true });
    }, QUARANTINE_REFRESH_INTERVAL_MS);
    return () => window.clearInterval(intervalId);
  }, [loadQuarantine]);

  const showNotice = useCallback((type: 'success' | 'error', message: string) => {
    setNotice({ type, message });
    window.setTimeout(() => setNotice(null), 4000);
  }, []);

  const runAction = useCallback(
    async (action: () => Promise<{ message: string }>) => {
      setIsActing(true);
      setError(null);
      try {
        const result = await action();
        showNotice('success', result.message);
        await loadQuarantine({ silent: true });
      } catch (err) {
        const message =
          err instanceof ApiError
            ? err.message
            : err instanceof Error
              ? err.message
              : 'Action failed';
        showNotice('error', message);
      } finally {
        setIsActing(false);
      }
    },
    [loadQuarantine, showNotice],
  );

  const restoreItem = useCallback(
    (id: number) => runAction(() => restoreQuarantineItem(id)),
    [runAction],
  );

  const deleteItem = useCallback(
    (id: number) => runAction(() => deleteQuarantineItem(id)),
    [runAction],
  );

  const clearAll = useCallback(async () => {
    setIsActing(true);
    try {
      const result = await clearQuarantine();
      showNotice('success', `Cleared ${result.cleared} quarantined file(s)`);
      await loadQuarantine({ silent: true });
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Clear failed';
      showNotice('error', message);
    } finally {
      setIsActing(false);
    }
  }, [loadQuarantine, showNotice]);

  const quarantineByPath = useCallback(
    async (filePath: string, reason?: string) => {
      await runAction(() =>
        addToQuarantine({
          file_path: filePath,
          reason: reason ?? 'Manual quarantine test',
          severity: 'medium',
          category: 'File Activity',
        }),
      );
    },
    [runAction],
  );

  const quarantineUpload = useCallback(
    async (file: File) => {
      await runAction(() => uploadToQuarantine(file));
    },
    [runAction],
  );

  const exportCsv = useCallback(() => {
    if (items.length === 0) return;
    const header = 'File Name,Threat Type,Date,Size,Risk,Status,Original Path\n';
    const rows = items
      .map(
        (item) =>
          `"${item.name}","${item.type}","${item.date}","${item.size}","${item.risk}","${item.status}","${item.originalPath}"`,
      )
      .join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'allsafe-quarantine-export.csv';
    link.click();
    URL.revokeObjectURL(url);
  }, [items]);

  return {
    items,
    stats,
    search,
    setSearch,
    severityFilter,
    setSeverityFilter,
    isLoading,
    isRefreshing,
    isActing,
    error,
    notice,
    reload: loadQuarantine,
    restoreItem,
    deleteItem,
    clearAll,
    quarantineByPath,
    quarantineUpload,
    exportCsv,
  };
}
