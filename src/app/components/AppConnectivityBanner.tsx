import { AlertTriangle, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { useAppStatusContext } from '@/contexts/AppStatusContext';
import { appHealthColors } from '@/lib/api';

export default function AppConnectivityBanner() {
  const { healthState, error, isStartupLoading, reconnectAttempt, reload } =
    useAppStatusContext();

  if (isStartupLoading) {
    return (
      <div
        className="px-4 py-2 text-sm flex items-center gap-2 border-b transition-opacity duration-300"
        style={{ backgroundColor: '#3B82F620', borderColor: '#3B82F6', color: '#93C5FD' }}
      >
        <RefreshCw className="w-4 h-4 animate-spin" />
        Starting AllSafe protection services…
      </div>
    );
  }

  if (healthState === 'healthy' || healthState === 'background') {
    return null;
  }

  const colors = appHealthColors(healthState);

  return (
    <div
      className="px-4 py-2 text-sm flex items-center justify-between gap-4 border-b transition-opacity duration-300"
      style={{ backgroundColor: colors.bg, borderColor: colors.color, color: colors.color }}
    >
      <div className="flex items-center gap-2">
        {healthState === 'offline' ? (
          <WifiOff className="w-4 h-4 shrink-0" />
        ) : healthState === 'reconnecting' ? (
          <RefreshCw className="w-4 h-4 shrink-0 animate-spin" />
        ) : (
          <AlertTriangle className="w-4 h-4 shrink-0" />
        )}
        <span>
          {error ??
            (healthState === 'offline'
              ? `Backend offline — reconnect attempt ${reconnectAttempt}`
              : `${colors.label} — some monitors need attention`)}
        </span>
      </div>
      <button
        type="button"
        onClick={() => void reload()}
        className="px-3 py-1 rounded text-xs flex items-center gap-1 shrink-0"
        style={{ backgroundColor: colors.color, color: '#0F172A' }}
      >
        <Wifi className="w-3 h-3" />
        Retry
      </button>
    </div>
  );
}
