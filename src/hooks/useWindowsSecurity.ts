import { useCallback, useEffect, useState } from 'react';
import {
  ApiError,
  WINDOWS_SECURITY_REFRESH_INTERVAL_MS,
  fetchWindowsSecurityStatus,
  triggerDefenderQuickScan,
  updateDefenderSignatures,
  type WindowsSecurityStatus,
} from '@/lib/api';

export function useWindowsSecurity() {
  const [status, setStatus] = useState<WindowsSecurityStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isActing, setIsActing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ type: 'success' | 'error'; message: string } | null>(
    null,
  );

  const showNotice = useCallback((type: 'success' | 'error', message: string) => {
    setNotice({ type, message });
    window.setTimeout(() => setNotice(null), 5000);
  }, []);

  const loadSecurity = useCallback(async (options?: { silent?: boolean; refresh?: boolean }) => {
    const silent = options?.silent ?? false;
    if (silent) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const data = await fetchWindowsSecurityStatus(options?.refresh ?? false);
      setStatus(data);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Failed to load Windows security status';
      setError(message);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadSecurity();
    const intervalId = window.setInterval(() => {
      void loadSecurity({ silent: true });
    }, WINDOWS_SECURITY_REFRESH_INTERVAL_MS);
    return () => window.clearInterval(intervalId);
  }, [loadSecurity]);

  const runQuickScan = useCallback(async () => {
    setIsActing(true);
    try {
      const result = await triggerDefenderQuickScan();
      showNotice('success', result.message);
      await loadSecurity({ silent: true, refresh: true });
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : err instanceof Error ? err.message : 'Scan failed';
      showNotice('error', message);
    } finally {
      setIsActing(false);
    }
  }, [loadSecurity, showNotice]);

  const runSignatureUpdate = useCallback(async () => {
    setIsActing(true);
    try {
      const result = await updateDefenderSignatures();
      showNotice('success', result.message);
      await loadSecurity({ silent: true, refresh: true });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Signature update failed';
      showNotice('error', message);
    } finally {
      setIsActing(false);
    }
  }, [loadSecurity, showNotice]);

  return {
    status,
    isLoading,
    isRefreshing,
    isActing,
    error,
    notice,
    reload: loadSecurity,
    runQuickScan,
    runSignatureUpdate,
  };
}
