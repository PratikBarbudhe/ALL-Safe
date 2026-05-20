import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, Search, XCircle, ShieldCheck, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  ApiError,
  REFRESH_INTERVAL_MS,
  fetchProcesses,
  mapProcessesResponse,
  type ProcessViewModel,
  type RiskLevel,
} from '@/lib/api';

const getRiskBadge = (risk: string) => {
  switch (risk) {
    case 'safe':
      return (
        <span className="px-3 py-1 rounded-full text-xs flex items-center gap-1 w-fit" style={{ backgroundColor: '#10B98120', color: '#10B981' }}>
          <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
          Safe
        </span>
      );
    case 'warning':
      return (
        <span className="px-3 py-1 rounded-full text-xs flex items-center gap-1 w-fit" style={{ backgroundColor: '#F59E0B20', color: '#F59E0B' }}>
          <div className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
          Suspicious
        </span>
      );
    case 'dangerous':
      return (
        <span className="px-3 py-1 rounded-full text-xs flex items-center gap-1 w-fit" style={{ backgroundColor: '#EF444420', color: '#EF4444' }}>
          <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
          Dangerous
        </span>
      );
  }
};

export default function ProcessMonitor() {
  const [processes, setProcesses] = useState<ProcessViewModel[]>([]);
  const [totalProcesses, setTotalProcesses] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState<'all' | RiskLevel>('all');

  const loadProcesses = useCallback(async (options?: { silent?: boolean }) => {
    const silent = options?.silent ?? false;
    if (silent) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const response = await fetchProcesses();
      setProcesses(mapProcessesResponse(response));
      setTotalProcesses(response.total_processes);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Failed to load processes';
      setError(message);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadProcesses();
    const intervalId = window.setInterval(() => {
      void loadProcesses({ silent: true });
    }, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(intervalId);
  }, [loadProcesses]);

  const filteredProcesses = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return processes.filter((process) => {
      const matchesSearch =
        !query ||
        process.name.toLowerCase().includes(query) ||
        String(process.pid).includes(query);
      const matchesRisk = riskFilter === 'all' || process.risk === riskFilter;
      return matchesSearch && matchesRisk;
    });
  }, [processes, searchQuery, riskFilter]);

  const riskCounts = useMemo(() => {
    return processes.reduce(
      (acc, process) => {
        acc[process.risk] += 1;
        return acc;
      },
      { safe: 0, warning: 0, dangerous: 0 } as Record<RiskLevel, number>,
    );
  }, [processes]);

  const tableOpacity = isLoading ? 0.45 : isRefreshing ? 0.7 : 1;

  return (
    <div className="p-6 overflow-y-auto" style={{ backgroundColor: '#0F172A', height: 'calc(100vh - 4rem)' }}>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl mb-1" style={{ color: '#F8FAFC' }}>Process Monitor</h2>
            <p className="text-sm" style={{ color: '#94A3B8' }}>Real-time monitoring of all running processes</p>
          </div>
          <button
            type="button"
            onClick={() => void loadProcesses({ silent: true })}
            disabled={isLoading || isRefreshing}
            className="px-4 py-2 rounded-lg flex items-center gap-2 disabled:opacity-60"
            style={{ backgroundColor: '#3B82F6', color: '#FFFFFF' }}
          >
            <Activity className={`w-4 h-4 ${isRefreshing ? 'animate-pulse' : ''}`} />
            {isRefreshing ? 'Scanning...' : 'Scan All Processes'}
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg" style={{ backgroundColor: '#3B82F620' }}>
                <Activity className="w-5 h-5" style={{ color: '#3B82F6' }} />
              </div>
              <div>
                <p className="text-2xl" style={{ color: '#F8FAFC' }}>
                  {isLoading ? '—' : totalProcesses}
                </p>
                <p className="text-xs" style={{ color: '#94A3B8' }}>Total Processes</p>
              </div>
            </div>
          </div>
          <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg" style={{ backgroundColor: '#10B98120' }}>
                <ShieldCheck className="w-5 h-5" style={{ color: '#10B981' }} />
              </div>
              <div>
                <p className="text-2xl" style={{ color: '#10B981' }}>
                  {isLoading ? '—' : riskCounts.safe}
                </p>
                <p className="text-xs" style={{ color: '#94A3B8' }}>Safe</p>
              </div>
            </div>
          </div>
          <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg" style={{ backgroundColor: '#F59E0B20' }}>
                <AlertTriangle className="w-5 h-5" style={{ color: '#F59E0B' }} />
              </div>
              <div>
                <p className="text-2xl" style={{ color: '#F59E0B' }}>
                  {isLoading ? '—' : riskCounts.warning}
                </p>
                <p className="text-xs" style={{ color: '#94A3B8' }}>Suspicious</p>
              </div>
            </div>
          </div>
          <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg" style={{ backgroundColor: '#EF444420' }}>
                <XCircle className="w-5 h-5" style={{ color: '#EF4444' }} />
              </div>
              <div>
                <p className="text-2xl" style={{ color: '#EF4444' }}>
                  {isLoading ? '—' : riskCounts.dangerous}
                </p>
                <p className="text-xs" style={{ color: '#94A3B8' }}>Threats</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div
          className="mb-4 p-4 rounded-lg border flex items-center justify-between gap-4"
          style={{ backgroundColor: '#EF444420', borderColor: '#EF4444', color: '#FCA5A5' }}
        >
          <div className="flex items-center gap-2 text-sm">
            <XCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={() => void loadProcesses()}
            className="px-3 py-1 rounded text-xs flex items-center gap-1 shrink-0"
            style={{ backgroundColor: '#EF4444', color: '#FFFFFF' }}
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        </div>
      )}

      {/* Search and Filters */}
      <div className="mb-4 flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4" style={{ color: '#94A3B8' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by process name or PID..."
            className="w-full pl-10 pr-4 py-2 rounded-lg outline-none"
            style={{
              backgroundColor: '#1E293B',
              color: '#F8FAFC',
              border: '1px solid #334155',
            }}
          />
        </div>
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value as 'all' | RiskLevel)}
          className="px-4 py-2 rounded-lg outline-none"
          style={{ backgroundColor: '#1E293B', color: '#F8FAFC', border: '1px solid #334155' }}
        >
          <option value="all">All Processes</option>
          <option value="safe">Safe Only</option>
          <option value="warning">Suspicious Only</option>
          <option value="dangerous">Dangerous Only</option>
        </select>
      </div>

      {/* Process Table */}
      <div className="rounded-xl border overflow-hidden relative" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
        {isLoading && (
          <div
            className="absolute inset-0 z-10 flex items-center justify-center"
            style={{ backgroundColor: '#1E293BCC' }}
          >
            <div className="flex items-center gap-2 text-sm" style={{ color: '#94A3B8' }}>
              <RefreshCw className="w-4 h-4 animate-spin" />
              Loading processes...
            </div>
          </div>
        )}
        <div
          className="overflow-x-auto transition-opacity duration-300 ease-in-out"
          style={{ opacity: tableOpacity }}
        >
          <table className="w-full">
            <thead>
              <tr style={{ backgroundColor: '#0F172A', borderBottom: '1px solid #334155' }}>
                <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>Process Name</th>
                <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>PID</th>
                <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>CPU %</th>
                <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>Memory (MB)</th>
                <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>Risk Level</th>
                <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>Status</th>
                <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {!isLoading && filteredProcesses.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-sm" style={{ color: '#94A3B8' }}>
                    {error ? 'No process data available.' : 'No processes match your filters.'}
                  </td>
                </tr>
              )}
              {filteredProcesses.map((process, index) => (
                <tr
                  key={process.id}
                  style={{
                    borderBottom: index < filteredProcesses.length - 1 ? '1px solid #334155' : 'none',
                    backgroundColor: process.risk === 'dangerous' ? '#EF44441A' : 'transparent',
                  }}
                  className="hover:bg-opacity-50 transition-colors"
                >
                  <td className="px-6 py-4" style={{ color: '#F8FAFC' }}>
                    <div className="flex items-center gap-2">
                      <Activity className="w-4 h-4" style={{ color: '#94A3B8' }} />
                      {process.name}
                    </div>
                  </td>
                  <td className="px-6 py-4" style={{ color: '#94A3B8' }}>{process.pid}</td>
                  <td className="px-6 py-4" style={{ color: '#F8FAFC' }}>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 rounded-full max-w-[60px]" style={{ backgroundColor: '#0F172A' }}>
                        <div
                          className="h-full rounded-full transition-all duration-300"
                          style={{
                            width: `${Math.min(process.cpu, 100)}%`,
                            backgroundColor: process.cpu > 50 ? '#EF4444' : process.cpu > 25 ? '#F59E0B' : '#10B981',
                          }}
                        ></div>
                      </div>
                      <span className="text-sm">{process.cpu.toFixed(1)}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4" style={{ color: '#94A3B8' }}>{process.memory} MB</td>
                  <td className="px-6 py-4">{getRiskBadge(process.risk)}</td>
                  <td className="px-6 py-4" style={{ color: '#10B981' }}>{process.status}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {process.risk === 'dangerous' ? (
                        <button type="button" className="px-3 py-1 rounded text-xs" style={{ backgroundColor: '#EF4444', color: '#FFFFFF' }}>
                          Terminate
                        </button>
                      ) : (
                        <button type="button" className="px-3 py-1 rounded text-xs" style={{ backgroundColor: '#334155', color: '#94A3B8' }}>
                          Details
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
