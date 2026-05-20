import { useRef, useState } from 'react';
import {
  Archive,
  Trash2,
  RotateCcw,
  Download,
  Search,
  Upload,
  AlertTriangle,
  RefreshCw,
  X,
  FileText,
} from 'lucide-react';
import { useQuarantine } from '@/hooks/useQuarantine';
import { formatQuarantineSize, type QuarantineItemViewModel } from '@/lib/api';

const getRiskBadge = (risk: string) => {
  switch (risk) {
    case 'critical':
      return (
        <span
          className="px-3 py-1 rounded-full text-xs flex items-center gap-1 w-fit"
          style={{ backgroundColor: '#EF444420', color: '#EF4444' }}
        >
          <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
          Critical
        </span>
      );
    case 'high':
      return (
        <span
          className="px-3 py-1 rounded-full text-xs flex items-center gap-1 w-fit"
          style={{ backgroundColor: '#F9731620', color: '#F97316' }}
        >
          <div className="w-1.5 h-1.5 rounded-full bg-orange-500" />
          High
        </span>
      );
    case 'medium':
      return (
        <span
          className="px-3 py-1 rounded-full text-xs flex items-center gap-1 w-fit"
          style={{ backgroundColor: '#EAB30820', color: '#EAB308' }}
        >
          <div className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
          Medium
        </span>
      );
    case 'low':
      return (
        <span
          className="px-3 py-1 rounded-full text-xs flex items-center gap-1 w-fit"
          style={{ backgroundColor: '#3B82F620', color: '#3B82F6' }}
        >
          <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
          Low
        </span>
      );
    default:
      return (
        <span className="px-3 py-1 rounded-full text-xs w-fit" style={{ backgroundColor: '#334155', color: '#94A3B8' }}>
          {risk}
        </span>
      );
  }
};

const getStatusBadge = (status: string) => {
  switch (status) {
    case 'quarantined':
      return (
        <span className="px-2 py-0.5 rounded text-xs" style={{ backgroundColor: '#3B82F620', color: '#3B82F6' }}>
          Quarantined
        </span>
      );
    case 'restored':
      return (
        <span className="px-2 py-0.5 rounded text-xs" style={{ backgroundColor: '#10B98120', color: '#10B981' }}>
          Restored
        </span>
      );
    case 'deleted':
      return (
        <span className="px-2 py-0.5 rounded text-xs" style={{ backgroundColor: '#EF444420', color: '#EF4444' }}>
          Deleted
        </span>
      );
    default:
      return (
        <span className="px-2 py-0.5 rounded text-xs" style={{ backgroundColor: '#334155', color: '#94A3B8' }}>
          {status}
        </span>
      );
  }
};

export default function Quarantine() {
  const {
    items,
    stats,
    search,
    setSearch,
    severityFilter,
    setSeverityFilter,
    isLoading,
    isRefreshing,
    isActing,
    error,
    notice,
    reload,
    restoreItem,
    deleteItem,
    clearAll,
    quarantineByPath,
    quarantineUpload,
    exportCsv,
  } = useQuarantine();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [detailsItem, setDetailsItem] = useState<QuarantineItemViewModel | null>(null);
  const [confirmAction, setConfirmAction] = useState<{
    type: 'restore' | 'delete' | 'clear';
    id?: number;
    name?: string;
  } | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [pathInput, setPathInput] = useState('');

  const handleConfirm = () => {
    if (!confirmAction) return;
    if (confirmAction.type === 'clear') {
      void clearAll();
    } else if (confirmAction.type === 'restore' && confirmAction.id) {
      void restoreItem(confirmAction.id);
    } else if (confirmAction.type === 'delete' && confirmAction.id) {
      void deleteItem(confirmAction.id);
    }
    setConfirmAction(null);
  };

  const handleAddByPath = () => {
    if (!pathInput.trim()) return;
    void quarantineByPath(pathInput.trim());
    setPathInput('');
    setShowAddModal(false);
  };

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
                Quarantine
              </h2>
              <p className="text-sm" style={{ color: '#94A3B8' }}>
                Isolated threats and suspicious files
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setShowAddModal(true)}
                disabled={isActing}
                className="px-4 py-2 rounded-lg flex items-center gap-2 disabled:opacity-50"
                style={{ backgroundColor: '#3B82F6', color: '#FFFFFF' }}
              >
                <Upload className="w-4 h-4" />
                Quarantine File
              </button>
              <button
                type="button"
                onClick={exportCsv}
                disabled={items.length === 0}
                className="px-4 py-2 rounded-lg flex items-center gap-2 disabled:opacity-50"
                style={{ backgroundColor: '#334155', color: '#F8FAFC' }}
              >
                <Download className="w-4 h-4" />
                Export
              </button>
              <button
                type="button"
                onClick={() => setConfirmAction({ type: 'clear' })}
                disabled={isActing || (stats?.active_count ?? 0) === 0}
                className="px-4 py-2 rounded-lg flex items-center gap-2 disabled:opacity-50"
                style={{ backgroundColor: '#EF4444', color: '#FFFFFF' }}
              >
                <Trash2 className="w-4 h-4" />
                Clear All
              </button>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: '#3B82F620' }}>
                  <Archive className="w-5 h-5" style={{ color: '#3B82F6' }} />
                </div>
                <div>
                  <p className="text-2xl" style={{ color: '#F8FAFC' }}>
                    {isLoading ? '—' : stats?.active_count ?? 0}
                  </p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>
                    Quarantined Items
                  </p>
                </div>
              </div>
            </div>
            <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: '#EF444420' }}>
                  <Archive className="w-5 h-5" style={{ color: '#EF4444' }} />
                </div>
                <div>
                  <p className="text-2xl" style={{ color: '#EF4444' }}>
                    {isLoading ? '—' : stats?.critical_count ?? 0}
                  </p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>
                    Critical Threats
                  </p>
                </div>
              </div>
            </div>
            <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: '#10B98120' }}>
                  <Archive className="w-5 h-5" style={{ color: '#10B981' }} />
                </div>
                <div>
                  <p className="text-2xl" style={{ color: '#F8FAFC' }}>
                    {isLoading ? '—' : formatQuarantineSize(stats?.total_size_bytes ?? 0)}
                  </p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>
                    Total Size
                  </p>
                </div>
              </div>
            </div>
            <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: '#F59E0B20' }}>
                  <Archive className="w-5 h-5" style={{ color: '#F59E0B' }} />
                </div>
                <div>
                  <p className="text-2xl" style={{ color: '#F8FAFC' }}>
                    {isLoading ? '—' : stats?.total_quarantined_ever ?? 0}
                  </p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>
                    Total Quarantined
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Search and filter */}
        <div className="mb-4 flex gap-4">
          <div className="flex-1 relative">
            <Search
              className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4"
              style={{ color: '#94A3B8' }}
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by file name, path, or reason..."
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
        </div>

        {/* Quarantine Table */}
        <div
          className="rounded-xl border overflow-hidden"
          style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}
        >
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr style={{ backgroundColor: '#0F172A', borderBottom: '1px solid #334155' }}>
                  <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>
                    File Name
                  </th>
                  <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>
                    Threat Type
                  </th>
                  <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>
                    Quarantined Date
                  </th>
                  <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>
                    Size
                  </th>
                  <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>
                    Risk Level
                  </th>
                  <th className="px-6 py-4 text-left text-xs uppercase tracking-wider" style={{ color: '#94A3B8' }}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {!isLoading && items.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-sm" style={{ color: '#94A3B8' }}>
                      No quarantined files. Use &quot;Quarantine File&quot; to isolate a suspicious file for testing.
                    </td>
                  </tr>
                )}
                {items.map((item, index) => (
                  <tr
                    key={item.id}
                    style={{
                      borderBottom: index < items.length - 1 ? '1px solid #334155' : 'none',
                      backgroundColor: item.risk === 'critical' ? '#EF44441A' : 'transparent',
                    }}
                    className="hover:bg-opacity-50 transition-colors cursor-pointer"
                    onClick={() => setDetailsItem(item)}
                  >
                    <td className="px-6 py-4" style={{ color: '#F8FAFC' }}>
                      <div className="flex items-center gap-2">
                        <Archive className="w-4 h-4 shrink-0" style={{ color: '#94A3B8' }} />
                        <span className="text-sm">{item.name}</span>
                        {getStatusBadge(item.status)}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 rounded text-xs" style={{ backgroundColor: '#334155', color: '#F8FAFC' }}>
                        {item.type}
                      </span>
                    </td>
                    <td className="px-6 py-4" style={{ color: '#94A3B8' }}>
                      {item.date}
                    </td>
                    <td className="px-6 py-4" style={{ color: '#94A3B8' }}>
                      {item.size}
                    </td>
                    <td className="px-6 py-4">{getRiskBadge(item.risk)}</td>
                    <td className="px-6 py-4" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          disabled={isActing}
                          onClick={() =>
                            setConfirmAction({ type: 'restore', id: item.id, name: item.name })
                          }
                          className="p-2 rounded hover:bg-opacity-80 disabled:opacity-40"
                          style={{ backgroundColor: '#334155' }}
                          title="Restore"
                        >
                          <RotateCcw className="w-4 h-4" style={{ color: '#10B981' }} />
                        </button>
                        <button
                          type="button"
                          disabled={isActing}
                          onClick={() =>
                            setConfirmAction({ type: 'delete', id: item.id, name: item.name })
                          }
                          className="p-2 rounded hover:bg-opacity-80 disabled:opacity-40"
                          style={{ backgroundColor: '#334155' }}
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" style={{ color: '#EF4444' }} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Details modal */}
      {detailsItem && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.85)' }}
          onClick={() => setDetailsItem(null)}
        >
          <div
            className="w-full max-w-lg rounded-xl border p-6"
            style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5" style={{ color: '#3B82F6' }} />
                <h3 className="text-lg" style={{ color: '#F8FAFC' }}>
                  File Details
                </h3>
              </div>
              <button type="button" onClick={() => setDetailsItem(null)} className="p-1 rounded" style={{ color: '#94A3B8' }}>
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-3 text-sm">
              <DetailRow label="File Name" value={detailsItem.name} />
              <DetailRow label="Threat Type" value={detailsItem.type} />
              <DetailRow label="Risk Level" value={detailsItem.risk} />
              <DetailRow label="Status" value={detailsItem.status} />
              <DetailRow label="Quarantined" value={detailsItem.date} />
              <DetailRow label="Size" value={detailsItem.size} />
              <DetailRow label="Reason" value={detailsItem.reason} />
              <DetailRow label="Original Path" value={detailsItem.originalPath} mono />
              <DetailRow label="SHA-256" value={detailsItem.fileHash} mono truncate />
            </div>
          </div>
        </div>
      )}

      {/* Confirm dialog */}
      {confirmAction && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.85)' }}
        >
          <div
            className="w-full max-w-md rounded-xl border p-6"
            style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}
          >
            <h3 className="text-lg mb-2" style={{ color: '#F8FAFC' }}>
              Confirm Action
            </h3>
            <p className="text-sm mb-6" style={{ color: '#94A3B8' }}>
              {confirmAction.type === 'clear' &&
                'Permanently delete all quarantined files? This cannot be undone.'}
              {confirmAction.type === 'restore' &&
                `Restore "${confirmAction.name}" to its original location?`}
              {confirmAction.type === 'delete' &&
                `Permanently delete "${confirmAction.name}" from quarantine?`}
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmAction(null)}
                className="px-4 py-2 rounded-lg text-sm"
                style={{ backgroundColor: '#334155', color: '#F8FAFC' }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                disabled={isActing}
                className="px-4 py-2 rounded-lg text-sm disabled:opacity-50"
                style={{
                  backgroundColor: confirmAction.type === 'restore' ? '#10B981' : '#EF4444',
                  color: '#FFFFFF',
                }}
              >
                {confirmAction.type === 'restore' ? 'Restore' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add / test quarantine modal */}
      {showAddModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.85)' }}
        >
          <div
            className="w-full max-w-lg rounded-xl border p-6"
            style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg" style={{ color: '#F8FAFC' }}>
                Quarantine File (Test)
              </h3>
              <button type="button" onClick={() => setShowAddModal(false)} style={{ color: '#94A3B8' }}>
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-xs mb-4" style={{ color: '#94A3B8' }}>
              Upload a file or enter an absolute Windows path. The file will be moved into secure quarantine storage.
            </p>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  void quarantineUpload(file);
                  setShowAddModal(false);
                }
                e.target.value = '';
              }}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isActing}
              className="w-full mb-4 px-4 py-3 rounded-lg flex items-center justify-center gap-2 disabled:opacity-50"
              style={{ backgroundColor: '#334155', color: '#F8FAFC' }}
            >
              <Upload className="w-4 h-4" />
              Choose File to Upload
            </button>
            <div className="text-xs mb-2 text-center" style={{ color: '#64748B' }}>
              — or quarantine by path —
            </div>
            <input
              type="text"
              value={pathInput}
              onChange={(e) => setPathInput(e.target.value)}
              placeholder="C:\Users\You\Downloads\suspicious.exe"
              className="w-full px-4 py-2 rounded-lg outline-none mb-4"
              style={{
                backgroundColor: '#0F172A',
                color: '#F8FAFC',
                border: '1px solid #334155',
              }}
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 rounded-lg text-sm"
                style={{ backgroundColor: '#334155', color: '#F8FAFC' }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleAddByPath}
                disabled={isActing || !pathInput.trim()}
                className="px-4 py-2 rounded-lg text-sm disabled:opacity-50"
                style={{ backgroundColor: '#3B82F6', color: '#FFFFFF' }}
              >
                Quarantine by Path
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function DetailRow({
  label,
  value,
  mono,
  truncate,
}: {
  label: string;
  value: string;
  mono?: boolean;
  truncate?: boolean;
}) {
  return (
    <div>
      <p className="text-xs mb-0.5" style={{ color: '#64748B' }}>
        {label}
      </p>
      <p
        className={`${mono ? 'font-mono text-xs' : ''} ${truncate ? 'truncate' : 'break-all'}`}
        style={{ color: '#F8FAFC' }}
        title={value}
      >
        {value}
      </p>
    </div>
  );
}
