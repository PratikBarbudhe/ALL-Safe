import { useRef } from 'react';
import {
  Settings as SettingsIcon,
  Shield,
  Bell,
  Download,
  Palette,
  Database,
  RefreshCw,
  AlertTriangle,
  Upload,
} from 'lucide-react';
import { useWindowsSecurity } from '@/hooks/useWindowsSecurity';
import { useSettingsContext } from '@/contexts/SettingsContext';
import {
  settingsSaveStatusColors,
  settingsSaveStatusLabel,
  windowsStatusColors,
  windowsStatusLabel,
} from '@/lib/api';

const SettingToggle = ({
  title,
  description,
  checked,
  disabled,
  onChange,
}: {
  title: string;
  description: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (value: boolean) => void;
}) => (
  <div
    className="flex items-center justify-between p-4 rounded-lg"
    style={{ backgroundColor: '#0F172A' }}
  >
    <div>
      <p className="text-sm mb-1" style={{ color: '#F8FAFC' }}>
        {title}
      </p>
      <p className="text-xs" style={{ color: '#94A3B8' }}>
        {description}
      </p>
    </div>
    <label className="relative inline-block w-12 h-6 cursor-pointer">
      <input
        type="checkbox"
        className="sr-only peer"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <div
        className={`w-12 h-6 rounded-full transition-colors ${checked ? 'bg-green-500' : 'bg-gray-600'} ${disabled ? 'opacity-50' : ''}`}
      />
      <div
        className={`absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform ${checked ? 'translate-x-6' : ''}`}
      />
    </label>
  </div>
);

const OsStatusRow = ({
  title,
  description,
  status,
  detail,
}: {
  title: string;
  description: string;
  status: string;
  detail?: string;
}) => {
  const colors = windowsStatusColors(status);
  return (
    <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm mb-1" style={{ color: '#F8FAFC' }}>
            {title}
          </p>
          <p className="text-xs" style={{ color: '#94A3B8' }}>
            {description}
          </p>
          {detail && (
            <p className="text-xs mt-1 truncate" style={{ color: '#64748B' }} title={detail}>
              {detail}
            </p>
          )}
        </div>
        <span
          className="px-3 py-1 rounded-full text-xs shrink-0"
          style={{ backgroundColor: colors.bg, color: colors.color }}
        >
          {windowsStatusLabel(status)}
        </span>
      </div>
    </div>
  );
};

export default function Settings() {
  const importInputRef = useRef<HTMLInputElement>(null);
  const {
    settings,
    saveStatus,
    isLoading: settingsLoading,
    isSaving,
    error: settingsError,
    queueUpdate,
    reset,
    exportConfig,
    importConfig,
  } = useSettingsContext();

  const {
    status: winSec,
    isLoading,
    isActing,
    error,
    notice,
    reload,
    runQuickScan,
    runSignatureUpdate,
  } = useWindowsSecurity();

  const disabled = settingsLoading || isSaving || !settings;
  const statusColors = settingsSaveStatusColors(saveStatus);
  const statusLabel = settingsSaveStatusLabel(saveStatus);

  return (
    <div
      className="p-6 overflow-y-auto"
      style={{ backgroundColor: '#0F172A', height: 'calc(100vh - 4rem)' }}
    >
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
            onClick={() => void reload({ refresh: true })}
            className="px-3 py-1 rounded text-xs flex items-center gap-1 shrink-0"
            style={{ backgroundColor: '#EF4444', color: '#FFFFFF' }}
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        </div>
      )}

      {settingsError && (
        <div
          className="mb-4 p-3 rounded-lg border text-sm"
          style={{ backgroundColor: '#EF444420', borderColor: '#EF4444', color: '#FCA5A5' }}
        >
          {settingsError}
        </div>
      )}

      {notice && (
        <div
          className="mb-4 p-3 rounded-lg border text-sm"
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
        className="transition-opacity duration-300"
        style={{ opacity: isLoading || settingsLoading ? 0.6 : isActing || isSaving ? 0.85 : 1 }}
      >
        {/* Header */}
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl mb-1" style={{ color: '#F8FAFC' }}>
              Settings
            </h2>
            <p className="text-sm" style={{ color: '#94A3B8' }}>
              Configure your security preferences and system settings
            </p>
          </div>
          {statusLabel && (
            <span
              className="px-3 py-1 rounded-full text-xs shrink-0 transition-colors duration-300"
              style={{ backgroundColor: statusColors.bg, color: statusColors.color }}
            >
              {isSaving ? 'Saving…' : statusLabel}
            </span>
          )}
        </div>

        {/* Security Settings — live Windows OS status */}
        <div
          className="mb-6 p-6 rounded-xl border"
          style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}
        >
          <div className="flex items-center gap-3 mb-4">
            <Shield className="w-5 h-5" style={{ color: '#3B82F6' }} />
            <h3 style={{ color: '#F8FAFC' }}>Security Settings</h3>
          </div>
          <div className="space-y-3">
            <OsStatusRow
              title="Real-time Protection"
              description="Windows Defender real-time monitoring"
              status={winSec?.defender.status ?? 'unavailable'}
              detail={
                winSec?.defender.realtime_protection
                  ? `Engine ${winSec.defender.engine_version || '—'}`
                  : 'Protection disabled or unavailable'
              }
            />
            <OsStatusRow
              title="Windows Firewall"
              description="Native firewall profile status"
              status={winSec?.firewall.status ?? 'unavailable'}
              detail={
                winSec
                  ? `Domain ${winSec.firewall.domain_enabled ? 'On' : 'Off'} · Private ${winSec.firewall.private_enabled ? 'On' : 'Off'} · Public ${winSec.firewall.public_enabled ? 'On' : 'Off'}`
                  : undefined
              }
            />
            <OsStatusRow
              title="Tamper Protection"
              description="Defender tamper protection state"
              status={
                winSec?.defender.tamper_protection === true
                  ? 'protected'
                  : winSec?.defender.tamper_protection === false
                    ? 'attention_needed'
                    : 'unavailable'
              }
            />
            <OsStatusRow
              title="Secure Boot"
              description="UEFI Secure Boot verification"
              status={
                winSec?.system_protection.secure_boot_enabled === true
                  ? 'protected'
                  : winSec?.system_protection.secure_boot_enabled === false
                    ? 'disabled'
                    : 'unavailable'
              }
            />
            <OsStatusRow
              title="TPM"
              description="Trusted Platform Module availability"
              status={
                winSec?.system_protection.tpm_ready === true
                  ? 'protected'
                  : winSec?.system_protection.tpm_present === true
                    ? 'attention_needed'
                    : 'unavailable'
              }
            />
            <SettingToggle
              title="Ransomware Protection"
              description="AllSafe heuristic ransomware monitoring (see Ransomware page)"
              checked={settings?.ransomware.monitoring_enabled ?? true}
              disabled={disabled}
              onChange={(v) => queueUpdate('ransomware', 'monitoring_enabled', v)}
            />
            <SettingToggle
              title="USB Auto-scan"
              description="Automatically scan USB devices when connected"
              checked={settings?.usb.auto_scan_on_connect ?? true}
              disabled={disabled}
              onChange={(v) => queueUpdate('usb', 'auto_scan_on_connect', v)}
            />
            <SettingToggle
              title="USB Monitoring"
              description="Background USB device attach/detach monitoring"
              checked={settings?.usb.monitoring_enabled ?? true}
              disabled={disabled}
              onChange={(v) => queueUpdate('usb', 'monitoring_enabled', v)}
            />
            <SettingToggle
              title="Trusted USB Devices Only"
              description="Flag devices not on the trusted allow list"
              checked={settings?.usb.trusted_devices_only ?? false}
              disabled={disabled}
              onChange={(v) => queueUpdate('usb', 'trusted_devices_only', v)}
            />
          </div>
        </div>

        {/* Scan Settings */}
        <div
          className="mb-6 p-6 rounded-xl border"
          style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}
        >
          <div className="flex items-center gap-3 mb-4">
            <SettingsIcon className="w-5 h-5" style={{ color: '#10B981' }} />
            <h3 style={{ color: '#F8FAFC' }}>Scan Settings</h3>
          </div>
          <div className="space-y-4">
            <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <label className="text-sm mb-2 block" style={{ color: '#F8FAFC' }}>
                Windows Defender Actions
              </label>
              <p className="text-xs mb-3" style={{ color: '#94A3B8' }}>
                Safe actions only — uses native Windows Security APIs
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={isActing || isLoading}
                  onClick={() => void runQuickScan()}
                  className="px-4 py-2 rounded-lg text-sm disabled:opacity-50"
                  style={{ backgroundColor: '#3B82F6', color: '#FFFFFF' }}
                >
                  {isActing ? 'Running…' : 'Run Quick Scan'}
                </button>
                <button
                  type="button"
                  disabled={isActing || isLoading}
                  onClick={() => void runSignatureUpdate()}
                  className="px-4 py-2 rounded-lg text-sm disabled:opacity-50"
                  style={{ backgroundColor: '#334155', color: '#F8FAFC' }}
                >
                  Update Signatures
                </button>
              </div>
            </div>
            <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                <div>
                  <span style={{ color: '#94A3B8' }}>Last quick scan</span>
                  <p style={{ color: '#F8FAFC' }}>
                    {isLoading ? '—' : winSec?.defender.last_quick_scan || 'Never recorded'}
                  </p>
                </div>
                <div>
                  <span style={{ color: '#94A3B8' }}>Last full scan</span>
                  <p style={{ color: '#F8FAFC' }}>
                    {isLoading ? '—' : winSec?.defender.last_full_scan || 'Never recorded'}
                  </p>
                </div>
                <div>
                  <span style={{ color: '#94A3B8' }}>Signature version</span>
                  <p className="truncate" style={{ color: '#F8FAFC' }} title={winSec?.defender.antivirus_signature_version}>
                    {isLoading ? '—' : winSec?.defender.antivirus_signature_version || '—'}
                  </p>
                </div>
                <div>
                  <span style={{ color: '#94A3B8' }}>Security Center</span>
                  <p style={{ color: '#F8FAFC' }}>
                    {isLoading ? '—' : winSec?.system_protection.security_center_health || '—'}
                  </p>
                </div>
              </div>
            </div>
            <SettingToggle
              title="Scan Archives"
              description="Scan inside ZIP, RAR, and other archive files"
              checked={settings?.scan.scan_archives ?? true}
              disabled={disabled}
              onChange={(v) => queueUpdate('scan', 'scan_archives', v)}
            />
            <SettingToggle
              title="Heuristic Analysis"
              description="Detect unknown threats using behavioral patterns"
              checked={settings?.scan.heuristic_analysis ?? true}
              disabled={disabled}
              onChange={(v) => queueUpdate('scan', 'heuristic_analysis', v)}
            />
            <SettingToggle
              title="Auto-start Monitoring"
              description="Start filesystem threat monitoring when AllSafe launches"
              checked={settings?.system.auto_start_monitoring ?? true}
              disabled={disabled}
              onChange={(v) => queueUpdate('system', 'auto_start_monitoring', v)}
            />
          </div>
        </div>

        {/* Notification Settings */}
        <div
          className="mb-6 p-6 rounded-xl border"
          style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}
        >
          <div className="flex items-center gap-3 mb-4">
            <Bell className="w-5 h-5" style={{ color: '#F59E0B' }} />
            <h3 style={{ color: '#F8FAFC' }}>Notification Settings</h3>
          </div>
          <div className="space-y-3">
            <SettingToggle
              title="Threat Notifications"
              description="Alert when threats are detected"
              checked={settings?.notifications.threat_notifications ?? true}
              disabled={disabled}
              onChange={(v) => queueUpdate('notifications', 'threat_notifications', v)}
            />
            <SettingToggle
              title="Scan Complete Notifications"
              description="Notify when scans finish"
              checked={settings?.notifications.scan_complete_notifications ?? true}
              disabled={disabled}
              onChange={(v) => queueUpdate('notifications', 'scan_complete_notifications', v)}
            />
            <SettingToggle
              title="Update Notifications"
              description="Alert when updates are available"
              checked={settings?.notifications.update_notifications ?? true}
              disabled={disabled}
              onChange={(v) => queueUpdate('notifications', 'update_notifications', v)}
            />
            <SettingToggle
              title="Desktop Notifications"
              description="Show Windows toast alerts for security events"
              checked={settings?.notifications.desktop_notifications ?? true}
              disabled={disabled}
              onChange={(v) => queueUpdate('notifications', 'desktop_notifications', v)}
            />
            <SettingToggle
              title="Critical Alert Popups"
              description="Display modal alerts for critical severity events"
              checked={settings?.notifications.critical_alert_popups ?? true}
              disabled={disabled}
              onChange={(v) => queueUpdate('notifications', 'critical_alert_popups', v)}
            />
            <SettingToggle
              title="Sound Alerts"
              description="Play sounds with desktop notifications (when supported)"
              checked={settings?.notifications.sound_alerts ?? false}
              disabled={disabled}
              onChange={(v) => queueUpdate('notifications', 'sound_alerts', v)}
            />
            <SettingToggle
              title="Weekly Reports"
              description="Local weekly summary preference (stored only)"
              checked={settings?.notifications.weekly_reports ?? false}
              disabled={disabled}
              onChange={(v) => queueUpdate('notifications', 'weekly_reports', v)}
            />
          </div>
        </div>

        {/* Update Settings */}
        <div
          className="mb-6 p-6 rounded-xl border"
          style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}
        >
          <div className="flex items-center gap-3 mb-4">
            <Download className="w-5 h-5" style={{ color: '#3B82F6' }} />
            <h3 style={{ color: '#F8FAFC' }}>Update Settings</h3>
          </div>
          <div className="space-y-3">
            <SettingToggle
              title="Automatic Updates"
              description="Automatically download and install updates"
              checked={settings?.update.automatic_updates ?? true}
              disabled={disabled}
              onChange={(v) => queueUpdate('update', 'automatic_updates', v)}
            />
            <SettingToggle
              title="Auto-update Threat Database"
              description="Keep threat signatures up to date"
              checked={settings?.update.auto_update_threat_database ?? true}
              disabled={disabled}
              onChange={(v) => queueUpdate('update', 'auto_update_threat_database', v)}
            />
            <SettingToggle
              title="Beta Updates"
              description="Receive early access to new features"
              checked={settings?.update.beta_updates ?? false}
              disabled={disabled}
              onChange={(v) => queueUpdate('update', 'beta_updates', v)}
            />
            <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm" style={{ color: '#F8FAFC' }}>
                  Defender Signatures
                </span>
                <span className="text-sm" style={{ color: '#10B981' }}>
                  {isLoading
                    ? '—'
                    : winSec?.defender.antivirus_signature_version
                      ? 'Installed'
                      : 'Unknown'}
                </span>
              </div>
              <button
                type="button"
                disabled={isActing || isLoading}
                onClick={() => void runSignatureUpdate()}
                className="w-full mt-2 px-4 py-2 rounded-lg disabled:opacity-50"
                style={{ backgroundColor: '#3B82F6', color: '#FFFFFF' }}
              >
                {isActing ? 'Updating…' : 'Update Defender Signatures'}
              </button>
            </div>
          </div>
        </div>

        {/* Appearance */}
        <div
          className="mb-6 p-6 rounded-xl border"
          style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}
        >
          <div className="flex items-center gap-3 mb-4">
            <Palette className="w-5 h-5" style={{ color: '#A855F7' }} />
            <h3 style={{ color: '#F8FAFC' }}>Appearance</h3>
          </div>
          <div className="space-y-4">
            <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <label className="text-sm mb-2 block" style={{ color: '#F8FAFC' }}>
                Theme
              </label>
              <select
                className="w-full px-4 py-2 rounded-lg outline-none"
                style={{
                  backgroundColor: '#1E293B',
                  color: '#F8FAFC',
                  border: '1px solid #334155',
                }}
                value={settings?.ui.theme ?? 'dark'}
                disabled={disabled}
                onChange={(e) => queueUpdate('ui', 'theme', e.target.value)}
              >
                <option value="dark">Dark (Default)</option>
                <option value="light">Light</option>
                <option value="auto">Auto (System)</option>
              </select>
            </div>
            <div className="p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <label className="text-sm mb-2 block" style={{ color: '#F8FAFC' }}>
                Accent Color
              </label>
              <div className="flex gap-3">
                {['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#A855F7'].map((color) => (
                  <button
                    key={color}
                    type="button"
                    disabled={disabled}
                    onClick={() => queueUpdate('ui', 'accent_color', color)}
                    className="w-10 h-10 rounded-lg border-2"
                    style={{
                      backgroundColor: color,
                      borderColor:
                        (settings?.ui.accent_color ?? '#3B82F6') === color ? '#FFFFFF' : 'transparent',
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Advanced */}
        <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
          <div className="flex items-center gap-3 mb-4">
            <Database className="w-5 h-5" style={{ color: '#EF4444' }} />
            <h3 style={{ color: '#F8FAFC' }}>Advanced</h3>
          </div>
          <div className="space-y-3">
            <SettingToggle
              title="Debug Mode"
              description="Enable detailed logging for troubleshooting"
              checked={settings?.advanced.debug_mode ?? false}
              disabled={disabled}
              onChange={(v) => queueUpdate('advanced', 'debug_mode', v)}
            />
            <SettingToggle
              title="Verbose Logging"
              description="Write DEBUG-level entries to backend logs"
              checked={settings?.logging.verbose_logging ?? false}
              disabled={disabled}
              onChange={(v) => queueUpdate('logging', 'verbose_logging', v)}
            />
            <SettingToggle
              title="Background Monitoring"
              description="Keep protection services active while app is running"
              checked={settings?.system.background_monitoring ?? true}
              disabled={disabled}
              onChange={(v) => queueUpdate('system', 'background_monitoring', v)}
            />
            <SettingToggle
              title="Minimize to System Tray"
              description="Hide window to tray instead of exiting when closed"
              checked={settings?.system.minimize_to_tray ?? true}
              disabled={disabled}
              onChange={(v) => queueUpdate('system', 'minimize_to_tray', v)}
            />
            <SettingToggle
              title="Start with Windows"
              description="Launch AllSafe when Windows starts (registry Run key)"
              checked={settings?.system.auto_start_with_windows ?? false}
              disabled={disabled}
              onChange={(v) => queueUpdate('system', 'auto_start_with_windows', v)}
            />
            <SettingToggle
              title="Send Anonymous Usage Data"
              description="Help improve AllSafe by sharing usage statistics"
              checked={settings?.advanced.send_anonymous_usage_data ?? false}
              disabled={disabled}
              onChange={(v) => queueUpdate('advanced', 'send_anonymous_usage_data', v)}
            />
            <div className="p-4 rounded-lg flex flex-wrap gap-2" style={{ backgroundColor: '#0F172A' }}>
              <button
                type="button"
                disabled={disabled}
                onClick={() => void exportConfig()}
                className="px-4 py-2 rounded-lg text-sm flex items-center gap-2"
                style={{ backgroundColor: '#334155', color: '#F8FAFC' }}
              >
                <Download className="w-4 h-4" />
                Export Config
              </button>
              <button
                type="button"
                disabled={disabled}
                onClick={() => importInputRef.current?.click()}
                className="px-4 py-2 rounded-lg text-sm flex items-center gap-2"
                style={{ backgroundColor: '#334155', color: '#F8FAFC' }}
              >
                <Upload className="w-4 h-4" />
                Import Config
              </button>
              <input
                ref={importInputRef}
                type="file"
                accept="application/json,.json"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) void importConfig(file);
                  e.target.value = '';
                }}
              />
            </div>
            <div
              className="p-4 rounded-lg border"
              style={{ backgroundColor: '#0F172A', borderColor: '#334155' }}
            >
              <p className="text-sm mb-2" style={{ color: '#F8FAFC' }}>
                Danger Zone
              </p>
              <button
                type="button"
                disabled={disabled}
                onClick={() => void reset()}
                className="w-full px-4 py-2 rounded-lg disabled:opacity-50"
                style={{ backgroundColor: '#EF4444', color: '#FFFFFF' }}
              >
                Reset All Settings
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
