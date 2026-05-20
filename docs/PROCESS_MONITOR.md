# Phase 3 — Process Monitor

## Architecture

```
ProcessMonitor.tsx  →  src/lib/api.ts  →  GET /processes  →  ProcessMonitor (psutil)
```

## Run locally

**Terminal 1 — backend:**

```powershell
cd F:\ALL-Safe\backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 — frontend (browser or Tauri):**

```powershell
cd F:\ALL-Safe
npm run dev
# or: npm run tauri:dev
```

Open Process Monitor in the sidebar. Data refreshes every **5 seconds**.

## Environment

Copy `.env.example` to `.env` if the API is not on the default host:

```
VITE_API_URL=http://127.0.0.1:8000
```

## Risk levels

Until threat-detection modules ship, risk badges use CPU/memory heuristics in `src/lib/api.ts` (`deriveRiskLevel`). Stats cards count risks among the **top 50** processes returned by the API.
