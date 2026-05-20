import { Shield, AlertTriangle, CheckCircle, Activity, Cpu, HardDrive, Usb, Wifi, TrendingUp, RefreshCw, Lock } from 'lucide-react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useDashboard } from '@/hooks/useDashboard';
import { useWindowsSecurity } from '@/hooks/useWindowsSecurity';
import type { RiskLevel } from '@/lib/api';
import { windowsStatusColors, windowsStatusLabel } from '@/lib/api';
import { formatBytesPerSecond, formatNumber, formatPercent } from '@/lib/format';

const StatCard = ({
  icon: Icon,
  title,
  value,
  change,
  status,
  loading,
}: {
  icon: typeof Shield;
  title: string;
  value: string;
  change?: number;
  status: 'danger' | 'success' | 'info';
  loading?: boolean;
}) => (
    <div
      className={`p-6 rounded-xl border transition-all duration-300 hover:shadow-lg ${loading ? 'animate-pulse' : ''}`}
      style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="p-3 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
          <Icon className="w-6 h-6" style={{ color: status === 'danger' ? '#EF4444' : status === 'success' ? '#10B981' : '#3B82F6' }} />
        </div>
        {change !== undefined && !loading && (
          <div className="flex items-center gap-1 px-2 py-1 rounded text-xs" style={{ backgroundColor: change > 0 ? '#10B98120' : '#EF444420', color: change > 0 ? '#10B981' : '#EF4444' }}>
            <TrendingUp className="w-3 h-3" />
            {Math.abs(change)}%
          </div>
        )}
      </div>
      <h3 className="text-2xl mb-1" style={{ color: '#F8FAFC' }}>{loading ? '—' : value}</h3>
      <p className="text-sm" style={{ color: '#94A3B8' }}>{title}</p>
    </div>
);

const ProcessCard = ({ name, status, cpu }: { name: string; status: RiskLevel; cpu: number }) => (
  <div className="flex items-center justify-between p-3 rounded-lg border" style={{ backgroundColor: '#0F172A', borderColor: '#334155' }}>
    <div className="flex items-center gap-3">
      <div className={`w-2 h-2 rounded-full ${status === 'safe' ? 'bg-green-500' : status === 'warning' ? 'bg-yellow-500' : 'bg-red-500'}`}></div>
      <span className="text-sm" style={{ color: '#F8FAFC' }}>{name}</span>
    </div>
    <span className="text-xs px-2 py-1 rounded" style={{ backgroundColor: '#1E293B', color: '#94A3B8' }}>{cpu.toFixed(1)}%</span>
  </div>
);

export default function Dashboard() {
  const {
    overview,
    recentProcesses,
    performanceHistory,
    threatHistory,
    networkThroughput,
    changes,
    isLoading,
    isRefreshing,
    error,
    reload,
  } = useDashboard();

  const {
    status: winSec,
    isLoading: winLoading,
    isRefreshing: winRefreshing,
    notice: winNotice,
  } = useWindowsSecurity();

  const threatChartData = threatHistory.length > 0 ? threatHistory : [{ time: '—', threats: 0 }];
  const performanceChartData =
    performanceHistory.length > 0 ? performanceHistory : [{ time: '—', cpu: 0, ram: 0 }];

  const networkBarWidth = Math.min(100, Math.max(5, (networkThroughput / (32 * 1024 * 1024)) * 100));

  const activeThreatStatus: 'danger' | 'success' | 'info' =
    (overview?.active_threats ?? 0) > 0 ? 'danger' : 'success';

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

      {winNotice && (
        <div
          className="mb-4 p-3 rounded-lg border text-sm transition-opacity duration-300"
          style={{
            backgroundColor: winNotice.type === 'success' ? '#10B98120' : '#EF444420',
            borderColor: winNotice.type === 'success' ? '#10B981' : '#EF4444',
            color: winNotice.type === 'success' ? '#6EE7B7' : '#FCA5A5',
          }}
        >
          {winNotice.message}
        </div>
      )}

      <div
        className="transition-opacity duration-300 ease-in-out"
        style={{
          opacity: isLoading || winLoading ? 0.5 : isRefreshing || winRefreshing ? 0.85 : 1,
        }}
      >
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          <StatCard icon={Shield} title="Security Score" value={`${overview?.security_score ?? 0}/100`} change={changes.securityScore} status="success" loading={isLoading} />
          <StatCard icon={AlertTriangle} title="Active Threats" value={formatNumber(overview?.active_threats ?? 0)} change={changes.activeThreats} status={activeThreatStatus} loading={isLoading} />
          <StatCard icon={CheckCircle} title="Blocked Attacks" value={formatNumber(overview?.blocked_threats ?? 0)} change={changes.blockedThreats} status="success" loading={isLoading} />
          <StatCard icon={Activity} title="Running Processes" value={formatNumber(overview?.running_processes ?? 0)} status="info" loading={isLoading} />
        </div>

        {/* Windows Security */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[
            {
              title: 'Windows Defender',
              value: windowsStatusLabel(winSec?.defender.status ?? 'unavailable'),
              sub: winSec?.defender.realtime_protection ? 'Real-time ON' : 'Real-time OFF',
              status: winSec?.defender.status ?? 'unavailable',
              icon: Shield,
            },
            {
              title: 'Firewall',
              value: windowsStatusLabel(winSec?.firewall.status ?? 'unavailable'),
              sub: winSec?.firewall.active_profile
                ? `Profile: ${winSec.firewall.active_profile}`
                : 'No active profile',
              status: winSec?.firewall.status ?? 'unavailable',
              icon: Lock,
            },
            {
              title: 'Secure Boot',
              value:
                winSec?.system_protection.secure_boot_enabled === true
                  ? 'Enabled'
                  : winSec?.system_protection.secure_boot_enabled === false
                    ? 'Disabled'
                    : 'Unavailable',
              sub: 'UEFI firmware protection',
              status:
                winSec?.system_protection.secure_boot_enabled === true
                  ? 'protected'
                  : winSec?.system_protection.secure_boot_enabled === false
                    ? 'attention_needed'
                    : 'unavailable',
              icon: CheckCircle,
            },
            {
              title: 'TPM',
              value:
                winSec?.system_protection.tpm_ready === true
                  ? 'Ready'
                  : winSec?.system_protection.tpm_present === true
                    ? 'Present'
                    : 'Unavailable',
              sub: winSec?.defender.antivirus_signature_version
                ? `Sig: ${winSec.defender.antivirus_signature_version.slice(0, 12)}…`
                : 'Signature unknown',
              status:
                winSec?.system_protection.tpm_ready === true
                  ? 'protected'
                  : winSec?.system_protection.tpm_present === true
                    ? 'attention_needed'
                    : 'unavailable',
              icon: Activity,
            },
          ].map((card) => {
            const colors = windowsStatusColors(card.status);
            const Icon = card.icon;
            return (
              <div
                key={card.title}
                className="p-4 rounded-lg border"
                style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg" style={{ backgroundColor: colors.bg }}>
                    <Icon className="w-5 h-5" style={{ color: colors.color }} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-lg truncate" style={{ color: colors.color }}>
                      {winLoading ? '—' : card.value}
                    </p>
                    <p className="text-xs" style={{ color: '#94A3B8' }}>
                      {card.title}
                    </p>
                    <p className="text-xs truncate mt-0.5" style={{ color: '#64748B' }} title={card.sub}>
                      {winLoading ? '—' : card.sub}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
            <h3 className="mb-4" style={{ color: '#F8FAFC' }}>Threat Activity (24h)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={threatChartData}>
                <defs>
                  <linearGradient id="threatGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#EF4444" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="time" stroke="#94A3B8" style={{ fontSize: '12px' }} />
                <YAxis stroke="#94A3B8" style={{ fontSize: '12px' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1E293B', border: '1px solid #334155', borderRadius: '8px', color: '#F8FAFC' }}
                />
                <Area type="monotone" dataKey="threats" stroke="#EF4444" fillOpacity={1} fill="url(#threatGradient)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
            <h3 className="mb-4" style={{ color: '#F8FAFC' }}>System Performance</h3>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={performanceChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="time" stroke="#94A3B8" style={{ fontSize: '12px' }} />
                <YAxis stroke="#94A3B8" style={{ fontSize: '12px' }} domain={[0, 100]} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1E293B', border: '1px solid #334155', borderRadius: '8px', color: '#F8FAFC' }}
                />
                <Line type="monotone" dataKey="cpu" stroke="#3B82F6" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="ram" stroke="#10B981" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
            <div className="flex items-center justify-center gap-6 mt-4">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#3B82F6' }}></div>
                <span className="text-xs" style={{ color: '#94A3B8' }}>CPU Usage</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#10B981' }}></div>
                <span className="text-xs" style={{ color: '#94A3B8' }}>RAM Usage</span>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
            <h3 className="mb-4" style={{ color: '#F8FAFC' }}>System Resources</h3>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-4 h-4" style={{ color: '#3B82F6' }} />
                    <span className="text-sm" style={{ color: '#94A3B8' }}>CPU Usage</span>
                  </div>
                  <span className="text-sm" style={{ color: '#F8FAFC' }}>
                    {isLoading ? '—' : formatPercent(overview?.cpu_usage ?? 0)}
                  </span>
                </div>
                <div className="w-full h-2 rounded-full" style={{ backgroundColor: '#0F172A' }}>
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: isLoading ? '0%' : `${overview?.cpu_usage ?? 0}%`,
                      background: 'linear-gradient(to right, #3B82F6, #60A5FA)',
                    }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <HardDrive className="w-4 h-4" style={{ color: '#10B981' }} />
                    <span className="text-sm" style={{ color: '#94A3B8' }}>RAM Usage</span>
                  </div>
                  <span className="text-sm" style={{ color: '#F8FAFC' }}>
                    {isLoading ? '—' : formatPercent(overview?.ram_usage ?? 0)}
                  </span>
                </div>
                <div className="w-full h-2 rounded-full" style={{ backgroundColor: '#0F172A' }}>
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: isLoading ? '0%' : `${overview?.ram_usage ?? 0}%`,
                      background: 'linear-gradient(to right, #10B981, #34D399)',
                    }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Wifi className="w-4 h-4" style={{ color: '#F59E0B' }} />
                    <span className="text-sm" style={{ color: '#94A3B8' }}>Network Activity</span>
                  </div>
                  <span className="text-sm" style={{ color: '#F8FAFC' }}>
                    {isLoading ? '—' : formatBytesPerSecond(networkThroughput)}
                  </span>
                </div>
                <div className="w-full h-2 rounded-full" style={{ backgroundColor: '#0F172A' }}>
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: isLoading ? '0%' : `${networkBarWidth}%`,
                      background: 'linear-gradient(to right, #F59E0B, #FBBF24)',
                    }}
                  ></div>
                </div>
              </div>
            </div>
          </div>

          <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
            <h3 className="mb-4" style={{ color: '#F8FAFC' }}>Recent Processes</h3>
            <div className="space-y-2">
              {isLoading &&
                [1, 2, 3, 4, 5].map((item) => (
                  <div key={item} className="h-12 rounded-lg animate-pulse" style={{ backgroundColor: '#0F172A' }} />
                ))}
              {!isLoading && recentProcesses.length === 0 && (
                <p className="text-sm text-center py-4" style={{ color: '#94A3B8' }}>
                  No process data available
                </p>
              )}
              {!isLoading &&
                recentProcesses.map((process) => (
                  <ProcessCard key={process.id} name={process.name} status={process.risk} cpu={process.cpu} />
                ))}
            </div>
          </div>

          <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
            <h3 className="mb-4" style={{ color: '#F8FAFC' }}>USB & Network Activity</h3>
            <div className="space-y-4">
              <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
                <div className="flex items-center gap-3 mb-2">
                  <Usb className="w-5 h-5" style={{ color: '#10B981' }} />
                  <span className="text-sm" style={{ color: '#F8FAFC' }}>USB Devices</span>
                </div>
                <p className="text-xs mb-2" style={{ color: '#94A3B8' }}>
                  {isLoading
                    ? '—'
                    : `${overview?.usb_devices_connected ?? 0} device${(overview?.usb_devices_connected ?? 0) === 1 ? '' : 's'} connected`}
                </p>
                <div className="flex gap-2">
                  <span
                    className="px-2 py-1 rounded text-xs"
                    style={{
                      backgroundColor: (overview?.active_threats ?? 0) === 0 ? '#10B98120' : '#F59E0B20',
                      color: (overview?.active_threats ?? 0) === 0 ? '#10B981' : '#F59E0B',
                    }}
                  >
                    {(overview?.active_threats ?? 0) === 0 ? 'All Safe' : 'Review Required'}
                  </span>
                </div>
              </div>
              <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
                <div className="flex items-center gap-3 mb-2">
                  <Wifi className="w-5 h-5" style={{ color: '#3B82F6' }} />
                  <span className="text-sm" style={{ color: '#F8FAFC' }}>Network Status</span>
                </div>
                <p className="text-xs mb-2" style={{ color: '#94A3B8' }}>
                  {isLoading
                    ? '—'
                    : `${formatNumber(overview?.network_connections ?? 0)} active connections`}
                </p>
                <div className="flex gap-2 flex-wrap">
                  <span className="px-2 py-1 rounded text-xs" style={{ backgroundColor: '#3B82F620', color: '#3B82F6' }}>
                    Monitored
                  </span>
                  {overview?.protection_status && (
                    <span
                      className="px-2 py-1 rounded text-xs"
                      style={{
                        backgroundColor: overview.protection_status.realtime_protection
                          ? '#10B98120'
                          : '#EF444420',
                        color: overview.protection_status.realtime_protection ? '#10B981' : '#EF4444',
                      }}
                    >
                      Defender {overview.protection_status.realtime_protection ? 'On' : 'Off'}
                    </span>
                  )}
                  {overview?.protection_status && (
                    <span
                      className="px-2 py-1 rounded text-xs"
                      style={{
                        backgroundColor: overview.protection_status.firewall
                          ? '#10B98120'
                          : '#EF444420',
                        color: overview.protection_status.firewall ? '#10B981' : '#EF4444',
                      }}
                    >
                      Firewall {overview.protection_status.firewall ? 'On' : 'Off'}
                    </span>
                  )}
                  {overview && (
                    <span
                      className="px-2 py-1 rounded text-xs"
                      style={{
                        backgroundColor: overview.system_health === 'Secure' ? '#10B98120' : '#F59E0B20',
                        color: overview.system_health === 'Secure' ? '#10B981' : '#F59E0B',
                      }}
                    >
                      {overview.system_health}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
