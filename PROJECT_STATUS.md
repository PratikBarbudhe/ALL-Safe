# AllSafe Project Status

> **AI instruction:** Read this file completely before continuing development.

Last updated to reflect the repository as of Phase 13 completion (production hardening, lifecycle, tray, packaging).

---

## 1. Project Overview

### Purpose of the application

**AllSafe** is a local-only Windows desktop cybersecurity monitoring application. It provides a security-dashboard-style UI for observing system health, running processes, USB device activity, and real-time filesystem security events. The product goal is an EDR-like monitoring experience without cloud dependency.

### Target platform

- **Primary:** Windows 10 / Windows 11 (desktop)
- **Shell:** Tauri 2 native window (WebView2)
- **Backend:** Python FastAPI bound to `127.0.0.1` (local only)

### Current development stage

- **Phase 13 complete:** Application lifecycle, background/tray mode, performance monitoring, production packaging (NSIS/MSI/portable), bundled backend sidecar build
- **Phase 12 complete:** Centralized Settings (`/settings/*`, `backend/data/settings.json`)
- **Phase 11 complete:** Local AI Analysis engine (`/ai-analysis/*`)
- **Phase 10 complete:** Notification center (`/notifications/*`)
- **Phase 9 complete:** Native Windows Defender/Firewall/TPM integration, dashboard + Settings live status
- **Phase 8 complete:** Ransomware heuristic detection, auto-quarantine, live Ransomware Detection UI
- **Phase 7 complete:** Real quarantine engine (file isolation, restore, delete, SQLite + metadata)
- **Phase 6 complete:** Threat logging with watchdog filesystem monitoring, SQLite persistence, and live Threat Logs UI
- **Phases 1–5 complete:** Tauri desktop, FastAPI foundation, process monitor, live dashboard, USB monitoring
- **Several UI screens exist with static/mock data only** (AI Analysis, Settings toggles, Header search)

### Local-only architecture

- No cloud services, accounts, or remote APIs in the current implementation
- Frontend talks to `http://127.0.0.1:8000` (configurable via `VITE_API_URL`)
- All monitoring data is collected and stored on the local machine
- CORS allows localhost Vite and Tauri origins only (`backend/config.py`)

---

## 2. Final Architecture

```
React UI (Vite + TypeScript)
        ↓ fetch / REST
Tauri Desktop Wrapper (Rust, WebView2)
        ↓ loads frontend; does NOT host Python API today
FastAPI Backend (Python, uvicorn)
        ↓
Windows APIs / Monitoring Services
   ├── psutil          → CPU, RAM, disk, network, processes
   ├── WMI + pywin32   → USB enumeration, drive scan heuristics
   ├── watchdog        → Real-time filesystem events
   ├── PowerShell/helpers → Defender, firewall, connection counts
   └── SQLite          → Threat logs + quarantine_items persistence
```

### Technology stack (in use)

| Layer | Technology | Role |
|-------|------------|------|
| UI | React 18 | Screen components, state-based navigation |
| Build | Vite 6 | Dev server, production bundle → `dist/` |
| Language | TypeScript | Frontend types, hooks, API client |
| Styling | Tailwind CSS 4 | Utility classes + inline theme colors |
| Components | shadcn/ui (Radix) | `src/app/components/ui/*` — available; main screens use custom slate cyber UI |
| Charts | Recharts | Dashboard performance + threat area charts |
| Icons | lucide-react | Sidebar, cards, tables |
| Desktop | Tauri 2 | Native window, bundling, `tauri dev` / `tauri build` |
| API | FastAPI | REST endpoints, lifespan hooks |
| System metrics | psutil | System + process collectors |
| File monitor | watchdog | Observer on Desktop, Downloads, Documents, Temp |
| USB | WMI | Device enumeration |
| Windows integration | pywin32 | Windows-specific helpers |
| Persistence | SQLite | `backend/data/threat_logs.db` |
| Policy files | JSON | USB trusted/blocked device lists |

**Note:** In production builds, Tauri spawns the `allsafe-api` sidecar automatically. In dev, start the backend manually or via `tauri dev` (Python fallback spawn).

---

## 3. Current Folder Structure

### Frontend (project root + `src/`)

```
ALL-Safe/
├── index.html                 # Vite HTML entry
├── package.json               # npm scripts (dev, build, tauri:dev, tauri:build)
├── vite.config.ts             # Vite + Tailwind + @ alias + Tauri dev/HMR settings
├── package-lock.json
├── dist/                      # Production build output (generated)
│
└── src/
    ├── main.tsx               # React root mount
    ├── app/
    │   ├── App.tsx            # Screen router (useState, no React Router)
    │   └── components/
    │       ├── Dashboard.tsx          # Live dashboard (useDashboard)
    │       ├── ProcessMonitor.tsx     # Live processes (inline polling)
    │       ├── UsbProtection.tsx      # Live USB (useUsbMonitor)
    │       ├── ThreatLogs.tsx         # Live threat logs (useThreatLogs)
    │       ├── RansomwareDetection.tsx  # STATIC UI only
    │       ├── AiAnalysis.tsx           # STATIC UI only
    │       ├── Quarantine.tsx           # Live quarantine (useQuarantine)
    │       ├── Settings.tsx             # STATIC UI only
    │       ├── Sidebar.tsx              # Navigation
    │       ├── Header.tsx               # Top bar (search not wired)
    │       ├── ui/                      # shadcn/ui primitives
    │       └── figma/                   # Asset helpers
    ├── hooks/
    │   ├── useDashboard.ts    # Dashboard + chart history
    │   ├── useUsbMonitor.ts     # USB devices + history
    │   ├── useThreatLogs.ts     # Threat table + stats + filters
    │   └── useQuarantine.ts     # Quarantine table + actions
    ├── lib/
    │   ├── api.ts             # Central API client + TypeScript interfaces
    │   └── format.ts          # Number/byte formatting helpers
    └── styles/
        ├── index.css
        ├── tailwind.css
        ├── theme.css
        └── globals.css
```

### Tauri (`src-tauri/`)

```
src-tauri/
├── Cargo.toml                 # Rust deps: tauri 2, tauri-plugin-log
├── tauri.conf.json            # App name, window 1280×800, devUrl, bundle
├── tauri.windows.conf.json    # Windows-specific Tauri overrides
├── build.rs                   # Tauri build script
├── capabilities/
│   └── default.json           # Tauri 2 capabilities
├── icons/                     # Application icons (.ico, .png, .icns)
└── src/
    ├── main.rs                # Desktop entry
    └── lib.rs                 # Tauri builder + log plugin (debug)
```

### Backend (`backend/`)

```
backend/
├── main.py                    # FastAPI app, lifespan, CORS, exception handlers
├── config.py                  # ALLSAFE_* env settings, CORS origins
├── requirements.txt           # Python dependencies
├── README.md                  # Backend setup notes
│
├── api/
│   ├── __init__.py            # Aggregates all routers
│   ├── system_routes.py       # GET /system/stats
│   ├── process_routes.py      # GET /processes
│   ├── dashboard_routes.py    # GET /dashboard/overview
│   ├── usb_routes.py          # GET /usb/devices, /usb/history, POST /usb/scan
│   ├── threat_routes.py       # GET /threats/logs, /threats/stats, POST /threats/clear
│   └── quarantine_routes.py   # POST /quarantine/add, GET /items, restore, delete, clear
│
├── monitoring/                # OS-level collectors (blocking)
│   ├── system_monitor.py      # psutil system stats
│   ├── process_monitor.py     # psutil top processes
│   ├── usb_monitor.py         # WMI USB + drive root heuristics
│   └── file_monitor.py        # watchdog classification + burst detection
│
├── services/                  # Business logic, state, background threads
│   ├── dashboard_service.py   # Aggregates overview for dashboard
│   ├── usb_service.py         # USB poll thread, history, policy, logging
│   ├── threat_log_service.py  # SQLite + file monitor lifecycle + threat log API
│   └── threat_counters.py     # In-memory counters synced to dashboard
│
├── models/                    # Pydantic response schemas
│   ├── system_models.py
│   ├── process_models.py
│   ├── dashboard_models.py
│   ├── usb_models.py
│   ├── threat_models.py
│   └── quarantine_models.py
│
├── utils/
│   ├── exceptions.py          # Domain exception types
│   ├── logging_config.py      # Root rotating allsafe.log
│   └── windows_security.py    # Defender, firewall, USB count, TCP count
│
├── data/
│   ├── trusted_usb_devices.json
│   ├── blocked_usb_devices.json
│   ├── threat_logs.db         # SQLite (runtime)
│   └── quarantine.db          # SQLite quarantine_items (runtime)
│
└── logs/
    ├── .gitkeep
    ├── allsafe.log            # Rotating root log (runtime)
    ├── usb_events.log         # USB audit log (runtime)
    ├── threat_events.log      # Threat audit log (runtime)
    └── quarantine_events.log  # Quarantine audit log (runtime)

backend/quarantine/
├── files/                     # Isolated .quarantine files
└── metadata/                  # Per-item JSON metadata
```

### Documentation (`docs/`)

| File | Contents |
|------|----------|
| `docs/TAURI_SETUP.md` | Phase 1 Tauri setup and build |
| `docs/DASHBOARD.md` | Dashboard API and widgets |
| `docs/PROCESS_MONITOR.md` | Process monitor integration |
| `docs/USB_MONITORING.md` | USB architecture |
| `docs/FILE_MONITORING.md` | Threat / filesystem monitoring |

---

## 4. Completed Phases

### Phase 1 — Tauri Setup

**Completed items:**

- Tauri 2 project under `src-tauri/`
- Window: **AllSafe Security**, 1280×800, min 1024×640, dark theme
- Bundle ID: `com.allsafe.security`
- Vite dev integration (`devUrl: http://localhost:5173`)
- npm scripts: `tauri:dev`, `tauri:build`
- `@tauri-apps/api` and `@tauri-apps/cli` in `package.json`
- Debug logging via `tauri-plugin-log` in `src-tauri/src/lib.rs`

**Important files:**

- `src-tauri/tauri.conf.json`
- `src-tauri/Cargo.toml`
- `vite.config.ts` (Tauri HMR, `src-tauri` watch ignore)
- `docs/TAURI_SETUP.md`

**Build commands:**

```powershell
npm install
npm run tauri:dev      # Desktop + Vite hot reload
npm run tauri:build    # Windows installer under src-tauri/target/release/bundle/
```

---

### Phase 2 — FastAPI Backend Foundation

**Completed items:**

- FastAPI application in `backend/main.py`
- Modular routers in `backend/api/`
- Pydantic models in `backend/models/`
- `config.py` with `ALLSAFE_HOST`, `ALLSAFE_PORT`, `ALLSAFE_DEBUG`, CORS
- Rotating file logging via `utils/logging_config.py`
- Domain exceptions + JSON error handlers
- Health check endpoint

**Endpoints (foundation + system):**

- `GET /health`
- `GET /system-stats` (root alias)
- `GET /system/stats` (namespaced duplicate)

**Architecture pattern established:**

```
api/<feature>_routes.py  →  services/<feature>_service.py  →  monitoring/<feature>_monitor.py
```

**Services at this stage:** collectors called per-request via `asyncio.to_thread` (system, process).

---

### Phase 3 — Process Monitor

**Completed items:**

- `backend/monitoring/process_monitor.py` — top processes by CPU via psutil
- `GET /processes` — `ProcessListResponse`
- `src/app/components/ProcessMonitor.tsx` — live table, search, risk filter
- Client-side risk heuristic in `src/lib/api.ts` (`deriveRiskLevel`)
- Auto-refresh every **5 seconds** (`REFRESH_INTERVAL_MS`)
- Loading, silent refresh, error banner + retry

**API response structure:**

```json
{
  "processes": [
    {
      "pid": 1234,
      "process_name": "example.exe",
      "cpu_percent": 12.5,
      "memory_percent": 3.2,
      "status": "running",
      "username": "DOMAIN\\user",
      "executable_path": "C:\\...",
      "create_time": 1710000000.0
    }
  ],
  "total_processes": 250,
  "system_memory_total_bytes": 17179869184
}
```

**Frontend:** `ProcessMonitor.tsx` uses `fetchProcesses()` directly (no dedicated hook file).

---

### Phase 4 — Live Dashboard

**Completed items:**

- `backend/services/dashboard_service.py` — aggregates system, processes, Windows security
- `GET /dashboard/overview` — security score, health, threat counters, protection status
- `src/hooks/useDashboard.ts` — polls overview + processes every **5s**
- `src/app/components/Dashboard.tsx` — stat cards, Recharts area/line charts, resource bars
- `utils/windows_security.py` — Defender, firewall, USB count, network connections
- `threat_counters.py` — in-memory counters (synced from threat logs in Phase 6)

**Widgets connected to live data:**

| Widget | Data source |
|--------|-------------|
| Security Score | `overview.security_score` |
| Active Threats | `overview.active_threats` |
| Blocked Attacks | `overview.blocked_threats` |
| Running Processes | `overview.running_processes` |
| Threat Activity (24h) chart | `fetchThreatStats().events_last_24h` (fallback: `active_threats`) |
| System Performance chart | `cpu_usage`, `ram_usage` history (last 7 poll points) |
| System Resources bars | CPU, RAM, network throughput delta |
| Recent Processes | Top 5 from `GET /processes` |
| USB & Network panel | `usb_devices_connected`, `network_connections`, `system_health` |

**Charts:** Recharts `AreaChart` (threats), `LineChart` (CPU/RAM).

---

### Phase 5 — USB Monitoring

**Completed items:**

- `backend/monitoring/usb_monitor.py` — WMI enumeration, drive root heuristic scan
- `backend/services/usb_service.py` — 1s background poll thread, device state, history deque
- JSON policy: `data/trusted_usb_devices.json`, `data/blocked_usb_devices.json`
- `GET /usb/devices`, `GET /usb/history`, `POST /usb/scan`
- `src/hooks/useUsbMonitor.ts` — **3s** refresh
- `src/app/components/UsbProtection.tsx` — live device cards, scan button
- `backend/logs/usb_events.log` — file audit log
- Lifespan: `usb_service.start_background_monitor()` on app startup

**Trusted device architecture:**

- Policy loaded from JSON at service init
- `protection_status`: `trusted`, `unknown`, `suspicious`, `blocked`, `recently_connected`
- Heuristic `threat_reasons` from suspicious filenames/executables on USB root
- **Detection and logging only** — no physical USB blocking implemented

---

### Phase 6 — Threat Logging

**Completed items:**

- `backend/monitoring/file_monitor.py` — watchdog observer, event classification, rapid-mod burst detection
- `backend/services/threat_log_service.py` — SQLite insert, rotating `threat_events.log`, dashboard counter sync
- `backend/models/threat_models.py` — severity, category, status enums
- `GET /threats/logs`, `GET /threats/stats`, `POST /threats/clear`
- `src/hooks/useThreatLogs.ts` — **3s** refresh, pagination, filters, search debounce
- `src/app/components/ThreatLogs.tsx` — live table (UI layout preserved from design)
- Watched paths: Desktop, Downloads, Documents, `%TEMP%` / `%TMP%` (recursive)
- Lifespan: `threat_log_service.start_background_monitor()` on startup (errors logged, app still runs)

**Severity system (stored lowercase):**

| Value | Typical use |
|-------|-------------|
| `low` | Routine file activity |
| `medium` | Temp modifications, unknown extensions |
| `high` | Suspicious executables, scripts |
| `critical` | Executables in temp/downloads, rapid modification bursts |

**Threat categories:**

- File Activity
- Suspicious Executable
- Script Execution
- Rapid Modification
- Unknown File Type

**Detection (no antivirus scanning):**

- created / modified / deleted / renamed
- `.exe`, `.bat`, `.ps1`, `.vbs` and script extensions
- Suspicious extensions (`.scr`, `.hta`, `.lnk`, etc.)
- 5+ modifications within 10 seconds on same path → Rapid Modification

---

### Phase 7 — Real Quarantine Engine

**Completed items:**

- `backend/services/quarantine_service.py` — move/isolate/restore/delete, SHA-256, metadata JSON
- `backend/utils/quarantine_files.py` — hash, sanitize filename, integrity verify
- `backend/api/quarantine_routes.py` — full REST API + multipart upload for testing
- `backend/models/quarantine_models.py` — Pydantic schemas
- `backend/data/quarantine.db` — `quarantine_items` table
- `backend/quarantine/files/` — physical isolation (`.quarantine` suffix)
- `backend/quarantine/metadata/{id}.json` — per-file metadata snapshots
- `backend/logs/quarantine_events.log` — rotating audit log
- Threat log integration via `threat_log_service.log_security_event()`
- Dashboard `quarantined_files` synced from active quarantine count
- `src/hooks/useQuarantine.ts` — **3s** refresh, actions, notifications
- `src/app/components/Quarantine.tsx` — live table (layout preserved), modals, manual quarantine

**Statuses:** `quarantined`, `restored`, `deleted`

**Docs:** `docs/QUARANTINE.md`

---

### Phase 8 — Ransomware Detection + Auto Quarantine

**Completed items:**

- `backend/monitoring/ransomware_monitor.py` — watchdog heuristics (bursts, entropy, encrypted extensions)
- `backend/services/ransomware_service.py` — SQLite events, settings JSON, auto-quarantine, threat log integration
- `backend/api/ransomware_routes.py` — status, events, start/stop, settings
- `backend/data/ransomware.db`, `backend/data/ransomware_settings.json`
- `backend/logs/ransomware_events.log`
- `src/hooks/useRansomware.ts` — 3s refresh, enable/disable, settings toggles
- `src/app/components/RansomwareDetection.tsx` — live stats, layers, event history (layout preserved)

**Protection statuses:** Protected, Monitoring, Suspicious Activity, Threat Detected

**Docs:** `docs/RANSOMWARE_DETECTION.md`

---

## 5. Active Backend Routes

### `GET /health`

| Field | Value |
|-------|-------|
| **Purpose** | Service liveness check |
| **Response** | `{ "status": "ok", "service": "AllSafe Security API" }` |
| **Frontend** | Not used by UI currently |

---

### `GET /system-stats`

| Field | Value |
|-------|-------|
| **Purpose** | Live system metrics (canonical root path) |
| **Response** | `SystemStatsResponse`: `cpu_usage`, `ram_usage`, `disk_usage`, `network_sent`, `network_received`, `running_processes`, `uptime` |
| **Frontend** | Available via API; dashboard uses `/dashboard/overview` instead |

---

### `GET /system/stats`

| Field | Value |
|-------|-------|
| **Purpose** | Same as `/system-stats` under `/system` prefix |
| **Response** | Identical to `SystemStatsResponse` |
| **Frontend** | Not directly used by UI currently |

---

### `GET /processes`

| Field | Value |
|-------|-------|
| **Purpose** | Top running processes sorted by CPU |
| **Response** | `ProcessListResponse` (see Phase 3) |
| **Frontend** | `ProcessMonitor.tsx`, `useDashboard.ts` (top 5 processes) |

---

### `GET /dashboard/overview`

| Field | Value |
|-------|-------|
| **Purpose** | Aggregated security + system snapshot for dashboard |
| **Response** | `DashboardOverviewResponse`: `system_health`, `cpu_usage`, `ram_usage`, `disk_usage`, `network_activity`, `running_processes`, `uptime`, `active_threats`, `blocked_threats`, `quarantined_files`, `usb_devices_connected`, `last_scan_time`, `protection_status`, `security_score`, `network_connections` |
| **Frontend** | `Dashboard.tsx` via `useDashboard.ts` |

---

### `GET /usb/devices`

| Field | Value |
|-------|-------|
| **Purpose** | Currently connected USB devices with protection status |
| **Response** | `UsbDeviceListResponse`: `devices[]`, `total_connected`, `safe_count`, `threat_count`, `scanning_count` |
| **Frontend** | `UsbProtection.tsx` via `useUsbMonitor.ts` |

---

### `GET /usb/history`

| Field | Value |
|-------|-------|
| **Purpose** | Recent USB insert/remove events (in-memory deque, max 200) |
| **Response** | `UsbHistoryResponse`: `events[]`, `total_events` |
| **Frontend** | `UsbProtection.tsx` via `useUsbMonitor.ts` |

---

### `POST /usb/scan`

| Field | Value |
|-------|-------|
| **Purpose** | Force immediate USB rescan + drive root heuristic check |
| **Response** | `{ "status": "ok", "message": "USB scan completed" }` |
| **Frontend** | `UsbProtection.tsx` — `triggerUsbScan()` |

---

### `GET /threats/logs`

| Field | Value |
|-------|-------|
| **Purpose** | Paginated filesystem security events |
| **Query params** | `page`, `page_size`, `severity`, `category`, `search` |
| **Response** | `ThreatLogListResponse`: `logs[]`, `total`, `page`, `page_size`, `total_pages` |
| **Log entry fields** | `id`, `timestamp`, `file_path`, `event_type`, `severity`, `category`, `process_name`, `status`, `description` |
| **Frontend** | `ThreatLogs.tsx` via `useThreatLogs.ts` |

---

### `GET /threats/stats`

| Field | Value |
|-------|-------|
| **Purpose** | Threat totals and dashboard-aligned counters |
| **Response** | `ThreatStatsResponse`: `total_threats`, `critical_count`, `high_count`, `medium_count`, `low_count`, `active_threats`, `blocked_threats`, `events_last_24h`, `detection_rate_percent`, `monitoring_active`, `watched_paths` |
| **Frontend** | `ThreatLogs.tsx` (stat cards), `useDashboard.ts` (threat chart) |

---

### `POST /threats/clear`

| Field | Value |
|-------|-------|
| **Purpose** | Delete all rows from SQLite threat log table |
| **Response** | `{ "cleared": <int>, "status": "ok" }` |
| **Frontend** | API function `clearThreatLogs()` exists; **no UI button wired yet** |

---

### `POST /quarantine/add`

| Field | Value |
|-------|-------|
| **Purpose** | Quarantine file by absolute path (move to secure storage) |
| **Body** | `file_path`, `reason`, `severity`, `category`, `source_event_id?` |
| **Response** | `QuarantineActionResponse` |
| **Frontend** | `Quarantine.tsx` — path input in test modal |

---

### `POST /quarantine/upload`

| Field | Value |
|-------|-------|
| **Purpose** | Upload file for manual quarantine testing |
| **Response** | `QuarantineActionResponse` |
| **Frontend** | `Quarantine.tsx` — file picker |

---

### `GET /quarantine/items`

| Field | Value |
|-------|-------|
| **Purpose** | List quarantine records (default `status=quarantined`) |
| **Query** | `status`, `severity`, `search` |
| **Response** | `QuarantineItemListResponse` |
| **Frontend** | `Quarantine.tsx` via `useQuarantine.ts` |

---

### `GET /quarantine/stats`

| Field | Value |
|-------|-------|
| **Purpose** | Stat cards: active, critical, total size, lifetime count |
| **Response** | `QuarantineStatsResponse` |
| **Frontend** | `Quarantine.tsx` |

---

### `GET /quarantine/items/{id}`

| Field | Value |
|-------|-------|
| **Purpose** | Single item details |
| **Frontend** | Available via API; details modal uses list row data |

---

### `POST /quarantine/restore/{id}`

| Field | Value |
|-------|-------|
| **Purpose** | Restore file to `original_path` (integrity check + conflict validation) |
| **Frontend** | `Quarantine.tsx` restore button |

---

### `DELETE /quarantine/delete/{id}`

| Field | Value |
|-------|-------|
| **Purpose** | Permanently delete quarantined file from disk |
| **Frontend** | `Quarantine.tsx` delete button |

---

### `POST /quarantine/clear`

| Field | Value |
|-------|-------|
| **Purpose** | Delete all active quarantined files |
| **Frontend** | `Quarantine.tsx` Clear All |

---

## 6. Frontend Hooks

### `useDashboard`

| Property | Detail |
|----------|--------|
| **File** | `src/hooks/useDashboard.ts` |
| **Refresh interval** | 5000 ms (`REFRESH_INTERVAL_MS`) |
| **APIs** | `GET /dashboard/overview`, `GET /processes`, `GET /threats/stats` |
| **UI component** | `Dashboard.tsx` |
| **Returns** | `overview`, `recentProcesses`, `performanceHistory`, `threatHistory`, `networkThroughput`, `changes`, `isLoading`, `isRefreshing`, `error`, `reload` |
| **Notes** | Chart history keeps last 7 poll points; threat chart uses `events_last_24h` when stats API succeeds |

### `useUsbMonitor`

| Property | Detail |
|----------|--------|
| **File** | `src/hooks/useUsbMonitor.ts` |
| **Refresh interval** | 3000 ms (`USB_REFRESH_INTERVAL_MS`) |
| **APIs** | `GET /usb/devices`, `GET /usb/history`, `POST /usb/scan` |
| **UI component** | `UsbProtection.tsx` |
| **Returns** | `devices`, `history`, `stats`, `isLoading`, `isRefreshing`, `isScanning`, `error`, `reload`, `scanAllDevices` |

### `useThreatLogs`

| Property | Detail |
|----------|--------|
| **File** | `src/hooks/useThreatLogs.ts` |
| **Refresh interval** | 3000 ms (`THREAT_REFRESH_INTERVAL_MS`) |
| **APIs** | `GET /threats/logs`, `GET /threats/stats` |
| **UI component** | `ThreatLogs.tsx` |
| **Returns** | `logs`, `stats`, `page`, `total`, `totalPages`, filters, `isLoading`, `isRefreshing`, `error`, `reload`, `goToPage` |
| **Mapping** | `mapThreatLogToViewModel()` maps API fields → table columns (`type`←`category`, `threat`←`description`, `action`←`status`, `source`← path folder or `process_name`) |

### `useQuarantine`

| Property | Detail |
|----------|--------|
| **File** | `src/hooks/useQuarantine.ts` |
| **Refresh interval** | 3000 ms (`QUARANTINE_REFRESH_INTERVAL_MS`) |
| **APIs** | `GET /quarantine/items`, `GET /quarantine/stats`, `POST /add`, `POST /upload`, restore, delete, clear |
| **UI component** | `Quarantine.tsx` |
| **Returns** | `items`, `stats`, filters, `restoreItem`, `deleteItem`, `clearAll`, `quarantineByPath`, `quarantineUpload`, `notice`, `exportCsv` |

### Non-hook live screen

| Component | Pattern |
|-----------|---------|
| `ProcessMonitor.tsx` | Inline `useCallback` + `useEffect` polling at 5s (same pattern as hooks, no separate file) |

---

## 7. Current Features Working

### REAL FEATURES

| Feature | Status |
|---------|--------|
| Live dashboard | ✅ `GET /dashboard/overview` + charts |
| Process monitor | ✅ `GET /processes`, 5s refresh, risk badges |
| USB monitoring | ✅ WMI poll, device list, history, scan, 3s refresh |
| File system monitoring | ✅ watchdog background observer |
| Threat logging | ✅ SQLite + API + live Threat Logs page |
| Threat severity/category classification | ✅ Rule-based in `file_monitor.py` |
| Dashboard threat counters | ✅ Synced from SQLite via `threat_log_service` |
| Charts (CPU/RAM/threat) | ✅ Recharts with polled data |
| Auto-refresh | ✅ 3s (USB, threats), 5s (dashboard, processes) |
| SQLite persistence | ✅ `threat_logs.db` |
| Rotating audit logs | ✅ `allsafe.log`, `usb_events.log`, `threat_events.log` |
| Tauri desktop shell | ✅ Dev and production build |
| Windows security telemetry | ✅ Defender/firewall/connection counts in overview |
| USB heuristic threat reasons | ✅ Filename/extension scan on drive root |
| Threat Logs export (current page) | ✅ Client-side CSV from loaded rows |
| Quarantine engine | ✅ Move/restore/delete, SHA-256, SQLite, threat audit logs |
| Quarantine UI | ✅ Live table, modals, manual upload/path test, 3s refresh |
| Error handling + retry banners | ✅ Dashboard, Process, USB, Threat Logs, Quarantine |

### PLACEHOLDER FEATURES (UI only, no backend)

| Feature | Component | Notes |
|---------|-----------|-------|
| Ransomware detection | `RansomwareDetection.tsx` | Static stats and buttons |
| AI threat analysis | `AiAnalysis.tsx` | Static chart data arrays |
| Settings persistence | `Settings.tsx` | Local toggles, no API |
| Global header search | `Header.tsx` | Input not connected |
| Sidebar “Real-time Protection Active” | `Sidebar.tsx` | Always shows green/active |
| `POST /threats/clear` UI | — | API exists, no button in Threat Logs |
| Process kill / block actions | `ProcessMonitor.tsx` | Display only |
| USB physical blocking | — | Policy flags only, no enforcement |

---

## 8. Placeholder / Not Yet Implemented

The following are **not implemented** in backend or live frontend integration:

- Real malware / antivirus scanning (signature engine)
- Ransomware rollback / recovery
- YARA rule scanning
- Deep behavior / EDR behavior analysis engine
- Kernel-mode or driver-level protection
- AI / ML threat analysis engine (beyond static UI)
- USB device blocking / port control enforcement
- Settings save/load to disk
- Dedicated `useProcesses` hook (optional refactor only)
- Tauri-managed Python backend process (backend started manually today)
- Process attribution on file events (`process_name` usually empty)
- Historical threat time-series API (chart uses rolling poll snapshots)

---

## 9. Coding Conventions

### Modular architecture

- **Backend:** `monitoring/` (collectors) → `services/` (state, threads, persistence) → `api/` (HTTP) → `models/` (schemas)
- **Frontend:** `lib/api.ts` (HTTP + types) → `hooks/` (polling state) → `components/` (UI)
- New features should add a vertical slice, not modify unrelated modules

### Async-ready backend

- FastAPI `async` route handlers
- Blocking OS calls wrapped in `asyncio.to_thread()` (monitors, dashboard build, threat DB)
- Background **daemon threads** for USB polling and watchdog observer (not asyncio tasks)

### TypeScript interfaces

- API response types defined in `src/lib/api.ts`
- View models via mapper functions (`mapProcessToViewModel`, `mapUsbDeviceToViewModel`, `mapThreatLogToViewModel`)

### Hooks pattern

- `useCallback` for load functions
- `useEffect` + `setInterval` for polling
- `silent` refresh flag to avoid full-page loading flicker
- `ApiError` for user-facing messages

### Service layer pattern

- Singleton services: `usb_service`, `threat_log_service` via `get_instance()`
- Started/stopped in FastAPI `lifespan` in `main.py`

### Logging strategy

- Root logger: console + rotating `backend/logs/allsafe.log` (5 MB × 3)
- Domain loggers: `allsafe.usb` → `usb_events.log`, `allsafe.threats` → `threat_events.log`
- Python `logging` module throughout; no structured JSON logs

### Error handling strategy

- Custom exceptions in `utils/exceptions.py`
- FastAPI handlers return `{ "detail": "...", "error": "<code>" }`
- Frontend: try/catch → `ApiError` message → banner + Retry button
- File monitor start failure: logged; API continues without filesystem events

---

## 10. Database & Logging

### SQLite usage

| Database | Path | Table | Purpose |
|----------|------|-------|---------|
| Threat logs | `backend/data/threat_logs.db` | `threat_logs` | Persistent security events |

**Schema columns:** `id`, `timestamp`, `file_path`, `event_type`, `severity`, `category`, `process_name`, `status`, `description`

**Indexes:** `timestamp`, `severity`, `category`

### JSON policy files (not SQLite)

| File | Purpose |
|------|---------|
| `backend/data/trusted_usb_devices.json` | Trusted device IDs and serials |
| `backend/data/blocked_usb_devices.json` | Blocked device IDs and serials |

### Rotating log files

| Log | Path | Max size | Backups |
|-----|------|----------|---------|
| Application | `backend/logs/allsafe.log` | 5 MB | 3 |
| USB events | `backend/logs/usb_events.log` | FileHandler (no rotation in usb logger) | — |
| Threat events | `backend/logs/threat_events.log` | 5 MB | 3 |

Runtime logs are created on first backend start. `logs/.gitkeep` tracks the directory only.

---

## 11. Current Commands

### Backend startup

```powershell
cd F:\ALL-Safe\backend
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

Optional environment variables:

- `ALLSAFE_DEBUG=true` — debug logging + uvicorn reload if launched via `python main.py`
- `ALLSAFE_HOST`, `ALLSAFE_PORT` — bind address
- `VITE_API_URL` — frontend API base (default `http://127.0.0.1:8000`)

### Frontend startup (browser / Vite only)

```powershell
cd F:\ALL-Safe
npm install
npm run dev
```

Opens `http://localhost:5173` — **requires backend running separately**.

### Tauri desktop startup

```powershell
cd F:\ALL-Safe
npm install
# Start backend in a second terminal first
npm run tauri:dev
```

### Production build

```powershell
# Frontend bundle
cd F:\ALL-Safe
npm run build

# Windows desktop installer
npm run tauri:build
# Output: src-tauri/target/release/bundle/
```

Backend production: run uvicorn without reload; no packaged Python bundle in Tauri artifact today.

---

## 12. Important Development Rules

1. **NEVER redesign existing UI** — connect backend to current components
2. **Preserve animations** — transitions, pulse indicators, hover states
3. **Preserve layout** — slate cyber theme (`#0F172A`, `#1E293B`, `#334155`, `#F8FAFC`, `#94A3B8`)
4. **Connect backend to existing components** — replace static data only
5. **Modular development only** — one feature per vertical slice
6. **One feature at a time** — complete phase before expanding scope
7. **Windows 10/11 compatibility** — use WMI, psutil, watchdog paths appropriate for Windows profiles
8. **Local-only** — no cloud APIs or external telemetry
9. **Do not commit secrets** — `.env` for overrides only
10. **Minimize diff scope** — match existing naming and patterns in each file touched

---

## 13. Current Pending Tasks

These are the **next logical integrations** based on UI screens that already exist but lack backend wiring (not speculative features):

| Priority area | Work needed |
|---------------|-------------|
| Ransomware Detection | Real detection signals (can build on `file_monitor` rapid-mod rules) + API |
| Auto-quarantine from threat logs | One-click quarantine from Threat Logs rows |
| AI Threat Analysis | Backend analysis endpoint + wire `AiAnalysis.tsx` |
| Settings | Persist preferences (JSON or SQLite) + wire `Settings.tsx` |
| Dashboard `quarantined_files` | Increment counter when quarantine engine exists |
| Threat clear UI | Optional button calling `POST /threats/clear` without layout change |
| USB blocking | Enforcement layer beyond policy flags |
| Malware scanning | Signature or engine integration (explicitly out of Phase 6 scope) |

---

## 14. Known Issues / Technical Notes

### FastAPI reload behavior

- `uvicorn` with `reload=True` only when running `python main.py` with `ALLSAFE_DEBUG=true`
- Reload restarts process → **restarts USB and file background monitors**
- For stable monitoring during dev, run uvicorn **without** reload

### Background monitoring lifecycle

- Started in FastAPI `lifespan` on app startup
- Stopped on shutdown
- USB: 1s poll thread (`usb-monitor`)
- Files: watchdog `Observer` thread (watchdog internal)
- If file monitor fails to start, API runs but `monitoring_active` may be `false`

### Polling architecture

- Frontend uses HTTP polling, not WebSockets
- Multiple intervals (3s vs 5s) — acceptable for local desktop
- Threat chart is **not** a true 24-hour time series database; it plots `events_last_24h` total at each poll (or active threats fallback)

### Current limitations

- High volume of file events possible (Downloads/Documents activity) — all logged to SQLite
- `process_name` on threat events is usually empty (watchdog does not provide process info)
- `quarantined_files` in dashboard stays **0** unless manually extended
- Tauri app does not auto-start Python backend
- Duplicate system stats routes (`/system-stats` and `/system/stats`)
- `ProcessMonitor` does not use a shared hook file (pattern duplication only)
- Risk levels on processes are **heuristic** (CPU/RAM thresholds), not threat intelligence

---

## 15. AI Continuation Instructions

**Read this file completely before continuing development.**

When continuing work on AllSafe:

1. **Preserve architecture** — React → (Tauri) → FastAPI → monitoring/services; do not introduce cloud dependencies without explicit request.
2. **Preserve design system** — Dark slate UI, inline styles + Tailwind, lucide icons, existing table/card layouts.
3. **Avoid rewriting working modules** — Extend `usb_service` / `threat_log_service` patterns rather than replacing them.
4. **Continue phase-by-phase** — Wire one placeholder screen at a time to a new backend slice (`monitoring` + `services` + `api` + `models` + hook).
5. **Update this file** after each completed phase — add routes, hooks, and move items from Placeholder to Real Features.
6. **Also read** `AI_CONTEXT.md` for mission, UI philosophy, and strict do/don't rules.
7. **Test on Windows** — Paths, WMI, and watchdog behavior are Windows-oriented.
8. **Keep backend and frontend in sync** — Add TypeScript types in `api.ts` when adding Pydantic models.

**Do not:**

- Redesign Threat Logs, Dashboard, or Sidebar without explicit user request
- Replace polling with WebSockets unless requested
- Add antivirus scanning while building unrelated features
- Guess future roadmap items in this document — document only what ships

---

*End of PROJECT_STATUS.md*
