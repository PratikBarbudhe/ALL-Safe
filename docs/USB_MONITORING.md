# Phase 5 — USB Device Monitoring

## How it works

```
UsbProtection.tsx → useUsbMonitor (3s) → GET /usb/devices + /usb/history
                                              ↓
                                    UsbService (background thread, 1s poll)
                                              ↓
                                    UsbMonitor (WMI + pywin32 on Windows)
```

1. **WMI enumeration** — `Win32_DiskDrive` (USB interface) and `Win32_LogicalDisk` (removable).
2. **Background monitor** — compares snapshots every second; logs insert/remove to `backend/logs/usb_events.log`.
3. **Heuristics** — unknown name, missing serial, duplicate serial, suspicious files on drive root.
4. **Policy files** — `backend/data/trusted_usb_devices.json`, `backend/data/blocked_usb_devices.json` (monitor-only placeholders).

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/usb/devices` | Connected USB storage devices |
| GET | `/usb/history` | Connect/disconnect event log |
| POST | `/usb/scan` | Force immediate rescan |

## Setup

```powershell
cd F:\ALL-Safe\backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Add trusted device (optional):

```json
// backend/data/trusted_usb_devices.json
{
  "trusted_device_ids": ["USB\\VID_0781&PID_5581\\..."],
  "trusted_serial_numbers": ["4C530001234567890"]
}
```

## Trust a device

Copy `device_id` or `serial_number` from `/usb/devices` into the trusted JSON file and restart the backend.
