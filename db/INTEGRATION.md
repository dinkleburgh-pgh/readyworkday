# PostgreSQL Integration Guide

## What was built

| File | Purpose |
|------|---------|
| `db/__init__.py` | Package entry point |
| `db/connection.py` | `ThreadedConnectionPool` via psycopg2; `get_conn()` context manager |
| `db/schema.sql` | All `CREATE TABLE IF NOT EXISTS` DDL |
| `db/state.py` | `load_state_pg` / `save_state_pg` / `archive_state_pg` / history |
| `db/fleet.py` | `load_fleet_pg` / `save_fleet_pg` / truck types |
| `db/auth.py` | Users, access requests, sessions |
| `db/communications.py` | Chat messages |
| `db/audit.py` | Audit/removal entries |
| `db/batch.py` | Batch wearer history |
| `db/durations.py` | Load timing history |
| `db/config.py` | `shortage_quick_amounts`, censor words, off-schedule, audit photos |
| `db/migrate.py` | One-shot JSON → Postgres import |
| `docker-compose.postgres.yml` | PostgreSQL 16 service overlay |

---

## Step 1 — Add `psycopg2` to requirements

```
psycopg2-binary>=2.9
```

---

## Step 2 — Environment variables

Add to your `.env` (never commit the password):

```dotenv
POSTGRES_USER=truckapp
POSTGRES_PASSWORD=a_strong_random_password_here
POSTGRES_DB=truckapp

TRUCKAPP_PG_HOST=postgres        # Docker service name; use 'localhost' for local dev
TRUCKAPP_PG_PORT=5432
TRUCKAPP_PG_DBNAME=truckapp
TRUCKAPP_PG_USER=truckapp
TRUCKAPP_PG_PASSWORD=a_strong_random_password_here
TRUCKAPP_PG_SSLMODE=disable      # 'require' if connecting over the network
```

---

## Step 3 — Start Postgres + migrate existing data

```powershell
# Apply schema + start DB
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d postgres

# Dry-run migration (preview only)
python -m db.migrate --dry-run

# Full migration
python -m db.migrate
```

The migration is **idempotent** — safe to re-run.

---

## Step 4 — Wire DB calls into `app_unloadv1.7.py`

Add this block near the top of the app, after the imports, using
`@st.cache_resource` so the pool is created once per server process:

```python
import streamlit as st
from db.connection import init_pool

@st.cache_resource
def _ensure_db_pool():
    return init_pool()

_ensure_db_pool()
```

Then replace each flat-file function with its DB equivalent.

---

## Function replacement map

### State (`.truck_state.json`)

| Current function | DB replacement |
|-----------------|---------------|
| `load_state()` | `from db.state import load_state_pg; load_state_pg(run_date_key)` |
| `save_state()` | `from db.state import save_state_pg; save_state_pg(run_date_key, _serialize_state())` |
| `archive_current_state(run_date_key)` | `from db.state import archive_state_pg` |
| `_load_archived_state_for_run_date(key)` | `from db.state import load_archived_state_pg` |
| `_available_state_history_run_dates()` | `from db.state import list_archived_run_dates_pg` |

### Fleet (`truck_fleet.json`)

| Current function | DB replacement |
|-----------------|---------------|
| `load_fleet_file()` | `from db.fleet import load_fleet_pg` |
| `save_fleet_file(fleet)` | `from db.fleet import save_fleet_pg` |
| `load_truck_types()` | `from db.fleet import load_truck_types_pg` |
| `save_truck_types(types)` | `from db.fleet import save_truck_types_pg` |

### Auth (`auth_users.json`, `auth_user_requests.json`, `.truck_sessions.json`)

| Current function | DB replacement |
|-----------------|---------------|
| `_load_auth_users()` | `from db.auth import load_auth_users_pg` |
| `_save_auth_users(users)` | `from db.auth import save_auth_users_pg` |
| `_load_auth_requests()` | `from db.auth import load_auth_requests_pg` |
| `_save_auth_requests(reqs)` | `from db.auth import save_auth_requests_pg` |
| `_load_sessions()` | `from db.auth import load_sessions_pg` |
| `_save_sessions(sessions)` | *(no longer needed — use atomic helpers)* |
| `_write_auth_session(username, role)` | `from db.auth import write_auth_session_pg` |
| `_restore_from_session_store(meta)` | use `resolve_session_pg(session_id)` then set `st.session_state` |
| `_prune_sessions(...)` | `from db.auth import prune_sessions_pg` |

### Chat (`communications_chat.json`)

| Current function | DB replacement |
|-----------------|---------------|
| `_load_communications_messages()` | `from db.communications import load_messages_pg` |
| `_save_communications_messages(msgs)` | *(replaced by atomic append/delete)* |
| `_append_communications_message(ch, user, msg)` | `from db.communications import append_message_pg` |
| `_delete_communications_message(id, ...)` | `from db.communications import delete_message_pg` |
| `_prune_communications_messages_by_age(days)` | `from db.communications import prune_messages_by_age_pg` |
| `_keep_latest_communications_messages(n)` | `from db.communications import keep_latest_messages_pg` |
| `_clear_communications_messages()` | `from db.communications import clear_all_messages_pg` |
| `_latest_communications_message_ts(...)` | `from db.communications import latest_message_ts_pg` |

### Audit history (`audit_requests.json`)

| Current function | DB replacement |
|-----------------|---------------|
| `_load_audit_history()` | `from db.audit import load_audit_entries_pg` |
| `_save_audit_history(entries)` | `from db.audit import save_audit_entries_pg` |
| `_append_audit_history_entry(...)` | build the entry dict, then `from db.audit import append_audit_entry_pg` |
| `_delete_audit_history_entry(id)` | `from db.audit import delete_audit_entry_pg` |
| `_mark_audit_warning_applied(id)` | `from db.audit import mark_audit_warning_applied_pg` |

### Batch history (`batch_history.json`)

| Current function | DB replacement |
|-----------------|---------------|
| `_load_batch_history()` | `from db.batch import load_batch_history_pg` |
| `_save_batch_history(entries)` | `from db.batch import save_batch_history_pg` |
| `_append_batch_history_entry(...)` | build entry dict, then `from db.batch import append_batch_entry_pg` |

### Load durations (`load_durations.json`)

| Current function | DB replacement |
|-----------------|---------------|
| `load_duration_history()` | `from db.durations import load_duration_history_pg` |
| `append_load_duration(truck, seconds)` | build record dict, then `from db.durations import append_load_duration_pg` |
| `remove_abnormal_loadtimes(min, max)` | `from db.durations import remove_abnormal_loadtimes_pg` |

### Config files

| Current function | DB replacement |
|-----------------|---------------|
| `load_quick_amounts()` | `from db.config import load_quick_amounts_pg` |
| `load_chat_censor_words()` | `from db.config import load_censor_words_pg` |
| `_save_chat_censor_words(words)` | `from db.config import save_censor_words_pg` |
| `load_off_schedule_defaults()` | `from db.config import load_off_schedule_defaults_pg` |
| `save_off_schedule_defaults(schedule)` | `from db.config import save_off_schedule_defaults_pg` |
| `_load_audit_photo_manifest(key)` | `from db.config import load_audit_photos_pg` |
| `_save_audit_photo_manifest(entries, key)` | `from db.config import append_audit_photo_pg` (per-entry) |

---

## Caching pattern (replaces mtime-based file cache)

The existing `_load_xxx_cache` pattern in session_state tracks file mtime.
With Postgres, replace it with `@st.cache_data(ttl=...)`:

```python
import streamlit as st
from db.audit import load_audit_entries_pg

@st.cache_data(ttl=5)          # stale after 5 seconds
def _cached_audit_entries():
    return load_audit_entries_pg()
```

Use `st.cache_data.clear()` or targeted key invalidation after any write.

---

## Streamlit vulnerability notes addressed

| Issue | Fix |
|-------|-----|
| Race condition on concurrent JSON writes | Postgres transactions with row-level locking |
| Multiple browser tabs/devices overwriting each other's state | `ON CONFLICT DO UPDATE` — last writer wins, no corruption |
| Session tokens in plaintext `.truck_sessions.json` | `auth_sessions` table with expiry index; never served over HTTP |
| Passwords readable in `auth_users.json` | Already bcrypt-hashed; `password_hash` column name makes intent explicit |
| mtime cache invalidation fails on NAS volume mounts | Replaced with `@st.cache_data(ttl=...)` — no filesystem dependency |

---

## TrueNAS SCALE deployment notes

1. Create a dataset: `tank/appdata/truckapp-postgres`
2. Set `driver_opts` in `docker-compose.postgres.yml` to bind-mount that dataset.
3. The `postgres:16-alpine` image runs as UID 999; set dataset ownership accordingly:
   ```
   chown -R 999:999 /mnt/tank/appdata/truckapp-postgres
   ```
4. Add `COMPOSE_FILE=docker-compose.yml:docker-compose.postgres.yml` to `.env` so
   `docker compose up` picks up both files automatically.
