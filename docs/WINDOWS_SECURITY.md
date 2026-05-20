# Windows Security Integration (Phase 9)

AllSafe reads native Windows Defender, Firewall, and system protection state via PowerShell (local-only).

## API

| Method | Path |
|--------|------|
| GET | `/windows-security/status` |
| GET | `/windows-security/defender` |
| GET | `/windows-security/firewall` |
| GET | `/windows-security/system-protection` |
| POST | `/windows-security/quick-scan` |
| POST | `/windows-security/update-signatures` |

## Status values

- `protected`
- `attention_needed`
- `disabled`
- `unavailable`

## Dashboard integration

`GET /dashboard/overview` uses `windows_defender_service` for:

- `protection_status` (Defender + Firewall booleans)
- `last_scan_time` (Defender last quick scan when available)
- `security_score` (adjusted for OS protection health)

## Logs

`backend/logs/windows_security.log` (rotating)

## Commands

```powershell
cd F:\ALL-Safe\backend
uvicorn main:app --host 127.0.0.1 --port 8000
```

View live status: Dashboard Windows Security row + Settings → Security Settings.
