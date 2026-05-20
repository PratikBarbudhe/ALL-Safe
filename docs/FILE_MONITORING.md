# Real-Time File System Monitoring

AllSafe uses **watchdog** to monitor high-risk user directories on Windows 10/11 and persist security events locally.

## Architecture

```
watchdog Observer (background thread)
        ↓
monitoring/file_monitor.py   — classify events, detect bursts
        ↓
services/threat_log_service.py — SQLite + rotating threat_events.log
        ↓
api/threat_routes.py         — REST API
        ↓
React Threat Logs + Dashboard widgets
```

## Watched paths

- `%USERPROFILE%\Desktop`
- `%USERPROFILE%\Downloads`
- `%USERPROFILE%\Documents`
- `%TEMP%` / `%TMP%`

## Detection rules

| Signal | Category | Typical severity |
|--------|----------|------------------|
| File created / modified / deleted / renamed | File Activity | LOW–MEDIUM |
| `.exe`, `.bat`, `.ps1`, `.vbs` created | Suspicious Executable | HIGH–CRITICAL |
| Scripts in Temp | Script Execution | CRITICAL |
| `.scr`, `.hta`, `.lnk`, etc. | Suspicious Executable | HIGH |
| 5+ modifications in 10 seconds | Rapid Modification | CRITICAL |
| Rare extensions (`.encrypted`, etc.) | Unknown File Type | MEDIUM |

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/threats/logs` | Paginated logs (`page`, `page_size`, `severity`, `category`, `search`) |
| GET | `/threats/stats` | Totals, severity breakdown, 24h activity |
| POST | `/threats/clear` | Clear SQLite threat log table |

Dashboard overview (`GET /dashboard/overview`) syncs `active_threats` and `blocked_threats` from persisted logs on each request.

## Storage

- **SQLite:** `backend/data/threat_logs.db`
- **Rotating log:** `backend/logs/threat_events.log` (5 MB × 3 backups)

## Run commands

```powershell
cd f:\ALL-Safe\backend
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

```powershell
cd f:\ALL-Safe
npm install
npm run dev
```

Monitoring starts automatically with the FastAPI lifespan hook alongside USB monitoring.
