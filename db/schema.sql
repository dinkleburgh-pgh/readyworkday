-- =============================================================================
-- TruckApp PostgreSQL Schema
-- Apply with: psql -U <user> -d <dbname> -f db/schema.sql
-- All tables use IF NOT EXISTS so this script is safe to re-run.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Generic config key-value store
-- Holds: shortage_quick_amounts, censor_words, off_schedule_defaults,
--        role_workflow_settings
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS config (
    key        TEXT        PRIMARY KEY,
    value      JSONB       NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- App state (single mutable row per run-date; replaces .truck_state.json)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_state (
    run_date_key TEXT        PRIMARY KEY,           -- e.g. "2026-05-24"
    payload      JSONB       NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Daily state archive (replaces state_history/state_YYYY-MM-DD.json)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS state_history (
    run_date_key TEXT        PRIMARY KEY,
    payload      JSONB       NOT NULL,
    archived_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Fleet trucks (replaces truck_fleet.json)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fleet_trucks (
    truck_num   INTEGER     PRIMARY KEY,
    truck_type  TEXT        NOT NULL DEFAULT 'Uniform',  -- Uniform | Dust | Spare
    is_spare    BOOLEAN     NOT NULL DEFAULT FALSE,
    enabled     BOOLEAN     NOT NULL DEFAULT TRUE,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Auth users (replaces auth_users.json)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    username      TEXT        PRIMARY KEY,               -- lowercase canonical
    display_name  TEXT        NOT NULL,
    password_hash TEXT        NOT NULL,                  -- bcrypt hash
    role          TEXT        NOT NULL DEFAULT 'guest',
    enabled       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Auth access requests (replaces auth_user_requests.json)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_requests (
    request_id    TEXT        PRIMARY KEY,
    username      TEXT        NOT NULL,
    display_name  TEXT,
    requested_role TEXT,
    status        TEXT        NOT NULL DEFAULT 'pending',  -- pending | approved | denied
    note          TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at   TIMESTAMPTZ,
    resolved_by   TEXT
);
CREATE INDEX IF NOT EXISTS idx_user_requests_status ON user_requests(status);

-- ---------------------------------------------------------------------------
-- Server-side auth sessions (replaces .truck_sessions.json)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_sessions (
    session_id TEXT           PRIMARY KEY,
    username   TEXT           NOT NULL,
    role       TEXT           NOT NULL,
    created_at DOUBLE PRECISION NOT NULL,
    expires_at DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires ON auth_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_username ON auth_sessions(username);

-- ---------------------------------------------------------------------------
-- Chat messages (replaces communications_chat.json)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_messages (
    message_id TEXT           PRIMARY KEY,
    ts         DOUBLE PRECISION NOT NULL,
    channel    TEXT           NOT NULL DEFAULT 'Team',
    username   TEXT           NOT NULL,
    message    TEXT           NOT NULL,
    deleted_at TIMESTAMPTZ                               -- soft-delete support
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_ts      ON chat_messages(ts);
CREATE INDEX IF NOT EXISTS idx_chat_messages_channel ON chat_messages(channel);

-- ---------------------------------------------------------------------------
-- Audit / removal entries (replaces audit_requests.json)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_entries (
    entry_id             TEXT        PRIMARY KEY,
    ts                   TIMESTAMPTZ NOT NULL,
    run_date             TEXT        NOT NULL,
    load_day_num         INTEGER,
    applied_day_num      INTEGER,
    loaded_day_num       INTEGER,
    truck                INTEGER     NOT NULL,
    route                INTEGER     NOT NULL,
    item                 TEXT        NOT NULL,
    qty                  INTEGER     NOT NULL DEFAULT 1,
    note                 TEXT,
    actor                TEXT,
    source               TEXT        DEFAULT 'workflow',
    warn_next_load       BOOLEAN     DEFAULT FALSE,
    warn_applied_run_date TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_entries_run_date ON audit_entries(run_date);
CREATE INDEX IF NOT EXISTS idx_audit_entries_truck    ON audit_entries(truck);
CREATE INDEX IF NOT EXISTS idx_audit_entries_ts       ON audit_entries(ts);

-- ---------------------------------------------------------------------------
-- Batch wearer history (replaces batch_history.json)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS batch_history (
    entry_id     TEXT        PRIMARY KEY,
    ts           TIMESTAMPTZ NOT NULL,
    run_date     TEXT        NOT NULL,
    load_day_num INTEGER,
    truck        INTEGER     NOT NULL,
    route        INTEGER     NOT NULL,
    batch_id     INTEGER,
    wearers      INTEGER     NOT NULL DEFAULT 0,
    action       TEXT        DEFAULT 'assign'
);
CREATE INDEX IF NOT EXISTS idx_batch_history_run_date ON batch_history(run_date);
CREATE INDEX IF NOT EXISTS idx_batch_history_truck    ON batch_history(truck);

-- ---------------------------------------------------------------------------
-- Spare assignment history (replaces spare_assignment_history.json)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS spare_history (
    entry_id      TEXT        PRIMARY KEY,
    ts            TIMESTAMPTZ NOT NULL,
    run_date      TEXT        NOT NULL,
    spare_truck   INTEGER     NOT NULL,
    covered_route INTEGER,
    action        TEXT,
    actor         TEXT,
    note          TEXT
);
CREATE INDEX IF NOT EXISTS idx_spare_history_run_date ON spare_history(run_date);

-- ---------------------------------------------------------------------------
-- Load duration history (replaces load_durations.json)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS load_durations (
    id           SERIAL      PRIMARY KEY,
    ts           DOUBLE PRECISION NOT NULL,
    ts_iso       TIMESTAMPTZ,
    run_date     TEXT,
    load_date    TEXT,
    truck        INTEGER     NOT NULL,
    route        INTEGER     NOT NULL,
    load_day_num INTEGER,
    seconds      INTEGER     NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_load_durations_run_date ON load_durations(run_date);
CREATE INDEX IF NOT EXISTS idx_load_durations_truck    ON load_durations(truck);
CREATE INDEX IF NOT EXISTS idx_load_durations_ts       ON load_durations(ts);

-- ---------------------------------------------------------------------------
-- Audit photo manifest (replaces per-day audit_photo_manifest.json files)
-- Physical image files remain on the filesystem / volume mount.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_photos (
    entry_id              TEXT        PRIMARY KEY,
    ts                    TIMESTAMPTZ NOT NULL,
    run_date              TEXT        NOT NULL,
    photo_day             TEXT,
    truck                 INTEGER     NOT NULL,
    route                 INTEGER     NOT NULL,
    photo_day_num         INTEGER,
    loaded_day_num        INTEGER,
    loaded_previous_date  TEXT,
    loaded_previous_context TEXT,
    actor                 TEXT,
    source                TEXT,
    note                  TEXT,
    relative_path         TEXT        NOT NULL,
    original_bytes        INTEGER,
    compressed_bytes      INTEGER,
    jpeg_quality          INTEGER,
    max_dimension         INTEGER
);
CREATE INDEX IF NOT EXISTS idx_audit_photos_run_date ON audit_photos(run_date);
CREATE INDEX IF NOT EXISTS idx_audit_photos_truck    ON audit_photos(truck);
