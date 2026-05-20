import { useCallback, useEffect, useState } from 'react';
import { useRefreshIntervals } from '@/contexts/SettingsContext';
import {
  ApiError,
  fetchAiAnalysisHistory,
  fetchAiAnalysisOverview,
  runAiAnalysis,
  type AiAnalysisOverview,
  type AnalysisHistoryEntry,
} from '@/lib/api';

export function useAIAnalysis() {
  const { aiAnalysisMs } = useRefreshIntervals();
  const [overview, setOverview] = useState<AiAnalysisOverview | null>(null);
  const [history, setHistory] = useState<AnalysisHistoryEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAnalysis = useCallback(async (options?: { silent?: boolean }) => {
    const silent = options?.silent ?? false;
    if (silent) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const [overviewData, historyData] = await Promise.all([
        fetchAiAnalysisOverview(),
        fetchAiAnalysisHistory(15),
      ]);
      setOverview(overviewData);
      setHistory(historyData.history);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Failed to load AI analysis';
      setError(message);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadAnalysis();
    const intervalId = window.setInterval(() => {
      void loadAnalysis({ silent: true });
    }, aiAnalysisMs);
    return () => window.clearInterval(intervalId);
  }, [loadAnalysis, aiAnalysisMs]);

  const runAnalysis = useCallback(async () => {
    setIsRunning(true);
    setError(null);
    try {
      const result = await runAiAnalysis();
      setOverview(result.overview);
      const historyData = await fetchAiAnalysisHistory(15);
      setHistory(historyData.history);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Analysis run failed';
      setError(message);
    } finally {
      setIsRunning(false);
    }
  }, []);

  return {
    overview,
    history,
    isLoading,
    isRefreshing,
    isRunning,
    error,
    reload: loadAnalysis,
    runAnalysis,
  };
}
