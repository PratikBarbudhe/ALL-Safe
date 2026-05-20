# AllSafe Production Build Guide

This document describes how to build an installable Windows desktop release of AllSafe with a bundled Python backend (no separate Python install required).

## Architecture

```
AllSafe.exe (Tauri + WebView2)
    ├── Spawns allsafe-api sidecar (PyInstaller, FastAPI/uvicorn)
    ├── System tray (show/hide/exit/restart monitors)
    └── React UI → http://127.0.0.1:8000
```

## Prerequisites

- Windows 10/11 (x64)
- Node.js 20+ and npm/pnpm
- Rust toolchain (for Tauri)
- Python 3.11+ with `backend/requirements.txt` installed
- WebView2 Runtime (bootstrapped by installer if missing)

## Development (two processes)

```powershell
# Terminal 1 — API
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000

# Terminal 2 — Desktop shell
cd ..
npm install
npm run tauri:dev
```

Or run API only in browser: `npm run dev` + backend above.

## Production build steps

### 1. Build frontend

```powershell
npm install
npm run build
```

### 2. Build backend sidecar

```powershell
npm run build:backend
```

This runs `scripts/build_backend.ps1`, which uses PyInstaller to produce:

`src-tauri/bin/allsafe-api-x86_64-pc-windows-msvc.exe`

### 3. Build Tauri installers

```powershell
npm run tauri:build
```

Outputs (under `src-tauri/target/release/bundle/`):

| Target | Output |
|--------|--------|
| NSIS | `nsis/AllSafe_*_x64-setup.exe` |
| MSI | `msi/AllSafe_*_x64_en-US.msi` |
| Portable | `app/AllSafe.exe` (standalone binary) |

One-shot:

```powershell
npm run build:production
```

## Runtime behavior

- **Startup:** Tauri launches the API sidecar, then loads the UI. `AppLifecycleService` initializes monitors per `backend/data/settings.json`.
- **Tray:** Close window → minimizes to tray when `minimize_to_tray` is enabled. Protection continues in background.
- **Exit:** Tray → Exit calls `POST /app/shutdown` and terminates the app.
- **Windows startup:** Enable **Start with Windows** in Settings to add an HKCU Run registry entry.
- **Watchdog:** `BackgroundServiceManager` restarts dead monitor threads every 30 seconds.
- **Performance:** `backend/logs/performance.log` tracks AllSafe CPU/RAM and poll throttling.

## API endpoints (operations)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/app/status` | Monitor health, uptime, DB connectivity |
| GET | `/app/performance` | Process metrics and anomalies |
| POST | `/app/restart-monitors` | Recover all background monitors |
| POST | `/app/shutdown` | Graceful shutdown |

## Configuration

All runtime behavior is driven by `backend/data/settings.json` (managed via Settings UI).

Key production flags:

- `system.background_monitoring` — keep monitors running
- `system.minimize_to_tray` — tray on close
- `system.auto_start_with_windows` — registry startup
- `logging.log_retention_days` — log rotation cleanup on startup

## Troubleshooting

| Issue | Action |
|-------|--------|
| UI shows offline | Confirm sidecar is running; check port 8000 |
| Monitors degraded | Dashboard → Production Diagnostics → Restart Monitors |
| Sidecar missing | Re-run `npm run build:backend` before `tauri:build` |
| High CPU | Performance log may show throttling; increase dashboard refresh interval in Settings |

## Version

Application version is synchronized across:

- `package.json` / `src-tauri/tauri.conf.json` → **1.0.0**
- `backend/config.py` → `app_version`
