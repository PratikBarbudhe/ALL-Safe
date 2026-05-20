# AllSafe — AI Context & Development Guide

> Permanent context for Cursor, Copilot, and other AI assistants working on this repository.  
> Pair with **`PROJECT_STATUS.md`** for factual implementation state.

---

## Project Mission

**AllSafe** (“All Safe”) is a **local-only Windows desktop cybersecurity application** that gives users a professional security operations center (SOC) style experience without cloud accounts, subscriptions, or data leaving the machine.

### Core mission

1. **Observe** — System health, processes, USB devices, and filesystem activity in real time.
2. **Detect** — Rule-based security events (heuristics, not full antivirus yet).
3. **Report** — Dashboard widgets, threat logs, and audit files the user can review.
4. **Protect (progressive)** — Build toward quarantine, blocking, and advanced analysis **one module at a time**.

### What AllSafe is today

A **monitoring and logging platform** with a polished cyber dashboard UI and a modular FastAPI backend. It behaves like a lightweight EDR sensor for file and USB activity on Windows.

### What AllSafe is not today

- Not a replacement for Windows Defender or commercial AV
- Not an AI-powered SOC in production (AI screen is UI-only)
- Not a cloud-connected security product

---

## Cybersecurity Application Goals

| Goal | Current state |
|------|----------------|
| Real-time visibility | ✅ Dashboard, processes, USB, file events |
| Local data sovereignty | ✅ SQLite + local logs only |
| USB risk awareness | ✅ WMI + heuristics + policy JSON |
| Filesystem threat telemetry | ✅ watchdog + severity taxonomy |
| User trust through transparency | ✅ Threat Logs table with paths and descriptions |
| Actual malware neutralization | ❌ Not implemented |
| Automated quarantine | ❌ UI placeholder only |
| Ransomware-specific recovery | ❌ UI placeholder only |

**Guiding principle:** Ship **observable, honest** features before **marketing-style** capabilities. Never imply blocking or AI analysis is active when it is static UI.

---

## UI Philosophy

### Design origin

UI is based on the **Cybersecurity Dashboard Design** (Figma-derived). The visual language is intentional and must be preserved.

### Visual system

| Element | Convention |
|---------|------------|
| Page background | `#0F172A` |
| Card / panel | `#1E293B`, border `#334155` |
| Primary text | `#F8FAFC` |
| Muted text | `#94A3B8` |
| Accent / actions | `#3B82F6` |
| Danger | `#EF4444` |
| Success | `#10B981` |
| Warning / medium | `#F59E0B` / `#EAB308` |
| High severity | `#F97316` (orange) |
| Low severity | `#3B82F6` (blue) |

### Layout rules

- **Sidebar navigation** — `useState` screen switching in `App.tsx` (no React Router in production flow today)
- **Fixed viewport pages** — `height: calc(100vh - 4rem)` on main screens
- **Tables** — Custom HTML tables with inline styles on primary screens (not forced through shadcn `Table` on Threat Logs)
- **Stat cards** — Icon + large number + label pattern
- **Animations** — `transition-opacity`, `transition-colors`, `animate-pulse` on status dots; keep smooth, subtle

### UX principles for AI implementers

1. **Same layout, new data** — Swap mock arrays for API hooks; do not reorganize grids or rename columns without user approval.
2. **Loading without layout shift** — Use opacity transitions and `—` placeholders, not skeleton redesigns, unless the screen already uses pulses.
3. **Errors are visible** — Red banner + Retry; match `Dashboard.tsx` / `ThreatLogs.tsx` pattern.
4. **Empty states are informative** — Explain that monitoring is active when tables are empty.
5. **Severity is color-coded consistently** — See `ThreatLogs.tsx` badge colors.

---

## Architecture Philosophy

```
Presentation (React)
    ↕ REST / JSON
Application API (FastAPI routes)
    ↕
Domain services (state, policy, persistence)
    ↕
Infrastructure monitors (psutil, WMI, watchdog)
    ↕
Operating system (Windows)
```

### Rules

- **Monitors are dumb collectors** — No HTTP, no SQLite in `monitoring/`.
- **Services own state** — Threads, deques, singletons, DB writes live in `services/`.
- **Routes are thin** — Validate inputs, call service, return Pydantic models.
- **Frontend never embeds security logic** — Risk colors and labels may be derived client-side for display only; authoritative classification stays in Python for threats/USB.

### Tauri role

- Hosts the web UI in a native window
- Does **not** currently embed or spawn the Python backend
- Future native features (tray, notifications) should use Tauri plugins without breaking the React layout

---

## Coding Style

### Python (backend)

- Python 3.10+ style (type hints, `|` unions)
- Pydantic v2 models for all API responses
- `logging.getLogger(__name__)` per module
- Prefer explicit exception types in `utils/exceptions.py`
- Use `asyncio.to_thread` for blocking work from async routes
- Singleton services with `get_instance()` where background state is required

### TypeScript (frontend)

- Functional components + hooks
- API types colocated in `src/lib/api.ts`
- Path alias `@/` → `src/`
- Prefer `useCallback` + stable polling intervals
- Export interval constants (`REFRESH_INTERVAL_MS`, etc.) from `api.ts`

### Naming

| Layer | Pattern | Example |
|-------|---------|---------|
| Monitor | `*_monitor.py` | `file_monitor.py` |
| Service | `*_service.py` | `threat_log_service.py` |
| Routes | `*_routes.py` | `threat_routes.py` |
| Models | `*_models.py` | `threat_models.py` |
| Hook | `useFeature.ts` | `useThreatLogs.ts` |

---

## Strict Do / Don’t Rules

### DO

- Read **`PROJECT_STATUS.md`** fully before any multi-file change
- Follow the established **monitoring → service → api → models** slice
- Use existing hooks or mirror `useUsbMonitor` / `useThreatLogs` patterns
- Keep CORS/local-only assumptions
- Update **`PROJECT_STATUS.md`** when a phase completes
- Run backend on Windows when testing WMI/watchdog
- Preserve cyber color palette and spacing
- Write minimal, focused diffs
- Use `ApiError` and backend `detail` messages for user-facing errors

### DON’T

- **Redesign** Dashboard, Threat Logs, Sidebar, or USB pages without explicit request
- **Remove** animations, gradients, or table structures for “cleanliness”
- **Replace** working polling integrations with mock data
- **Add** cloud APIs, telemetry SDKs, or external auth
- **Implement** antivirus scanning as a side effect of another task
- **Rewrite** entire modules when a 20-line integration suffices
- **Introduce** React Router unless the user asks for URL routing
- **Commit** `.env`, credentials, or `threat_logs.db` with real user data
- **Assume** Tauri starts the backend — document two-terminal workflow
- **Fabricate** features in status docs — document only what exists

---

## Development Methodology

### Phase-based delivery

Each phase delivers:

1. Backend monitor and/or service
2. Pydantic models + routes
3. `api.ts` types + fetch functions
4. Hook (or inline polling matching hooks)
5. Wire **existing** React component
6. Short doc in `docs/` if non-trivial
7. Update `PROJECT_STATUS.md`

### Order of operations for a new feature

```
1. models → 2. monitoring/service → 3. routes → 4. register router
→ 5. lifespan if background → 6. api.ts → 7. hook → 8. component
```

### Testing expectations

- Manual test on Windows: start backend, start frontend, exercise UI
- Filesystem: create/modify files in Downloads to populate Threat Logs
- USB: insert/removable drive to populate USB page
- No requirement for automated test suite unless user requests it

### Git / commits

- Commit only when user asks
- Never force-push `main`
- Never skip hooks unless user requests

---

## Prompt Guidelines for AI

When the user asks for a feature, respond by:

1. **Checking PROJECT_STATUS.md** — Is it already done? Is it placeholder?
2. **Scoping to one phase** — Refuse scope creep (e.g. don’t add AV + quarantine + AI in one pass).
3. **Naming the slice** — Which monitor, service, route, hook, component?
4. **Stating what stays unchanged** — UI layout, colors, navigation.
5. **Providing exact commands** — Backend + frontend + Tauri if relevant.

### Good request examples

- “Wire Quarantine page to a new `/quarantine` API using the same table layout.”
- “Add POST /threats/clear button to Threat Logs without changing the header design.”
- “Persist Settings toggles to a JSON file in backend/data.”

### Bad request handling

If the user asks to “make it work like CrowdStrike,” clarify that only **implemented modules** can be extended, and propose the next **single** phase from Pending Tasks in `PROJECT_STATUS.md`.

### Response format preferences

- Concise, technical blog quality prose
- Code citations as `startLine:endLine:filepath` for navigation
- Markdown links for paths and URLs
- No engagement bait at end of messages
- Proportional length to task complexity

---

## How Cursor Should Behave

### On every new chat

1. Read **`PROJECT_STATUS.md`** (full file)
2. Read **`AI_CONTEXT.md`** (this file) for rules and tone
3. Inspect only files relevant to the user’s request
4. Prefer editing existing files over creating parallel implementations

### When implementing

- Match indentation and import style of the target file
- Do not add comments unless logic is non-obvious
- Do not add tests unless user asks or they cover real behavior
- Use parallel tool calls for exploration, not serial guesswork
- Run commands in the real environment (Windows, PowerShell separators `;`)

### When unsure

- Ask one focused question OR infer from `PROJECT_STATUS.md` Placeholder vs Real tables
- Never invent endpoints not listed in section 5 of PROJECT_STATUS

### When completing work

- Summarize what changed and how to verify
- Remind user to update PROJECT_STATUS if they consider the phase done
- List exact terminal commands

---

## Key File Quick Reference

| Need | File |
|------|------|
| App entry / screens | `src/app/App.tsx` |
| API client | `src/lib/api.ts` |
| Backend entry | `backend/main.py` |
| Router registry | `backend/api/__init__.py` |
| Implementation truth | `PROJECT_STATUS.md` |
| USB docs | `docs/USB_MONITORING.md` |
| Threat/file docs | `docs/FILE_MONITORING.md` |
| Tauri docs | `docs/TAURI_SETUP.md` |

---

## Severity & Category Reference (Threat Logging)

Use these exact strings when extending threat detection:

**Severity:** `low`, `medium`, `high`, `critical`

**Category:**

- `File Activity`
- `Suspicious Executable`
- `Script Execution`
- `Rapid Modification`
- `Unknown File Type`

**Status (UI “Action” column):** `Detected`, `Monitored`, `Blocked`, `Quarantined`, `Logged`

---

## Communication Tone

- Direct, professional, accurate
- Distinguish **monitoring** vs **blocking** vs **scanning** explicitly
- Never claim “real-time AI” or “100% protection” for heuristic rules
- Treat the user as a developer building a serious local security product

---

*This file defines how AI should think about AllSafe. Factual route and file lists live in `PROJECT_STATUS.md`.*
