# Quarantine Engine (Phase 7)

AllSafe quarantine **physically isolates** files on disk with SQLite tracking, metadata JSON, and threat-log audit integration.

## Workflow

```
POST /quarantine/add  or  /quarantine/upload
        ↓
Validate file exists & not already quarantined
        ↓
Insert SQLite row → move file → backend/quarantine/files/{id}_{token}_{name}.quarantine
        ↓
SHA-256 hash + metadata JSON in quarantine/metadata/{id}.json
        ↓
Threat log entry (status: Quarantined)
        ↓
Dashboard quarantined_files counter updated
```

### Restore

1. Verify quarantined file on disk + SHA-256 match  
2. Ensure original path is free  
3. `shutil.move` back to `original_path`  
4. Update status → `restored`, write threat audit log  

### Delete / Clear

- Removes file from `quarantine/files/`  
- Status → `deleted`  
- Threat audit log (status: Blocked)  

## Storage

| Location | Purpose |
|----------|---------|
| `backend/data/quarantine.db` | `quarantine_items` table |
| `backend/quarantine/files/` | Isolated files (`.quarantine` suffix) |
| `backend/quarantine/metadata/` | Per-item JSON snapshots |
| `backend/logs/quarantine_events.log` | Rotating audit log |

## API

| Method | Path |
|--------|------|
| POST | `/quarantine/add` |
| POST | `/quarantine/upload` |
| GET | `/quarantine/items` |
| GET | `/quarantine/stats` |
| GET | `/quarantine/items/{id}` |
| POST | `/quarantine/restore/{id}` |
| DELETE | `/quarantine/delete/{id}` |
| POST | `/quarantine/clear` |

## Commands

```powershell
cd F:\ALL-Safe\backend
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
```

```powershell
cd F:\ALL-Safe
npm run dev
```

Test: open **Quarantine** → **Quarantine File** → upload or paste `C:\...\file.txt`.
