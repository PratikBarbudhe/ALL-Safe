const API_BASE_URL =
  import.meta.env.VITE_API_URL?.replace(/\/$/, '') ?? 'http://127.0.0.1:8000';

const REFRESH_INTERVAL_MS = 5000;

export { API_BASE_URL, REFRESH_INTERVAL_MS };

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export interface ProcessInfo {
  pid: number;
  process_name: string;
  cpu_percent: number;
  memory_percent: number;
  status: string;
  username: string;
  executable_path: string;
  create_time: number;
}

export interface ProcessListResponse {
  processes: ProcessInfo[];
  total_processes: number;
  system_memory_total_bytes: number;
}

export type RiskLevel = 'safe' | 'warning' | 'dangerous';

export interface ProcessViewModel {
  id: number;
  name: string;
  pid: number;
  cpu: number;
  memory: number;
  risk: RiskLevel;
  status: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        detail = body.detail;
      }
    } catch {
      // ignore JSON parse errors
    }
    throw new ApiError(detail || `Request failed (${response.status})`, response.status);
  }

  return response.json() as Promise<T>;
}

export async function fetchProcesses(): Promise<ProcessListResponse> {
  return request<ProcessListResponse>('/processes');
}

export interface NetworkActivity {
  sent: number;
  received: number;
}

export interface ProtectionStatus {
  realtime_protection: boolean;
  firewall: boolean;
  windows_defender: boolean;
}

export interface DashboardOverview {
  system_health: string;
  cpu_usage: number;
  ram_usage: number;
  disk_usage: number;
  network_activity: NetworkActivity;
  running_processes: number;
  uptime: string;
  active_threats: number;
  blocked_threats: number;
  quarantined_files: number;
  usb_devices_connected: number;
  last_scan_time: string;
  protection_status: ProtectionStatus;
  security_score: number;
  network_connections: number;
}

export async function fetchDashboardOverview(): Promise<DashboardOverview> {
  return request<DashboardOverview>('/dashboard/overview');
}

export const USB_REFRESH_INTERVAL_MS = 3000;
export const THREAT_REFRESH_INTERVAL_MS = 3000;
export const QUARANTINE_REFRESH_INTERVAL_MS = 3000;
export const RANSOMWARE_REFRESH_INTERVAL_MS = 3000;
export const WINDOWS_SECURITY_REFRESH_INTERVAL_MS = 5000;

export interface DefenderStatus {
  available: boolean;
  status: string;
  realtime_protection: boolean;
  antivirus_enabled: boolean;
  antispyware_enabled: boolean;
  service_running: boolean;
  engine_version: string;
  antivirus_signature_version: string;
  antispyware_signature_version: string;
  last_quick_scan: string;
  last_full_scan: string;
  quick_scan_age_hours: number | null;
  tamper_protection: boolean | null;
  threat_protection: string;
}

export interface FirewallProfileStatus {
  name: string;
  enabled: boolean;
  default_inbound: string;
  default_outbound: string;
}

export interface FirewallStatus {
  available: boolean;
  status: string;
  enabled: boolean;
  active_profile: string;
  domain_enabled: boolean;
  private_enabled: boolean;
  public_enabled: boolean;
  profiles: FirewallProfileStatus[];
}

export interface SystemProtectionStatus {
  available: boolean;
  status: string;
  smartscreen_enabled: boolean | null;
  uac_enabled: boolean | null;
  secure_boot_enabled: boolean | null;
  tpm_present: boolean | null;
  tpm_ready: boolean | null;
  security_center_health: string;
}

export interface WindowsSecurityStatus {
  overall_status: string;
  defender: DefenderStatus;
  firewall: FirewallStatus;
  system_protection: SystemProtectionStatus;
  collected_at: string;
}

export async function fetchWindowsSecurityStatus(
  refresh = false,
): Promise<WindowsSecurityStatus> {
  return request<WindowsSecurityStatus>(
    `/windows-security/status${refresh ? '?refresh=true' : ''}`,
  );
}

export async function fetchWindowsDefenderStatus(): Promise<DefenderStatus> {
  return request<DefenderStatus>('/windows-security/defender');
}

export async function fetchWindowsFirewallStatus(): Promise<FirewallStatus> {
  return request<FirewallStatus>('/windows-security/firewall');
}

export async function triggerDefenderQuickScan(): Promise<{
  status: string;
  message: string;
  job_started: boolean;
}> {
  return request('/windows-security/quick-scan', { method: 'POST' });
}

export async function updateDefenderSignatures(): Promise<{
  status: string;
  message: string;
  job_started: boolean;
}> {
  return request('/windows-security/update-signatures', { method: 'POST' });
}

export function windowsStatusLabel(status: string): string {
  switch (status) {
    case 'protected':
      return 'Protected';
    case 'attention_needed':
      return 'Attention Needed';
    case 'disabled':
      return 'Disabled';
    default:
      return 'Unavailable';
  }
}

export function windowsStatusColors(status: string): { bg: string; color: string } {
  switch (status) {
    case 'protected':
      return { bg: '#10B98120', color: '#10B981' };
    case 'attention_needed':
      return { bg: '#F59E0B20', color: '#F59E0B' };
    case 'disabled':
      return { bg: '#EF444420', color: '#EF4444' };
    default:
      return { bg: '#334155', color: '#94A3B8' };
  }
}

export interface ThreatLogEntry {
  id: number;
  timestamp: string;
  file_path: string;
  event_type: string;
  severity: string;
  category: string;
  process_name: string;
  status: string;
  description: string;
}

export interface ThreatLogListResponse {
  logs: ThreatLogEntry[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ThreatStats {
  total_threats: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  active_threats: number;
  blocked_threats: number;
  events_last_24h: number;
  detection_rate_percent: number;
  monitoring_active: boolean;
  watched_paths: string[];
}

export interface ThreatLogQuery {
  page?: number;
  page_size?: number;
  severity?: string;
  category?: string;
  search?: string;
}

export interface ThreatLogViewModel {
  id: number;
  timestamp: string;
  type: string;
  severity: string;
  threat: string;
  action: string;
  source: string;
}

export async function fetchThreatLogs(
  query: ThreatLogQuery = {},
): Promise<ThreatLogListResponse> {
  const params = new URLSearchParams();
  if (query.page) params.set('page', String(query.page));
  if (query.page_size) params.set('page_size', String(query.page_size));
  if (query.severity) params.set('severity', query.severity);
  if (query.category) params.set('category', query.category);
  if (query.search) params.set('search', query.search);
  const qs = params.toString();
  return request<ThreatLogListResponse>(`/threats/logs${qs ? `?${qs}` : ''}`);
}

export async function fetchThreatStats(): Promise<ThreatStats> {
  return request<ThreatStats>('/threats/stats');
}

export async function clearThreatLogs(): Promise<{ cleared: number; status: string }> {
  return request<{ cleared: number; status: string }>('/threats/clear', {
    method: 'POST',
  });
}

export interface QuarantineItem {
  id: number;
  original_path: string;
  quarantined_path: string;
  file_name: string;
  file_hash: string;
  file_size: number;
  severity: string;
  category: string;
  reason: string;
  detected_at: string;
  restored_at: string;
  deleted_at: string;
  status: string;
  source_event_id: number | null;
}

export interface QuarantineItemListResponse {
  items: QuarantineItem[];
  total: number;
}

export interface QuarantineStats {
  active_count: number;
  critical_count: number;
  total_size_bytes: number;
  total_quarantined_ever: number;
}

export interface QuarantineAddRequest {
  file_path: string;
  reason?: string;
  severity?: string;
  category?: string;
  source_event_id?: number;
}

export interface QuarantineActionResponse {
  status: string;
  message: string;
  item: QuarantineItem | null;
}

export interface QuarantineItemViewModel {
  id: number;
  name: string;
  type: string;
  date: string;
  size: string;
  risk: string;
  status: string;
  originalPath: string;
  fileHash: string;
  reason: string;
}

export async function fetchQuarantineItems(params?: {
  status?: string;
  severity?: string;
  search?: string;
}): Promise<QuarantineItemListResponse> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set('status', params.status);
  if (params?.severity) qs.set('severity', params.severity);
  if (params?.search) qs.set('search', params.search);
  const query = qs.toString();
  return request<QuarantineItemListResponse>(
    `/quarantine/items${query ? `?${query}` : ''}`,
  );
}

export async function fetchQuarantineStats(): Promise<QuarantineStats> {
  return request<QuarantineStats>('/quarantine/stats');
}

export async function fetchQuarantineItem(id: number): Promise<QuarantineItem> {
  return request<QuarantineItem>(`/quarantine/items/${id}`);
}

export async function addToQuarantine(
  body: QuarantineAddRequest,
): Promise<QuarantineActionResponse> {
  return request<QuarantineActionResponse>('/quarantine/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function uploadToQuarantine(
  file: File,
  options?: { reason?: string; severity?: string; category?: string },
): Promise<QuarantineActionResponse> {
  const form = new FormData();
  form.append('file', file);
  const params = new URLSearchParams();
  if (options?.reason) params.set('reason', options.reason);
  if (options?.severity) params.set('severity', options.severity);
  if (options?.category) params.set('category', options.category);
  const qs = params.toString();
  const response = await fetch(
    `${API_BASE_URL}/quarantine/upload${qs ? `?${qs}` : ''}`,
    { method: 'POST', body: form },
  );
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // ignore
    }
    throw new ApiError(detail || `Upload failed (${response.status})`, response.status);
  }
  return response.json() as Promise<QuarantineActionResponse>;
}

export async function restoreQuarantineItem(
  id: number,
): Promise<QuarantineActionResponse> {
  return request<QuarantineActionResponse>(`/quarantine/restore/${id}`, {
    method: 'POST',
  });
}

export async function deleteQuarantineItem(
  id: number,
): Promise<QuarantineActionResponse> {
  return request<QuarantineActionResponse>(`/quarantine/delete/${id}`, {
    method: 'DELETE',
  });
}

export async function clearQuarantine(): Promise<{ cleared: number; status: string }> {
  return request<{ cleared: number; status: string }>('/quarantine/clear', {
    method: 'POST',
  });
}

export function formatQuarantineSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export interface RansomwareSettings {
  monitoring_enabled: boolean;
  auto_quarantine: boolean;
  sensitivity: string;
  protected_folders: string[];
}

export interface RansomwareSettingsUpdate {
  monitoring_enabled?: boolean;
  auto_quarantine?: boolean;
  sensitivity?: string;
  protected_folders?: string[];
}

export interface RansomwareEvent {
  id: number;
  timestamp: string;
  file_path: string;
  event_type: string;
  severity: string;
  threat_name: string;
  description: string;
  status: string;
  response_action: string;
  quarantined: boolean;
  folder_path: string;
  heuristic_type: string;
}

export interface RansomwareStatus {
  protection_status: string;
  monitoring_active: boolean;
  monitoring_enabled: boolean;
  auto_quarantine: boolean;
  sensitivity: string;
  protected_folders: string[];
  attempts_blocked: number;
  protected_files_count: number;
  success_rate_percent: number;
  events_last_24h: number;
  critical_events_24h: number;
  layers: { name: string; status: string }[];
}

export interface RansomwareEventListResponse {
  events: RansomwareEvent[];
  total: number;
}

export async function fetchRansomwareStatus(): Promise<RansomwareStatus> {
  return request<RansomwareStatus>('/ransomware/status');
}

export async function fetchRansomwareEvents(
  limit = 50,
): Promise<RansomwareEventListResponse> {
  return request<RansomwareEventListResponse>(`/ransomware/events?limit=${limit}`);
}

export async function fetchRansomwareSettings(): Promise<RansomwareSettings> {
  return request<RansomwareSettings>('/ransomware/settings');
}

export async function startRansomwareProtection(): Promise<{
  status: string;
  message: string;
  monitoring_active: boolean;
}> {
  return request('/ransomware/start', { method: 'POST' });
}

export async function stopRansomwareProtection(): Promise<{
  status: string;
  message: string;
  monitoring_active: boolean;
}> {
  return request('/ransomware/stop', { method: 'POST' });
}

export async function updateRansomwareSettings(
  update: RansomwareSettingsUpdate,
): Promise<RansomwareSettings> {
  return request<RansomwareSettings>('/ransomware/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
  });
}

export function formatRelativeThreatTime(isoOrDisplay: string): string {
  const date = new Date(isoOrDisplay);
  if (Number.isNaN(date.getTime())) {
    return isoOrDisplay;
  }
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return `${seconds} sec ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? '' : 's'} ago`;
}

export function mapQuarantineItemToViewModel(
  item: QuarantineItem,
): QuarantineItemViewModel {
  return {
    id: item.id,
    name: item.file_name,
    type: item.category,
    date: item.detected_at,
    size: formatQuarantineSize(item.file_size),
    risk: item.severity,
    status: item.status,
    originalPath: item.original_path,
    fileHash: item.file_hash,
    reason: item.reason,
  };
}

export function mapThreatLogToViewModel(entry: ThreatLogEntry): ThreatLogViewModel {
  const pathParts = entry.file_path.replace(/\\/g, '/').split('/');
  const folder = pathParts.length > 1 ? pathParts[pathParts.length - 2] : 'Filesystem';
  const source = entry.process_name || folder || 'Local Filesystem';

  return {
    id: entry.id,
    timestamp: entry.timestamp,
    type: entry.category,
    severity: entry.severity,
    threat: entry.description,
    action: entry.status,
    source,
  };
}

export interface UsbDevice {
  device_id: string;
  name: string;
  manufacturer: string;
  serial_number: string;
  connected_time: string;
  device_type: string;
  status: string;
  drive_letter: string;
  capacity_bytes: number;
  protection_status: string;
  threat_count: number;
  threat_reasons: string[];
  is_duplicate: boolean;
  is_unauthorized: boolean;
  last_scan_time: string;
}

export interface UsbEvent {
  event_id: string;
  device_id: string;
  device_name: string;
  event_type: string;
  timestamp: string;
  drive_letter: string;
  protection_status: string;
}

export interface UsbDeviceListResponse {
  devices: UsbDevice[];
  total_connected: number;
  safe_count: number;
  threat_count: number;
  scanning_count: number;
}

export interface UsbHistoryResponse {
  events: UsbEvent[];
  total_events: number;
}

export type UsbUiStatus = 'safe' | 'threat' | 'scanning';

export interface UsbDeviceViewModel {
  id: string;
  name: string;
  capacity: string;
  status: UsbUiStatus;
  lastScan: string;
  threats: number;
  manufacturer: string;
  driveLetter: string;
  protectionStatus: string;
  threatReasons: string[];
  connectedTime: string;
  isRecentlyConnected: boolean;
}

export async function fetchUsbDevices(): Promise<UsbDeviceListResponse> {
  return request<UsbDeviceListResponse>('/usb/devices');
}

export async function fetchUsbHistory(): Promise<UsbHistoryResponse> {
  return request<UsbHistoryResponse>('/usb/history');
}

export async function triggerUsbScan(): Promise<void> {
  await request<{ status: string }>('/usb/scan', { method: 'POST' });
}

export function mapUsbUiStatus(device: UsbDevice): UsbUiStatus {
  if (
    device.protection_status === 'suspicious' ||
    device.protection_status === 'blocked' ||
    device.is_unauthorized
  ) {
    return 'threat';
  }
  if (
    device.protection_status === 'unknown' ||
    device.protection_status === 'recently_connected'
  ) {
    return 'scanning';
  }
  return 'safe';
}

export function mapUsbDeviceToViewModel(device: UsbDevice): UsbDeviceViewModel {
  const status = mapUsbUiStatus(device);
  return {
    id: device.device_id,
    name: device.name,
    capacity: formatCapacityFromBytes(device.capacity_bytes),
    status,
    lastScan: formatRelativeTimeFromIso(device.last_scan_time || device.connected_time),
    threats: device.threat_count,
    manufacturer: device.manufacturer,
    driveLetter: device.drive_letter,
    protectionStatus: device.protection_status,
    threatReasons: device.threat_reasons,
    connectedTime: device.connected_time,
    isRecentlyConnected: device.protection_status === 'recently_connected',
  };
}

function formatCapacityFromBytes(bytes: number): string {
  if (!bytes) {
    return 'Unknown';
  }
  const gb = bytes / (1024 ** 3);
  if (gb >= 1) {
    return `${gb.toFixed(gb >= 10 ? 0 : 1)} GB`;
  }
  return `${Math.round(bytes / (1024 ** 2))} MB`;
}

function formatRelativeTimeFromIso(isoTime: string): string {
  const date = new Date(isoTime);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 10) {
    return 'Just now';
  }
  if (seconds < 60) {
    return `${seconds} sec ago`;
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes} min ago`;
  }
  return date.toLocaleString();
}

/** Heuristic risk scoring until advanced threat detection is implemented. */
export function deriveRiskLevel(
  cpuPercent: number,
  memoryPercent: number,
): RiskLevel {
  if (cpuPercent >= 50 || memoryPercent >= 80) {
    return 'dangerous';
  }
  if (cpuPercent >= 25 || memoryPercent >= 50) {
    return 'warning';
  }
  return 'safe';
}

export function memoryPercentToMb(
  memoryPercent: number,
  systemMemoryTotalBytes: number,
): number {
  const bytesUsed = (memoryPercent / 100) * systemMemoryTotalBytes;
  return Math.round(bytesUsed / (1024 * 1024));
}

export function formatCpuPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function formatStatus(status: string): string {
  if (!status) {
    return 'Unknown';
  }
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export function mapProcessToViewModel(
  process: ProcessInfo,
  systemMemoryTotalBytes: number,
): ProcessViewModel {
  return {
    id: process.pid,
    name: process.process_name,
    pid: process.pid,
    cpu: process.cpu_percent,
    memory: memoryPercentToMb(process.memory_percent, systemMemoryTotalBytes),
    risk: deriveRiskLevel(process.cpu_percent, process.memory_percent),
    status: formatStatus(process.status),
  };
}

export function mapProcessesResponse(
  response: ProcessListResponse,
): ProcessViewModel[] {
  return response.processes.map((process) =>
    mapProcessToViewModel(process, response.system_memory_total_bytes),
  );
}
