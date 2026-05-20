# Ransomware Detection (Phase 8)

Heuristic real-time ransomware behavior monitoring with optional auto-quarantine.

## Workflow

```
watchdog (protected folders)
        ↓
ransomware_monitor.py — heuristics + sensitivity thresholds
        ↓
ransomware_service.py — SQLite event, threat log, auto-quarantine
        ↓
GET /ransomware/status + /events
        ↓
RansomwareDetection.tsx (3s refresh)
```

## Protected folders (default)

- Desktop, Documents, Downloads, Pictures

## Heuristics

| Signal | Severity |
|--------|----------|
| `.encrypted`, `.locked`, `.crypt`, etc. | CRITICAL |
| Rapid modifications in folder | CRITICAL |
| Mass rename burst | CRITICAL |
| Write/script burst | HIGH |
| High entropy sample (4KB) | HIGH |
| Executable in Downloads/AppData/Temp | HIGH |

## Settings (`backend/data/ransomware_settings.json`)

- `monitoring_enabled` — auto-start on backend boot
- `auto_quarantine` — move flagged files via quarantine service
- `sensitivity` — `low` | `medium` | `high`
- `protected_folders` — custom path list

## API

| Method | Path |
|--------|------|
| GET | `/ransomware/status` |
| GET | `/ransomware/events` |
| GET | `/ransomware/settings` |
| POST | `/ransomware/start` |
| POST | `/ransomware/stop` |
| POST | `/ransomware/settings` |

## Commands

```powershell
cd F:\ALL-Safe\backend
uvicorn main:app --host 127.0.0.1 --port 8000
```

```powershell
cd F:\ALL-Safe
npm run dev
```

Test: enable protection, then rapidly touch many files in Downloads or rename files with a `.locked` extension.
