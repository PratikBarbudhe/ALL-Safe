import { FileText, Search, Download, AlertTriangle, ShieldCheck, XCircle, RefreshCw } from 'lucide-react';
import { useThreatLogs } from '@/hooks/useThreatLogs';
import { useModuleAlerts } from '@/contexts/NotificationContext';
import NotificationAlertStrip from './NotificationAlertStrip';

const getSeverityBadge = (severity: string) => {
  switch (severity) {
    case 'critical':
      return (
        <span className="px-3 py-1 rounded-full text-xs flex items-center gap-1" style={{ backgroundColor: '#EF444420', color: '#EF4444' }}>
          <div className="w-1.5 h-1.5 rounded-full bg-red-500"></div>
          Critical
        </span>
      );
    case 'high':
      return (
        <span className="px-3 py-1 rounded-full text-xs flex items-center gap-1" style={{ backgroundColor: '#F9731620', color: '#F97316' }}>
          <div className="w-1.5 h-1.5 rounded-full bg-orange-500"></div>
          High
        </span>
      );
    case 'medium':
      return (
        <span className="px-3 py-1 rounded-full text-xs flex items-center gap-1" style={{ backgroundColor: '#EAB30820', color: '#EAB308' }}>
          <div className="w-1.5 h-1.5 rounded-full bg-yellow-500"></div>
          Medium
        </span>
      );
    case 'low':
      return (
        <span className="px-3 py-1 rounded-full text-xs flex items-center gap-1" style={{ backgroundColor: '#3B82F620', color: '#3B82F6' }}>
          <div className="w-1.5 h-1.5 rounded-full bg-blue-500"></div>
          Low
        </span>
      );
    default:
      return (
        <span className="px-3 py-1 rounded-full text-xs" style={{ backgroundColor: '#334155', color: '#94A3B8' }}>
          {severity}
        </span>
      );
  }
};

const getActionIcon = (action: string) => {
  switch (action) {
    case 'Blocked':
      return <XCircle className="w-4 h-4" style={{ color: '#EF4444' }} />;
    case 'Quarantined':
      return <AlertTriangle className="w-4 h-4" style={{ color: '#F59E0B' }} />;
    default:
      return <ShieldCheck className="w-4 h-4" style={{ color: '#10B981' }} />;
  }
};

const CATEGORY_OPTIONS = [
  { value: 'all', label: 'All Types' },
  { value: 'File Activity', label: 'File Activity' },
  { value: 'Suspicious Executable', label: 'Suspicious Executable' },
  { value: 'Script Execution', label: 'Script Execution' },
  { value: 'Rapid Modification', label: 'Rapid Modification' },
  { value: 'Unknown File Type', label: 'Unknown File Type' },
];

export default function ThreatLogs() {
  const {
    logs,
    stats,
    page,
    total,
    totalPages,
    pageSize,
    severityFilter,
    setSeverityFilter,
    categoryFilter,
    setCategoryFilter,
    search,
    setSearch,
    isLoading,
    isRefreshing,
    error,
    reload,
    goToPage,
  } = useThreatLogs();

  const { criticalCount, latest: threatAlert } = useModuleAlerts('Threat Detection');

  const startIndex = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const endIndex = Math.min(page * pageSize, total);

  const handleExport = () => {
    if (logs.length === 0) return;
    const header = 'Timestamp,Type,Threat Name,Severity,Action,Source\n';
    const rows = logs
      .map(
        (log) =>
          `"${log.timestamp}","${log.type}","${log.threat}","${log.severity}","${log.action}","${log.source}"`,
      )
      .join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `allsafe-threat-logs-page-${page}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const pageNumbers = Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1);

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

      {criticalCount > 0 && threatAlert && (
        <NotificationAlertStrip
          severity={threatAlert.severity}
          message={`${criticalCount} unread threat alert${criticalCount === 1 ? '' : 's'} — ${threatAlert.title}`}
        />
      )}

      <div
        className="transition-opacity duration-300 ease-in-out"
        style={{ opacity: isLoading ? 0.5 : isRefreshing ? 0.85 : 1 }}
      >
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-2xl mb-1" style={{ color: '#F8FAFC' }}>Threat Logs</h2>
              <p className="text-sm" style={{ color: '#94A3B8' }}>Complete history of detected and blocked threats</p>
            </div>
            <button
              type="button"
              onClick={handleExport}
              disabled={logs.length === 0}
              className="px-4 py-2 rounded-lg flex items-center gap-2 disabled:opacity-50"
              style={{ backgroundColor: '#3B82F6', color: '#FFFFFF' }}
            >
              <Download className="w-4 h-4" />
              Export Logs
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: '#EF444420' }}>
                  <AlertTriangle className="w-5 h-5" style={{ color: '#EF4444' }} />
                </div>
                <div>
                  <p className="text-2xl" style={{ color: '#F8FAFC' }}>
                    {isLoading ? '—' : (stats?.total_threats ?? 0).toLocaleString()}
                  </p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>Total Threats</p>
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
                    {isLoading ? '—' : stats?.critical_count ?? 0}
                  </p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>Critical</p>
                </div>
              </div>
            </div>
            <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: '#F9731620' }}>
                  <AlertTriangle className="w-5 h-5" style={{ color: '#F97316' }} />
                </div>
                <div>
                  <p className="text-2xl" style={{ color: '#F97316' }}>
                    {isLoading ? '—' : stats?.high_count ?? 0}
                  </p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>High</p>
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
                    {isLoading ? '—' : `${stats?.detection_rate_percent ?? 100}%`}
                  </p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>Success Rate</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="mb-4 flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4" style={{ color: '#94A3B8' }} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search logs by threat name, type, or source..."
              className="w-full pl-10 pr-4 py-2 rounded-lg outline-none"
              style={{
                backgroundColor: '#1E293B',
                color: '#F8FAFC',
                border: '1px solid #334155',
              }}
            />
          </div>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-4 py-2 rounded-lg outline-none"
            style={{ backgroundColor: '#1E293B', color: '#F8FAFC', border: '1px solid #334155' }}
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical Only</option>
            <option value="high">High Only</option>
            <option value="medium">Medium Only</option>
            <option value="low">Low Only</option>
          </select>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-4 py-2 rounded-lg outline-none"
            style={{ backgroundColor: '#1E293B', color: '#F8FAFC', border: '1px solid #334155' }}
          >
            {CATEGORY_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Logs Table */}
        <div className="rounded-xl border overflow-hidden" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr style={{ backgroundColor: '#0F172A', borderBottom: '1px solid #334155' }}>
                  <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>Timestamp</th>
                  <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>Type</th>
                  <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>Threat Name</th>
                  <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>Severity</th>
                  <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>Action Taken</th>
                  <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>Source</th>
                </tr>
              </thead>
              <tbody>
                {!isLoading && logs.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-sm" style={{ color: '#94A3B8' }}>
                      No threat events recorded yet. File system monitoring is active — activity will appear here in real time.
                    </td>
                  </tr>
                )}
                {logs.map((log, index) => (
                  <tr
                    key={log.id}
                    style={{
                      borderBottom: index < logs.length - 1 ? '1px solid #334155' : 'none',
                      backgroundColor: log.severity === 'critical' ? '#EF44441A' : 'transparent',
                    }}
                    className="hover:bg-opacity-50 transition-colors"
                  >
                    <td className="px-6 py-4" style={{ color: '#94A3B8' }}>
                      <div className="text-sm">{log.timestamp}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 rounded text-xs" style={{ backgroundColor: '#334155', color: '#F8FAFC' }}>
                        {log.type}
                      </span>
                    </td>
                    <td className="px-6 py-4" style={{ color: '#F8FAFC' }}>
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 shrink-0" style={{ color: '#94A3B8' }} />
                        <span className="text-sm truncate max-w-xs" title={log.threat}>
                          {log.threat}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">{getSeverityBadge(log.severity)}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {getActionIcon(log.action)}
                        <span className="text-sm" style={{ color: '#F8FAFC' }}>{log.action}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4" style={{ color: '#94A3B8' }}>{log.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pagination */}
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm" style={{ color: '#94A3B8' }}>
            {total === 0
              ? 'No threats to display'
              : `Showing ${startIndex}-${endIndex} of ${total.toLocaleString()} threats`}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => goToPage(page - 1)}
              className="px-3 py-2 rounded-lg text-sm disabled:opacity-40"
              style={{ backgroundColor: '#1E293B', color: '#F8FAFC' }}
            >
              Previous
            </button>
            {pageNumbers.map((num) => (
              <button
                key={num}
                type="button"
                onClick={() => goToPage(num)}
                className="px-3 py-2 rounded-lg text-sm"
                style={{
                  backgroundColor: num === page ? '#3B82F6' : '#1E293B',
                  color: num === page ? '#FFFFFF' : '#F8FAFC',
                }}
              >
                {num}
              </button>
            ))}
            <button
              type="button"
              disabled={page >= totalPages || totalPages === 0}
              onClick={() => goToPage(page + 1)}
              className="px-3 py-2 rounded-lg text-sm disabled:opacity-40"
              style={{ backgroundColor: '#1E293B', color: '#F8FAFC' }}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
