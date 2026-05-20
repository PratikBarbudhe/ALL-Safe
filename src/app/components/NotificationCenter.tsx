import { useEffect, useRef } from 'react';
import {
  AlertTriangle,
  Bell,
  Check,
  CheckCheck,
  Info,
  ShieldAlert,
  Trash2,
  X,
} from 'lucide-react';
import { formatRelativeThreatTime, notificationSeverityColors } from '@/lib/api';
import type { NotificationEntry } from '@/lib/api';

interface NotificationCenterProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  notifications: NotificationEntry[];
  unreadCount: number;
  isLoading: boolean;
  isRefreshing: boolean;
  onMarkRead: (id: number) => void;
  onMarkAllRead: () => void;
  onClearAll: () => void;
}

function SeverityIcon({ severity }: { severity: string }) {
  const colors = notificationSeverityColors(severity);
  const Icon =
    severity === 'critical' || severity === 'high'
      ? ShieldAlert
      : severity === 'warning'
        ? AlertTriangle
        : Info;
  return (
    <div
      className="p-2 rounded-lg flex-shrink-0"
      style={{ backgroundColor: colors.bg }}
    >
      <Icon className="w-4 h-4" style={{ color: colors.color }} />
    </div>
  );
}

export default function NotificationCenter({
  open,
  onOpenChange,
  notifications,
  unreadCount,
  isLoading,
  isRefreshing,
  onMarkRead,
  onMarkAllRead,
  onClearAll,
}: NotificationCenterProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        const bell = document.getElementById('allsafe-notification-bell');
        if (bell?.contains(event.target as Node)) return;
        onOpenChange(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open, onOpenChange]);

  if (!open) return null;

  return (
    <div
      ref={panelRef}
      className="absolute right-0 top-full mt-2 w-96 rounded-xl border shadow-2xl z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-200"
      style={{
        backgroundColor: '#1E293B',
        borderColor: '#334155',
      }}
    >
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: '#334155', backgroundColor: '#0F172A' }}
      >
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4" style={{ color: '#94A3B8' }} />
          <span className="text-sm font-medium" style={{ color: '#F8FAFC' }}>
            Security Alerts
          </span>
          {unreadCount > 0 && (
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{ backgroundColor: '#EF444420', color: '#EF4444' }}
            >
              {unreadCount} new
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          className="p-1 rounded hover:opacity-80"
          aria-label="Close notifications"
        >
          <X className="w-4 h-4" style={{ color: '#94A3B8' }} />
        </button>
      </div>

      <div className="flex items-center gap-2 px-3 py-2 border-b" style={{ borderColor: '#334155' }}>
        <button
          type="button"
          onClick={onMarkAllRead}
          className="flex items-center gap-1 text-xs px-2 py-1 rounded transition-colors"
          style={{ color: '#94A3B8', backgroundColor: '#0F172A' }}
        >
          <CheckCheck className="w-3 h-3" />
          Mark all read
        </button>
        <button
          type="button"
          onClick={onClearAll}
          className="flex items-center gap-1 text-xs px-2 py-1 rounded transition-colors"
          style={{ color: '#94A3B8', backgroundColor: '#0F172A' }}
        >
          <Trash2 className="w-3 h-3" />
          Clear all
        </button>
        {isRefreshing && (
          <span className="text-xs ml-auto" style={{ color: '#64748B' }}>
            Syncing…
          </span>
        )}
      </div>

      <div className="max-h-80 overflow-y-auto">
        {isLoading && notifications.length === 0 ? (
          <p className="text-sm text-center py-8" style={{ color: '#94A3B8' }}>
            Loading alerts…
          </p>
        ) : notifications.length === 0 ? (
          <p className="text-sm text-center py-8" style={{ color: '#94A3B8' }}>
            No security notifications
          </p>
        ) : (
          notifications.map((entry) => (
            <div
              key={entry.id}
              className="flex gap-3 px-4 py-3 border-b transition-colors cursor-pointer hover:opacity-90"
              style={{
                borderColor: '#334155',
                backgroundColor: entry.read_status ? 'transparent' : '#0F172A40',
              }}
              onClick={() => {
                if (!entry.read_status) onMarkRead(entry.id);
              }}
            >
              <SeverityIcon severity={entry.severity} />
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm truncate" style={{ color: '#F8FAFC' }}>
                    {entry.title}
                  </p>
                  {!entry.read_status && (
                    <span
                      className="w-2 h-2 rounded-full flex-shrink-0 mt-1"
                      style={{ backgroundColor: notificationSeverityColors(entry.severity).color }}
                    />
                  )}
                </div>
                <p className="text-xs mt-0.5 line-clamp-2" style={{ color: '#94A3B8' }}>
                  {entry.message}
                </p>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <span className="text-xs" style={{ color: '#64748B' }}>
                    {formatRelativeThreatTime(entry.timestamp)}
                  </span>
                  <span
                    className="text-xs px-1.5 py-0.5 rounded"
                    style={{ backgroundColor: '#334155', color: '#94A3B8' }}
                  >
                    {entry.category}
                  </span>
                  {entry.action_required && (
                    <span
                      className="text-xs px-1.5 py-0.5 rounded"
                      style={{ backgroundColor: '#EF444420', color: '#EF4444' }}
                    >
                      Action required
                    </span>
                  )}
                </div>
              </div>
              {!entry.read_status && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onMarkRead(entry.id);
                  }}
                  className="p-1 rounded flex-shrink-0"
                  aria-label="Mark as read"
                >
                  <Check className="w-3.5 h-3.5" style={{ color: '#64748B' }} />
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
