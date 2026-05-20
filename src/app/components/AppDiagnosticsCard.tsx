import { Activity, Cpu, RefreshCw, Server } from 'lucide-react';
import { useAppStatusContext } from '@/contexts/AppStatusContext';
import { appHealthColors } from '@/lib/api';

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m} min`;
  return `${seconds} sec`;
}

export default function AppDiagnosticsCard() {
  const { healthState, appStatus, performance, reload, restartMonitors } =
    useAppStatusContext();
  const colors = appHealthColors(healthState);

  return (
    <div
      className="p-6 rounded-xl border mb-6 transition-opacity duration-300"
      style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Server className="w-5 h-5" style={{ color: '#3B82F6' }} />
          <h3 style={{ color: '#F8FAFC' }}>Production Diagnostics</h3>
          <span
            className="px-2 py-0.5 rounded-full text-xs"
            style={{ backgroundColor: colors.bg, color: colors.color }}
          >
            {colors.label}
          </span>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void reload({ silent: true })}
            className="px-3 py-1 rounded text-xs flex items-center gap-1"
            style={{ backgroundColor: '#334155', color: '#F8FAFC' }}
          >
            <RefreshCw className="w-3 h-3" />
            Refresh
          </button>
          <button
            type="button"
            onClick={() => void restartMonitors()}
            className="px-3 py-1 rounded text-xs"
            style={{ backgroundColor: '#3B82F6', color: '#FFFFFF' }}
          >
            Restart Monitors
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
        <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
          <p className="text-xs mb-1" style={{ color: '#94A3B8' }}>Monitoring Uptime</p>
          <p className="text-xl" style={{ color: '#F8FAFC' }}>
            {appStatus ? formatUptime(appStatus.uptime_seconds) : '—'}
          </p>
        </div>
        <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
          <p className="text-xs mb-1" style={{ color: '#94A3B8' }}>Active Monitors</p>
          <p className="text-xl" style={{ color: '#F8FAFC' }}>
            {appStatus
              ? `${appStatus.monitors.filter((m) => m.running).length}/${appStatus.monitors.length}`
              : '—'}
          </p>
        </div>
        <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
          <p className="text-xs mb-1" style={{ color: '#94A3B8' }}>Backend Health</p>
          <p className="text-xl capitalize" style={{ color: colors.color }}>
            {appStatus?.status ?? '—'}
          </p>
        </div>
        <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
          <p className="text-xs mb-1 flex items-center gap-1" style={{ color: '#94A3B8' }}>
            <Cpu className="w-3 h-3" /> Process Load
          </p>
          <p className="text-xl" style={{ color: '#F8FAFC' }}>
            {performance ? `${performance.process_cpu_percent}%` : '—'}
          </p>
          <p className="text-xs" style={{ color: '#64748B' }}>
            {performance ? `${performance.process_memory_mb} MB RAM` : ''}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div>
          <p className="text-xs mb-2 uppercase tracking-wide" style={{ color: '#64748B' }}>
            Monitor Health
          </p>
          <div className="space-y-2">
            {(appStatus?.monitors ?? []).map((m) => (
              <div
                key={m.name}
                className="flex items-center justify-between p-2 rounded-lg text-sm"
                style={{ backgroundColor: '#0F172A' }}
              >
                <span style={{ color: '#F8FAFC' }}>{m.name}</span>
                <span
                  className="text-xs px-2 py-0.5 rounded"
                  style={{
                    backgroundColor: m.healthy ? '#10B98120' : '#EF444420',
                    color: m.healthy ? '#10B981' : '#EF4444',
                  }}
                >
                  {m.healthy ? 'healthy' : 'degraded'}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div>
          <p className="text-xs mb-2 uppercase tracking-wide" style={{ color: '#64748B' }}>
            Performance
          </p>
          <div className="p-3 rounded-lg space-y-2" style={{ backgroundColor: '#0F172A' }}>
            <div className="flex items-center gap-2 text-sm" style={{ color: '#94A3B8' }}>
              <Activity className="w-4 h-4" />
              Status: {performance?.status ?? '—'}
            </div>
            {performance?.poll_throttle_active && (
              <p className="text-xs" style={{ color: '#F59E0B' }}>
                Poll throttling active — expensive analysis deferred
              </p>
            )}
            {(performance?.anomalies ?? []).map((a) => (
              <p key={a} className="text-xs" style={{ color: '#F59E0B' }}>
                {a}
              </p>
            ))}
            {performance && performance.anomalies.length === 0 && (
              <p className="text-xs" style={{ color: '#10B981' }}>
                No performance anomalies detected
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
