import { useCallback, useEffect, useState } from 'react';
import {
  ApiError,
  USB_REFRESH_INTERVAL_MS,
  fetchUsbDevices,
  fetchUsbHistory,
  mapUsbDeviceToViewModel,
  triggerUsbScan,
  type UsbDeviceViewModel,
  type UsbEvent,
} from '@/lib/api';

export function useUsbMonitor() {
  const [devices, setDevices] = useState<UsbDeviceViewModel[]>([]);
  const [history, setHistory] = useState<UsbEvent[]>([]);
  const [stats, setStats] = useState({
    total: 0,
    safe: 0,
    threats: 0,
    scanning: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadUsbData = useCallback(async (options?: { silent?: boolean }) => {
    const silent = options?.silent ?? false;
    if (silent) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const [deviceResponse, historyResponse] = await Promise.all([
        fetchUsbDevices(),
        fetchUsbHistory(),
      ]);

      setDevices(deviceResponse.devices.map(mapUsbDeviceToViewModel));
      setHistory(historyResponse.events);
      setStats({
        total: deviceResponse.total_connected,
        safe: deviceResponse.safe_count,
        threats: deviceResponse.threat_count,
        scanning: deviceResponse.scanning_count,
      });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Failed to load USB data';
      setError(message);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  const scanAllDevices = useCallback(async () => {
    setIsScanning(true);
    setError(null);
    try {
      await triggerUsbScan();
      await loadUsbData({ silent: true });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'USB scan failed';
      setError(message);
    } finally {
      setIsScanning(false);
    }
  }, [loadUsbData]);

  useEffect(() => {
    void loadUsbData();
    const intervalId = window.setInterval(() => {
      void loadUsbData({ silent: true });
    }, USB_REFRESH_INTERVAL_MS);
    return () => window.clearInterval(intervalId);
  }, [loadUsbData]);

  return {
    devices,
    history,
    stats,
    isLoading,
    isRefreshing,
    isScanning,
    error,
    reload: loadUsbData,
    scanAllDevices,
  };
}
