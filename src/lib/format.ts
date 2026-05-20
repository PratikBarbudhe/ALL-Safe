export function formatBytes(bytes: number, decimals = 1): string {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return '0 B';
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const index = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const value = bytes / 1024 ** index;
  return `${value.toFixed(decimals)} ${units[index]}`;
}

export function formatBytesPerSecond(bytesPerSecond: number): string {
  if (!Number.isFinite(bytesPerSecond) || bytesPerSecond <= 0) {
    return '0 MB/s';
  }
  const mbPerSecond = bytesPerSecond / (1024 * 1024);
  if (mbPerSecond >= 1) {
    return `${mbPerSecond.toFixed(1)} MB/s`;
  }
  const kbPerSecond = bytesPerSecond / 1024;
  return `${kbPerSecond.toFixed(1)} KB/s`;
}

export function formatUptime(uptime: string): string {
  return uptime || '—';
}

export function formatNumber(value: number): string {
  return value.toLocaleString();
}

export function formatPercent(value: number, digits = 0): string {
  return `${value.toFixed(digits)}%`;
}

export function formatScanTime(isoTime: string): string {
  if (!isoTime) {
    return 'Never';
  }
  const date = new Date(isoTime);
  if (Number.isNaN(date.getTime())) {
    return isoTime;
  }
  return date.toLocaleString();
}

export function formatNetworkTotal(sent: number, received: number): string {
  return `${formatBytes(sent)} ↑ / ${formatBytes(received)} ↓`;
}

export function formatCapacity(bytes: number): string {
  if (!bytes || bytes <= 0) {
    return 'Unknown';
  }
  const gb = bytes / (1024 ** 3);
  if (gb >= 1) {
    return `${gb.toFixed(gb >= 10 ? 0 : 1)} GB`;
  }
  const mb = bytes / (1024 ** 2);
  return `${mb.toFixed(0)} MB`;
}

export function formatRelativeTime(isoTime: string): string {
  if (!isoTime) {
    return '—';
  }
  const date = new Date(isoTime);
  if (Number.isNaN(date.getTime())) {
    return isoTime;
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
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours} hr ago`;
  }
  return date.toLocaleString();
}

export function formatEventType(eventType: string): string {
  return eventType === 'inserted' ? 'Connected' : 'Disconnected';
}
