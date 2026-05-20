import { useState } from 'react';
import { Search, Bell, User, ShieldCheck } from 'lucide-react';
import NotificationCenter from './NotificationCenter';
import { useNotificationContext } from '@/contexts/NotificationContext';
import { useAppStatusContext } from '@/contexts/AppStatusContext';
import { appHealthColors } from '@/lib/api';

export default function Header() {
  const [panelOpen, setPanelOpen] = useState(false);
  const {
    notifications,
    unreadCount,
    isLoading,
    isRefreshing,
    markRead,
    markAllRead,
    clearAll,
  } = useNotificationContext();
  const { healthState } = useAppStatusContext();
  const healthStyle = appHealthColors(healthState);

  return (
    <header className="h-16 flex items-center justify-between px-6 border-b" style={{ backgroundColor: '#0F172A', borderColor: '#1E293B' }}>
      {/* Search Bar */}
      <div className="flex-1 max-w-xl">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4" style={{ color: '#94A3B8' }} />
          <input
            type="text"
            placeholder="Search threats, processes, logs..."
            className="w-full pl-10 pr-4 py-2 rounded-lg outline-none transition-all"
            style={{
              backgroundColor: '#1E293B',
              color: '#F8FAFC',
              border: '1px solid #334155',
            }}
          />
        </div>
      </div>

      {/* Right Section */}
      <div className="flex items-center gap-4">
        {/* Protection Status */}
        <div className="flex items-center gap-2 px-4 py-2 rounded-lg" style={{ backgroundColor: '#1E293B' }}>
          <ShieldCheck className="w-5 h-5" style={{ color: '#10B981' }} />
          <div className="flex flex-col">
            <span className="text-xs" style={{ color: '#94A3B8' }}>Protection</span>
            <span className="text-sm" style={{ color: healthStyle.color }}>
              {healthState === 'background' ? 'Background' : healthState === 'healthy' ? 'Active' : healthStyle.label}
            </span>
          </div>
        </div>

        {/* Notifications */}
        <div className="relative">
          <button
            id="allsafe-notification-bell"
            type="button"
            onClick={() => setPanelOpen((prev) => !prev)}
            className="relative p-2 rounded-lg transition-colors hover:bg-opacity-80"
            style={{ backgroundColor: '#1E293B' }}
            aria-label="Security notifications"
            aria-expanded={panelOpen}
          >
            <Bell className="w-5 h-5" style={{ color: panelOpen ? '#F8FAFC' : '#94A3B8' }} />
            {unreadCount > 0 && (
              <div
                className="absolute top-1 right-1 min-w-[8px] h-2 px-0.5 rounded-full flex items-center justify-center"
                style={{ backgroundColor: '#EF4444' }}
              >
                {unreadCount > 9 ? (
                  <span className="text-[8px] text-white font-bold">9+</span>
                ) : unreadCount > 1 ? (
                  <span className="text-[8px] text-white font-bold">{unreadCount}</span>
                ) : (
                  <span className="w-2 h-2 bg-red-500 rounded-full block" />
                )}
              </div>
            )}
          </button>
          <NotificationCenter
            open={panelOpen}
            onOpenChange={setPanelOpen}
            notifications={notifications}
            unreadCount={unreadCount}
            isLoading={isLoading}
            isRefreshing={isRefreshing}
            onMarkRead={(id) => void markRead(id)}
            onMarkAllRead={() => void markAllRead()}
            onClearAll={() => void clearAll()}
          />
        </div>

        {/* User Profile */}
        <button className="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors" style={{ backgroundColor: '#1E293B' }}>
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
            <User className="w-4 h-4 text-white" />
          </div>
          <div className="text-left">
            <p className="text-sm" style={{ color: '#F8FAFC' }}>Admin</p>
            <p className="text-xs" style={{ color: '#94A3B8' }}>System Admin</p>
          </div>
        </button>
      </div>
    </header>
  );
}
