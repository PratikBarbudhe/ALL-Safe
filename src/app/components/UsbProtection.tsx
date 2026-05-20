import { Usb, AlertTriangle, CheckCircle, XCircle, HardDrive, RefreshCw } from 'lucide-react';
import { useUsbMonitor } from '@/hooks/useUsbMonitor';
import { formatEventType, formatRelativeTime } from '@/lib/format';
import type { UsbDeviceViewModel } from '@/lib/api';

function DeviceCard({ device }: { device: UsbDeviceViewModel }) {
  return (
    <div
      className="p-6 rounded-xl border transition-all duration-300"
      style={{
        backgroundColor: '#1E293B',
        borderColor: device.status === 'threat' ? '#EF4444' : '#334155',
        borderWidth: device.status === 'threat' ? '2px' : '1px',
      }}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
            <HardDrive
              className="w-8 h-8"
              style={{
                color:
                  device.status === 'threat'
                    ? '#EF4444'
                    : device.status === 'safe'
                      ? '#10B981'
                      : '#F59E0B',
              }}
            />
          </div>
          <div>
            <h3 className="mb-1" style={{ color: '#F8FAFC' }}>{device.name}</h3>
            <p className="text-sm mb-2" style={{ color: '#94A3B8' }}>
              Capacity: {device.capacity}
              {device.driveLetter ? ` · Drive ${device.driveLetter}` : ''}
            </p>
            <div className="flex items-center gap-2 flex-wrap">
              {device.status === 'safe' && (
                <span
                  className="px-3 py-1 rounded-full text-xs flex items-center gap-1"
                  style={{ backgroundColor: '#10B98120', color: '#10B981' }}
                >
                  <CheckCircle className="w-3 h-3" />
                  {device.protectionStatus === 'trusted' ? 'Trusted' : 'Safe'}
                </span>
              )}
              {device.status === 'threat' && (
                <span
                  className="px-3 py-1 rounded-full text-xs flex items-center gap-1"
                  style={{ backgroundColor: '#EF444420', color: '#EF4444' }}
                >
                  <XCircle className="w-3 h-3" />
                  {device.threats} Threat{device.threats === 1 ? '' : 's'} Detected
                </span>
              )}
              {device.status === 'scanning' && (
                <span
                  className="px-3 py-1 rounded-full text-xs flex items-center gap-1"
                  style={{ backgroundColor: '#F59E0B20', color: '#F59E0B' }}
                >
                  <div className="w-3 h-3 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin"></div>
                  {device.isRecentlyConnected ? 'Recently Connected' : 'Scanning...'}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs mb-2" style={{ color: '#94A3B8' }}>
            Last scan:{' '}
            {device.status === 'scanning' && device.isRecentlyConnected
              ? 'Scanning...'
              : device.lastScan}
          </p>
          <div className="flex gap-2">
            {device.status === 'threat' ? (
              <>
                <button type="button" className="px-3 py-1 rounded text-xs" style={{ backgroundColor: '#EF4444', color: '#FFFFFF' }}>
                  Block Device
                </button>
                <button type="button" className="px-3 py-1 rounded text-xs" style={{ backgroundColor: '#334155', color: '#F8FAFC' }}>
                  Quarantine
                </button>
              </>
            ) : (
              <>
                <button type="button" className="px-3 py-1 rounded text-xs" style={{ backgroundColor: '#3B82F6', color: '#FFFFFF' }}>
                  Scan Now
                </button>
                <button type="button" className="px-3 py-1 rounded text-xs" style={{ backgroundColor: '#334155', color: '#F8FAFC' }}>
                  Eject
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {device.status === 'threat' && device.threatReasons.length > 0 && (
        <div className="mt-4 pt-4 border-t" style={{ borderColor: '#334155' }}>
          <h4 className="text-sm mb-3" style={{ color: '#F8FAFC' }}>Detected Threats:</h4>
          <div className="space-y-2">
            {device.threatReasons.map((reason) => (
              <div
                key={reason}
                className="flex items-center justify-between p-3 rounded-lg"
                style={{ backgroundColor: '#0F172A' }}
              >
                <div>
                  <p className="text-sm" style={{ color: '#F8FAFC' }}>{reason}</p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>
                    Heuristic detection — monitoring only
                  </p>
                </div>
                <span className="px-2 py-1 rounded text-xs" style={{ backgroundColor: '#EF444420', color: '#EF4444' }}>
                  {reason.toLowerCase().includes('duplicate') ? 'Medium Risk' : 'High Risk'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function UsbProtection() {
  const {
    devices,
    history,
    stats,
    isLoading,
    isRefreshing,
    isScanning,
    error,
    reload,
    scanAllDevices,
  } = useUsbMonitor();

  const contentOpacity = isLoading ? 0.5 : isRefreshing ? 0.85 : 1;

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

      <div className="transition-opacity duration-300 ease-in-out" style={{ opacity: contentOpacity }}>
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-2xl mb-1" style={{ color: '#F8FAFC' }}>USB Protection</h2>
              <p className="text-sm" style={{ color: '#94A3B8' }}>Monitor and protect against USB-based threats</p>
            </div>
            <button
              type="button"
              onClick={() => void scanAllDevices()}
              disabled={isLoading || isScanning}
              className="px-4 py-2 rounded-lg flex items-center gap-2 disabled:opacity-60"
              style={{ backgroundColor: '#3B82F6', color: '#FFFFFF' }}
            >
              <Usb className={`w-4 h-4 ${isScanning ? 'animate-pulse' : ''}`} />
              {isScanning ? 'Scanning...' : 'Scan All Devices'}
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: '#3B82F620' }}>
                  <Usb className="w-5 h-5" style={{ color: '#3B82F6' }} />
                </div>
                <div>
                  <p className="text-2xl" style={{ color: '#F8FAFC' }}>{isLoading ? '—' : stats.total}</p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>Connected Devices</p>
                </div>
              </div>
            </div>
            <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: '#10B98120' }}>
                  <CheckCircle className="w-5 h-5" style={{ color: '#10B981' }} />
                </div>
                <div>
                  <p className="text-2xl" style={{ color: '#10B981' }}>{isLoading ? '—' : stats.safe}</p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>Safe Devices</p>
                </div>
              </div>
            </div>
            <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: '#EF444420' }}>
                  <XCircle className="w-5 h-5" style={{ color: '#EF4444' }} />
                </div>
                <div>
                  <p className="text-2xl" style={{ color: '#EF4444' }}>{isLoading ? '—' : stats.threats}</p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>Threats Detected</p>
                </div>
              </div>
            </div>
            <div className="p-4 rounded-lg border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg" style={{ backgroundColor: '#F59E0B20' }}>
                  <AlertTriangle className="w-5 h-5" style={{ color: '#F59E0B' }} />
                </div>
                <div>
                  <p className="text-2xl" style={{ color: '#F59E0B' }}>{isLoading ? '—' : stats.scanning}</p>
                  <p className="text-xs" style={{ color: '#94A3B8' }}>Scanning</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mb-6 p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
          <h3 className="mb-4" style={{ color: '#F8FAFC' }}>Protection Settings</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <div>
                <p className="text-sm mb-1" style={{ color: '#F8FAFC' }}>Auto-scan on connect</p>
                <p className="text-xs" style={{ color: '#94A3B8' }}>Automatically scan new USB devices</p>
              </div>
              <div className="relative inline-block w-12 h-6">
                <input type="checkbox" className="sr-only peer" defaultChecked readOnly />
                <div className="w-12 h-6 rounded-full peer peer-checked:bg-green-500 bg-gray-600 transition-colors cursor-pointer"></div>
                <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full peer-checked:translate-x-6 transition-transform"></div>
              </div>
            </div>
            <div className="flex items-center justify-between p-4 rounded-lg" style={{ backgroundColor: '#0F172A' }}>
              <div>
                <p className="text-sm mb-1" style={{ color: '#F8FAFC' }}>Block unknown devices</p>
                <p className="text-xs" style={{ color: '#94A3B8' }}>Prevent unrecognized USB access</p>
              </div>
              <div className="relative inline-block w-12 h-6">
                <input type="checkbox" className="sr-only peer" readOnly />
                <div className="w-12 h-6 rounded-full bg-gray-600 transition-colors cursor-pointer"></div>
                <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform"></div>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4 mb-6">
          {isLoading &&
            [1, 2, 3].map((item) => (
              <div
                key={item}
                className="p-6 rounded-xl border animate-pulse h-32"
                style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}
              />
            ))}
          {!isLoading && devices.length === 0 && (
            <div className="p-8 rounded-xl border text-center" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
              <Usb className="w-10 h-10 mx-auto mb-3" style={{ color: '#94A3B8' }} />
              <p className="text-sm" style={{ color: '#F8FAFC' }}>No USB storage devices connected</p>
              <p className="text-xs mt-1" style={{ color: '#94A3B8' }}>Connect a device to begin live monitoring</p>
            </div>
          )}
          {!isLoading && devices.map((device) => <DeviceCard key={device.id} device={device} />)}
        </div>

        <div className="p-6 rounded-xl border" style={{ backgroundColor: '#1E293B', borderColor: '#334155' }}>
          <h3 className="mb-4" style={{ color: '#F8FAFC' }}>USB Activity History</h3>
          {!isLoading && history.length === 0 && (
            <p className="text-sm text-center py-4" style={{ color: '#94A3B8' }}>No USB events recorded yet</p>
          )}
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {!isLoading &&
              history.slice(0, 20).map((event) => (
                <div
                  key={event.event_id}
                  className="flex items-center justify-between p-3 rounded-lg"
                  style={{ backgroundColor: '#0F172A' }}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-2 h-2 rounded-full ${event.event_type === 'inserted' ? 'bg-green-500' : 'bg-red-500'}`}
                    />
                    <div>
                      <p className="text-sm" style={{ color: '#F8FAFC' }}>{event.device_name}</p>
                      <p className="text-xs" style={{ color: '#94A3B8' }}>
                        {formatEventType(event.event_type)}
                        {event.drive_letter ? ` · ${event.drive_letter}` : ''}
                      </p>
                    </div>
                  </div>
                  <span className="text-xs" style={{ color: '#94A3B8' }}>
                    {formatRelativeTime(event.timestamp)}
                  </span>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
