import { createContext, useContext, type ReactNode } from 'react';
import { useNotifications } from '@/hooks/useNotifications';
import type { NotificationEntry } from '@/lib/api';

type NotificationContextValue = ReturnType<typeof useNotifications>;

const NotificationContext = createContext<NotificationContextValue | null>(null);

export function NotificationProvider({
  children,
  enableToasts = true,
}: {
  children: ReactNode;
  enableToasts?: boolean;
}) {
  const value = useNotifications({ enableToasts });
  return (
    <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>
  );
}

export function useNotificationContext(): NotificationContextValue {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    throw new Error('useNotificationContext must be used within NotificationProvider');
  }
  return ctx;
}

export function useModuleAlerts(category?: string) {
  const { notifications, unreadCount } = useNotificationContext();
  const filtered = category
    ? notifications.filter((n) => n.category === category && !n.read_status)
    : notifications.filter((n) => !n.read_status);
  const criticalCount = filtered.filter(
    (n) => n.severity === 'critical' || n.severity === 'high',
  ).length;
  const latest = filtered[0] ?? null;
  return { unreadCount, criticalCount, latest, alerts: filtered.slice(0, 5) };
}

export type { NotificationEntry };
