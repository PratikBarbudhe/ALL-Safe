# Phase 4 — Live Dashboard

## Architecture

```
Dashboard.tsx → useDashboard() → GET /dashboard/overview
                              → GET /processes (top 5 for widget)
         ↓
DashboardService → SystemMonitor + ProcessMonitor + Windows security (PowerShell)
                → ThreatCounterStore (in-memory, swappable)
```

## Run

```powershell
# Backend
cd F:\ALL-Safe\backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Frontend
cd F:\ALL-Safe
npm run dev
```

Charts build rolling history client-side (7 samples, 5s interval). Network throughput is derived from byte deltas between polls.

## Real vs placeholder data

| Field | Source |
|-------|--------|
| CPU / RAM / Disk / Network / Uptime / Processes | psutil |
| Defender / Firewall | PowerShell |
| USB count | WMI via PowerShell |
| Network connections | PowerShell |
| active_threats / blocked / quarantine | `ThreatCounterStore` (replace later) |
