import { AlertTriangle, Shield, FileText, TrendingUp, RefreshCw } from 'lucide-react';
import { useRansomware } from '@/hooks/useRansomware';
import { formatRelativeThreatTime, formatNumber } from '@/lib/format';
import { useModuleAlerts } from '@/contexts/NotificationContext';
import NotificationAlertStrip from './NotificationAlertStrip';

const statusColors: Record<string, { bg: string; color: string; dot: string }> = {
  Protected: { bg: '#10B98120', color: '#10B981', dot: 'bg-green-500' },
  Monitoring: { bg: '#3B82F620', color: '#3B82F6', dot: 'bg-blue-500' },
  'Suspicious Activity': { bg: '#F59E0B20', color: '#F59E0B', dot: 'bg-yellow-500' },
  'Threat Detected': { bg: '#EF444420', color: '#EF4444', dot: 'bg-red-500' },
};

const layerStatusStyle = (layerStatus: string) => {
  if (layerStatus === 'active') {
    return { bg: '#10B98120', color: '#10B981', dot: 'bg-green-500' };
  }
  if (layerStatus === 'standby') {
    return { bg: '#334155', color: '#94A3B8', dot: 'bg-slate-500' };
  }
  return { bg: '#EF444420', color: '#EF4444', dot: 'bg-red-500' };
};

const severityStyle = (severity: string) => {
  switch (severity) {
    case 'critical':
      return { bg: '#EF444420', color: '#EF4444' };
    case 'high':
      return { bg: '#F9731620', color: '#F97316' };
    case 'medium':
      return { bg: '#EAB30820', color: '#EAB308' };
    default:
      return { bg: '#3B82F620', color: '#3B82F6' };
  }
};

export default function RansomwareDetection() {
  const {
    status,
    events,
    settings,
    isLoading,
    isRefreshing,
    isToggling,
    error,
    notice,
    reload,
    toggleProtection,
    saveSettings,
  } = useRansomware();

  const { criticalCount, latest: ransomwareAlert } = useModuleAlerts('Ransomware');

  const protectionLabel = status?.protection_status ?? 'Monitoring';
  const protectionStyle = statusColors[protectionLabel] ?? statusColors.Monitoring;
  const isActive = status?.monitoring_active ?? false;

  return (
    <div className="p-6 overflow-y-auto" style={{ backgroundColor: '#0F172A', height: 'calc(100vh - 4rem)' }}>
      {error && (
        <div
          className="mb-4 p-4 rounded-lg border flex items-center justify-between gap-4"
          style={{ backgroundColor: '#EF444420', borderColor: '#EF4444', color: '#FCA5A5' }}
        >
          <div className="flex items-center gap-2 text-sm">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => void reload()}
            className="px-3 py-1 rounded text-xs flex items-center gap-1 shrink-0"
            style={{ backgroundColor: '#EF4444', color: '#FFFFFF' }}
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        </div>
      )}

      {criticalCount > 0 && ransomwareAlert && (
        <NotificationAlertStrip
          severity={ransomwareAlert.severity}
          message={`${criticalCount} ransomware alert${criticalCount === 1 ? '' : 's'} — ${ransomwareAlert.title}`}
        />
      )}

      {notice && (
        <div
          className="mb-4 p-3 rounded-lg border text-sm transition-opacity duration-300"
          style={{
            backgroundColor: notice.type === 'success' ? '#10B98120' : '#EF444420',
            borderColor: notice.type === 'success' ? '#10B981' : '#EF4444',
            color: notice.type === 'success' ? '#6EE7B7' : '#FCA5A5',
          }}
        >
          {notice.message}
        </div>
      )}

      <div
        className="transition-opacity duration-300 ease-in-out"
        style={{ opacity: isLoading ? 0.5 : isRefreshing ? 0.85 : 1 }}
      >
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-2xl mb-1" style={{ color: '#F8FAFC' }}>
                Ransomware Detection
              </h2>
              <p className="text-sm" style={{ color: '#94A3B8' }}>
                Advanced protection against ransomware attacks
              </p>
            </div>
            <button
              type="button"
              onClick={() => void toggleProtection()}
              disabled={isToggling || isLoading}
              className="px-4 py-2 rounded-lg flex items-center gap-2 disabled:opacity-50"
              style={{
                backgroundColor: isActive ? '#334155' : '#3B82F6',
                color: '#FFFFFF',
              }}
            >
              <Shield className="w-4 h-4" />
              {isActive ? 'Disable Protection' : 'Enable Protection'}
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: protectionStyle.bg }}>
                  <Shield className="w-5 h-5" style={{ color: protectionStyle.color }} />
                </div>
                <div>
                  <p className="text-2xl" style={{ color: protectionStyle.color }}>
                    {isLoading ? '—' : protectionLabel}
                  </p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>
                    Protection Status
                  </p>
                </div>
              </div>
            </div>
            <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: '#EF444420' }}>
                  <AlertTriangle className="w-5 h-5" style={{ color: '#EF4444' }} />
                </div>
                <div>
                  <p className="text-2xl" style={{ color: '#F8FAFC' }}>
                    {isLoading ? '—' : formatNumber(status?.attempts_blocked ?? 0)}
                  </p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>
                    Attempts Blocked
                  </p>
                </div>
              </div>
            </div>
            <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: '#3B82F620' }}>
                  <FileText className="w-5 h-5" style={{ color: '#3B82F6' }} />
                </div>
                <div>
                  <p className="text-2xl" style={{ color: '#F8FAFC' }}>
                    {isLoading ? '—' : formatNumber(status?.protected_files_count ?? 0)}
                  </p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>
                    Protected Files
                  </p>
                </div>
              </div>
            </div>
            <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: '#10B98120' }}>
                  <TrendingUp className="w-5 h-5" style={{ color: '#10B981' }} />
                </div>
                <div>
                  <p className="text-2xl" style={{ color: '#10B981' }}>
                    {isLoading ? '—' : `${status?.success_rate_percent ?? 100}%`}
                  </p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>
                    Success Rate
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Settings row */}
        <div
          className="mb-6 p-4 rounded-xl border grid grid-cols-1 md:grid-cols-3 gap-4"
          style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}
        >
          <label className="flex items-center justify-between gap-3 text-sm" style={{ color: '#F8FAFC' }}>
            <span>Auto-quarantine</span>
            <input
              type="checkbox"
              checked={settings?.auto_quarantine ?? true}
              disabled={isToggling || isLoading}
              onChange={(e) => void saveSettings({ auto_quarantine: e.target.checked })}
              className="w-4 h-4"
            />
          </label>
          <label className="flex items-center justify-between gap-3 text-sm" style={{ color: '#F8FAFC' }}>
            <span>Sensitivity</span>
            <select
              value={settings?.sensitivity ?? 'medium'}
              disabled={isToggling || isLoading}
              onChange={(e) => void saveSettings({ sensitivity: e.target.value })}
              className="px-3 py-1 rounded-lg text-sm outline-none"
              style={{ backgroundColor: '#0F172A', color: '#F8FAFC', border: '1px solid #334155' }}
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </label>
          <div className="text-sm" style={{ color: '#94A3B8' }}>
            <span style={{ color: '#F8FAFC' }}>Protected folders: </span>
            {(status?.protected_folders ?? []).length > 0
              ? `${status?.protected_folders.length} paths monitored`
              : '—'}
          </div>
        </div>

        {/* Protection Features */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
            <h3 className="mb-4" style={{ color: '#F8FAFC' }}>
              Active Protection Layers
            </h3>
            <div className="space-y-3">
              {(status?.layers ?? []).map((layer) => {
                const style = layerStatusStyle(layer.status);
                return (
                  <div
                    key={layer.name}
                    className="flex items-center justify-between p-3 rounded-lg"
                    style={{ backgroundColor: '#0F172A' }}
                  >
                    <span className="text-sm" style={{ color: '#F8FAFC' }}>
                      {layer.name}
                    </span>
                    <span
                      className="px-3 py-1 rounded-full text-xs flex items-center gap-1"
                      style={{ backgroundColor: style.bg, color: style.color }}
                    >
                      {layer.status === 'active' && (
                        <div className={`w-1.5 h-1.5 rounded-full ${style.dot} animate-pulse`} />
                      )}
                      {layer.status}
                    </span>
                  </div>
                );
              })}
            </div>
            {!isLoading && (status?.protected_folders?.length ?? 0) > 0 && (
              <div className="mt-4 pt-4 border-t" style={{ borderColor: '#334155' }}>
                <p className="text-xs mb-2 uppercase tracking-wider" style={{ color: '#64748B' }}>
                  Protected Folders
                </p>
                <ul className="space-y-1 max-h-28 overflow-y-auto">
                  {status?.protected_folders.map((folder) => (
                    <li key={folder} className="text-xs truncate" style={{ color: '#94A3B8' }} title={folder}>
                      {folder}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
            <h3 className="mb-4" style={{ color: '#F8FAFC' }}>
              Recent Blocked Attempts
            </h3>
            <div className="space-y-3">
              {!isLoading && events.length === 0 && (
                <p className="text-sm text-center py-6" style={{ color: '#94A3B8' }}>
                  No ransomware activity detected yet. Protection is{' '}
                  {isActive ? 'actively monitoring' : 'disabled'}.
                </p>
              )}
              {events.map((attempt) => {
                const sev = severityStyle(attempt.severity);
                return (
                  <div
                    key={attempt.id}
                    className="p-3 rounded-lg border"
                    style={{ backgroundColor: '#0F172A', borderColor: '#334155' }}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm truncate pr-2" style={{ color: '#F8FAFC' }} title={attempt.threat_name}>
                        {attempt.threat_name}
                      </span>
                      <span className="text-xs shrink-0" style={{ color: '#94A3B8' }}>
                        {formatRelativeThreatTime(attempt.timestamp)}
                      </span>
                    </div>
                    <p className="text-xs mb-2 truncate" style={{ color: '#64748B' }} title={attempt.description}>
                      {attempt.description}
                    </p>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="px-2 py-1 rounded text-xs" style={{ backgroundColor: sev.bg, color: sev.color }}>
                        {attempt.severity}
                      </span>
                      {attempt.quarantined && (
                        <span className="px-2 py-1 rounded text-xs" style={{ backgroundColor: '#3B82F620', color: '#3B82F6' }}>
                          quarantined
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
