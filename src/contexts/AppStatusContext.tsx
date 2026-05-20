import { createContext, useContext, useEffect, type ReactNode } from 'react';
import { useAppStatus } from '@/hooks/useAppStatus';
import { restartAppMonitors, setBackgroundMode, shutdownApp } from '@/lib/api';

type AppStatusContextValue = ReturnType<typeof useAppStatus>;

const AppStatusContext = createContext<AppStatusContextValue | null>(null);

function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

export function AppStatusProvider({ children }: { children: ReactNode }) {
  const value = useAppStatus();

  useEffect(() => {
    if (!isTauriRuntime()) return;

    const unsubs: Array<() => void> = [];
    let cancelled = false;

    void (async () => {
      try {
        const { listen } = await import('@tauri-apps/api/event');
        if (cancelled) return;

        unsubs.push(
          (await listen<boolean>('allsafe-background-mode', () => {
            void value.enterBackgroundMode();
          })).unlisten,
        );
        unsubs.push(
          (await listen('allsafe-restart-monitors', () => {
            void restartAppMonitors().then(() => value.reload({ silent: true }));
          })).unlisten,
        );
        unsubs.push(
          (await listen('allsafe-exit', () => {
            void shutdownApp();
          })).unlisten,
        );
        unsubs.push(
          (await listen('allsafe-shutdown', () => {
            void setBackgroundMode(false);
          })).unlisten,
        );
      } catch {
        // Browser-only dev without Tauri events
      }
    })();

    return () => {
      cancelled = true;
      unsubs.forEach((fn) => fn());
    };
  }, [value]);

  return (
    <AppStatusContext.Provider value={value}>{children}</AppStatusContext.Provider>
  );
}

export function useAppStatusContext(): AppStatusContextValue {
  const ctx = useContext(AppStatusContext);
  if (!ctx) {
    throw new Error('useAppStatusContext must be used within AppStatusProvider');
  }
  return ctx;
}
