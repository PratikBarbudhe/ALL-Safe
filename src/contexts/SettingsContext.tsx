import { createContext, useContext, type ReactNode } from 'react';
import { useSettings } from '@/hooks/useSettings';
import type { AllSafeSettings } from '@/lib/api';

type SettingsContextValue = ReturnType<typeof useSettings>;

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const value = useSettings();
  return (
    <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
  );
}

export function useSettingsContext(): SettingsContextValue {
  const ctx = useContext(SettingsContext);
  if (!ctx) {
    throw new Error('useSettingsContext must be used within SettingsProvider');
  }
  return ctx;
}

export function useRefreshIntervals() {
  const { settings } = useSettingsContext();
  return {
    dashboardMs: settings?.dashboard.refresh_interval_ms ?? 5000,
    aiAnalysisMs: (settings?.ai_analysis.analysis_interval_seconds ?? 60) * 1000,
    notificationMs: 3000,
    threatMs: 3000,
    chartHistoryLimit: settings?.dashboard.chart_history_limit ?? 7,
  };
}

export type { AllSafeSettings };
