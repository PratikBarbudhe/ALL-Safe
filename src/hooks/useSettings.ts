import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ApiError,
  exportSettings,
  fetchSettings,
  importSettings,
  resetSettings,
  updateSettings,
  type AllSafeSettings,
  type SettingsUpdatePayload,
} from '@/lib/api';

export type SaveStatus = 'idle' | 'saved' | 'modified' | 'error' | 'default';

export function useSettings() {
  const [settings, setSettings] = useState<AllSafeSettings | null>(null);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSavedAt, setLastSavedAt] = useState<string>('');
  const pendingPatch = useRef<SettingsUpdatePayload>({});

  const loadSettings = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetchSettings();
      setSettings(response.settings);
      setLastSavedAt(response.last_saved_at);
      if (saveStatus !== 'modified') {
        setSaveStatus('saved');
      }
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Failed to load settings';
      setError(message);
      setSaveStatus('error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  const flushPending = useCallback(async () => {
    const patch = pendingPatch.current;
    if (Object.keys(patch).length === 0) {
      return;
    }
    pendingPatch.current = {};
    setIsSaving(true);
    setError(null);
    try {
      const response = await updateSettings(patch);
      setSettings(response.settings);
      setLastSavedAt(response.last_saved_at);
      setSaveStatus('saved');
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Failed to save settings';
      setError(message);
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  }, []);

  const queueUpdate = useCallback(
    (group: keyof SettingsUpdatePayload, field: string, value: boolean | string | number) => {
      if (!settings) return;

      setSettings((prev) => {
        if (!prev) return prev;
        const groupKey = group as keyof AllSafeSettings;
        const currentGroup = prev[groupKey];
        if (typeof currentGroup !== 'object' || currentGroup === null) {
          return prev;
        }
        return {
          ...prev,
          [group]: { ...currentGroup, [field]: value },
        };
      });

      pendingPatch.current = {
        ...pendingPatch.current,
        [group]: {
          ...(pendingPatch.current[group] ?? {}),
          [field]: value,
        },
      };
      setSaveStatus('modified');
    },
    [settings],
  );

  const saveNow = useCallback(async () => {
    await flushPending();
  }, [flushPending]);

  useEffect(() => {
    if (saveStatus !== 'modified') return;
    const timer = window.setTimeout(() => {
      void flushPending();
    }, 600);
    return () => window.clearTimeout(timer);
  }, [saveStatus, settings, flushPending]);

  const handleReset = useCallback(async () => {
    setIsSaving(true);
    setError(null);
    try {
      const response = await resetSettings();
      if (response.settings) {
        setSettings(response.settings);
      }
      pendingPatch.current = {};
      setSaveStatus('default');
      await loadSettings();
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : 'Reset failed';
      setError(message);
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  }, [loadSettings]);

  const handleExport = useCallback(async () => {
    try {
      const data = await exportSettings();
      const blob = new Blob([JSON.stringify(data.settings, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `allsafe-settings-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
      setSaveStatus('saved');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Export failed');
      setSaveStatus('error');
    }
  }, []);

  const handleImport = useCallback(async (file: File) => {
    setIsSaving(true);
    setError(null);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as Record<string, unknown>;
      const response = await importSettings(parsed);
      if (response.settings) {
        setSettings(response.settings);
      }
      pendingPatch.current = {};
      setSaveStatus('saved');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Import failed — invalid JSON');
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  }, []);

  return {
    settings,
    saveStatus,
    isLoading,
    isSaving,
    error,
    lastSavedAt,
    reload: loadSettings,
    queueUpdate,
    saveNow,
    reset: handleReset,
    exportConfig: handleExport,
    importConfig: handleImport,
  };
}
