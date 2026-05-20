import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import {
  ApiError,
  NOTIFICATION_REFRESH_INTERVAL_MS,
  clearNotifications,
  fetchNotifications,
  fetchUnreadNotificationCount,
  markAllNotificationsRead,
  markNotificationRead,
  notificationSeverityColors,
  type NotificationEntry,
} from '@/lib/api';

export function useNotifications(options?: { enableToasts?: boolean }) {
  const enableToasts = options?.enableToasts ?? false;
  const [notifications, setNotifications] = useState<NotificationEntry[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const seenIdsRef = useRef<Set<number>>(new Set());
  const initializedRef = useRef(false);

  const loadNotifications = useCallback(
    async (opts?: { silent?: boolean }) => {
      const silent = opts?.silent ?? false;
      if (silent) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      try {
        const [listResponse, unreadResponse] = await Promise.all([
          fetchNotifications({ limit: 50 }),
          fetchUnreadNotificationCount(),
        ]);

        setNotifications(listResponse.notifications);
        setTotal(listResponse.total);
        setUnreadCount(unreadResponse.unread_count);

        if (enableToasts) {
          for (const entry of listResponse.notifications) {
            if (seenIdsRef.current.has(entry.id)) {
              continue;
            }
            if (initializedRef.current && !entry.read_status) {
              const colors = notificationSeverityColors(entry.severity);
              toast(entry.title, {
                description: entry.message,
                duration: entry.severity === 'critical' ? 8000 : 4000,
                style: {
                  backgroundColor: '#1E293B',
                  color: '#F8FAFC',
                  border: `1px solid ${colors.color}40`,
                },
              });
            }
            seenIdsRef.current.add(entry.id);
          }
          initializedRef.current = true;
        }
      } catch (err) {
        const message =
          err instanceof ApiError
            ? err.message
            : err instanceof Error
              ? err.message
              : 'Failed to load notifications';
        setError(message);
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [enableToasts],
  );

  useEffect(() => {
    void loadNotifications();
    const intervalId = window.setInterval(() => {
      void loadNotifications({ silent: true });
    }, NOTIFICATION_REFRESH_INTERVAL_MS);
    return () => window.clearInterval(intervalId);
  }, [loadNotifications]);

  const markRead = useCallback(
    async (id: number) => {
      await markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read_status: true } : n)),
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    },
    [],
  );

  const markAllRead = useCallback(async () => {
    await markAllNotificationsRead();
    setNotifications((prev) => prev.map((n) => ({ ...n, read_status: true })));
    setUnreadCount(0);
  }, []);

  const clearAll = useCallback(async () => {
    await clearNotifications();
    setNotifications([]);
    setUnreadCount(0);
    setTotal(0);
    seenIdsRef.current.clear();
  }, []);

  return {
    notifications,
    unreadCount,
    total,
    isLoading,
    isRefreshing,
    error,
    reload: loadNotifications,
    markRead,
    markAllRead,
    clearAll,
  };
}
