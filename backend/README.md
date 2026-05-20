# AllSafe Python Backend (Phase 2)

Local-only **FastAPI** service that exposes real Windows system metrics to the AllSafe Tauri desktop app.

```
React UI  →  Tauri  →  FastAPI (this backend)  →  psutil / Windows APIs
```

## Folder structure

```
backend/
├── api/
│   ├── __init__.py          # Aggregates API routers
│   └── system_routes.py     # GET /system/stats
├── monitoring/
│   ├── __init__.py
│   └── system_monitor.py    # psutil metric collection (async-ready)
├── services/                # Future: USB, threats, quarantine logic
│   └── __init__.py
├── models/
│   ├── __init__.py
│   └── system_models.py     # Pydantic response schemas
├── utils/
│   ├── __init__.py
│   ├── exceptions.py        # Shared error types
│   └── logging_config.py    # Console + rotating file logs
├── logs/                    # Runtime logs (allsafe.log)
├── config.py                # Host, port, CORS, settings
├── main.py                  # FastAPI app entry point
├── requirements.txt
└── README.md
```

## File responsibilities

| File | Role |
|------|------|
| `main.py` | Creates the FastAPI app, CORS, lifespan logging, `GET /system-stats`, `GET /health`, exception handlers |
| `config.py` | Central settings (bind address, CORS origins for Tauri/Vite) |
| `monitoring/system_monitor.py` | Reads CPU, RAM, disk, network, process count, uptime via **psutil** |
| `api/system_routes.py` | Namespaced route `GET /system/stats` (same data as root endpoint) |
| `models/system_models.py` | Validates and documents API JSON responses |
| `utils/logging_config.py` | Writes to `logs/allsafe.log` and stdout |
| `services/` | Placeholder package for future modules (process monitor, USB, ransomware, etc.) |

## Prerequisites

- **Python 3.11+** (3.12 recommended)
- Windows 10 or 11

Verify Python:

```powershell
python --version
```

## Virtual environment setup

From the project root:

```powershell
cd F:\ALL-Safe\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Start the API (development)

With the virtual environment activated:

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Alternative:

```powershell
python main.py
```

- API base: `http://127.0.0.1:8000`
- Interactive docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

## Test locally

**PowerShell:**

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/system-stats
```

**curl:**

```powershell
curl http://127.0.0.1:8000/system-stats
```

Example response:

```json
{
  "cpu_usage": 12.5,
  "ram_usage": 48.2,
  "disk_usage": 62.1,
  "network_sent": 1048576,
  "network_received": 2097152,
  "running_processes": 245,
  "uptime": "1d 3h 22m 5s"
}
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/system-stats` | Primary system metrics (desktop integration) |
| GET | `/system/stats` | Same metrics, namespaced |
| GET | `/processes` | Top 50 processes by CPU (real psutil data) |
| GET | `/dashboard/overview` | Live dashboard aggregation (system + security) |
| GET | `/usb/devices` | Connected USB storage devices |
| GET | `/usb/history` | USB connect/disconnect history |
| POST | `/usb/scan` | Force USB rescan |
| GET | `/health` | Service health |
| GET | `/docs` | Swagger UI |

### Process monitor example

```powershell
Invoke-RestMethod http://127.0.0.1:8000/processes | ConvertTo-Json -Depth 4
```

## CORS (Tauri)

Allowed origins (local desktop only):

- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `https://tauri.localhost`
- `tauri://localhost`

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLSAFE_DEBUG` | `false` | Enable debug logging |
| `ALLSAFE_HOST` | `127.0.0.1` | Bind address |
| `ALLSAFE_PORT` | `8000` | Bind port |
| `ALLSAFE_CPU_SAMPLE_INTERVAL` | `0.1` | CPU percent sample window (seconds) |

## Future modules

The layout supports adding without restructuring:

- `monitoring/process_monitor.py` — suspicious process tracking
- `monitoring/usb_monitor.py` — removable device detection
- `services/threat_service.py` — threat log persistence
- `services/quarantine_service.py` — isolated file handling
- `api/threat_routes.py` — new routers included from `api/__init__.py`

## Security note

This server binds to **127.0.0.1** only. Do not expose it to the public internet; it is intended for the local AllSafe desktop process.
