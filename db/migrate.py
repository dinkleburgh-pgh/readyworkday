#!/usr/bin/env python3
"""
db/migrate.py  —  One-shot migration from flat JSON files → PostgreSQL.

Usage:
    # Set env vars first (TRUCKAPP_PG_DBNAME, TRUCKAPP_PG_USER, etc.)
    python -m db.migrate

    # Or pass --dry-run to see counts without writing anything
    python -m db.migrate --dry-run

    # Only migrate specific tables
    python -m db.migrate --only state,auth,audit

The script is idempotent: re-running it will not duplicate rows because
all inserts use ON CONFLICT DO NOTHING / DO UPDATE.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime, date
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("truckapp.migrate")

# ---------------------------------------------------------------------------
# Env-driven file paths (same defaults as the main app)
# ---------------------------------------------------------------------------

STATE_FILE           = os.getenv("TRUCKAPP_STATE_FILE",            ".truck_state.json")
FLEET_FILE           = os.getenv("TRUCKAPP_FLEET_FILE",            "truck_fleet.json")
DURATIONS_FILE       = os.getenv("TRUCKAPP_DURATIONS_FILE",        "load_durations.json")
OFF_SCHEDULE_FILE    = os.getenv("TRUCKAPP_OFF_SCHEDULE_DEFAULTS_FILE", "off_schedule_defaults.json")
HISTORY_DIR          = os.getenv("TRUCKAPP_HISTORY_DIR",            "state_history")
AUTH_USERS_FILE      = os.getenv("TRUCKAPP_AUTH_USERS_FILE",        "auth_users.json")
AUTH_REQUESTS_FILE   = os.getenv("TRUCKAPP_AUTH_REQUESTS_FILE",     "auth_user_requests.json")
COMMUNICATIONS_FILE  = os.getenv("TRUCKAPP_COMMUNICATIONS_FILE",    "communications_chat.json")
CHAT_CENSOR_FILE     = "chat_censor_words.json"
AUDIT_HISTORY_FILE   = os.getenv("TRUCKAPP_AUDIT_HISTORY_FILE",    "audit_requests.json")
BATCH_HISTORY_FILE   = os.getenv("TRUCKAPP_BATCH_HISTORY_FILE",    "batch_history.json")
SPARE_HISTORY_FILE   = os.getenv("TRUCKAPP_SPARE_HISTORY_FILE",    "spare_assignment_history.json")
SESSIONS_FILE        = os.getenv("TRUCKAPP_AUTH_SESSION_FILE",      ".truck_sessions.json")
AUDIT_PHOTO_DIR      = os.getenv("TRUCKAPP_AUDIT_PHOTO_ARCHIVE_DIR","audit_photo_archive")
QUICK_AMOUNTS_FILE   = "shortage_quick_amounts.json"

BASE_DIR = Path(os.getcwd())


def _read_json(path: str | Path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Could not read %s: %s", p, exc)
        return default


# ---------------------------------------------------------------------------
# Schema application
# ---------------------------------------------------------------------------

def apply_schema(dry_run: bool) -> None:
    if dry_run:
        logger.info("[DRY RUN] Would apply db/schema.sql")
        return
    schema_path = Path(__file__).parent / "schema.sql"
    if not schema_path.exists():
        logger.error("schema.sql not found at %s", schema_path)
        sys.exit(1)
    sql = schema_path.read_text(encoding="utf-8")
    from db.connection import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
    logger.info("Schema applied (all CREATE TABLE IF NOT EXISTS)")


# ---------------------------------------------------------------------------
# Migration helpers
# ---------------------------------------------------------------------------

def migrate_config(dry_run: bool) -> None:
    """shortage_quick_amounts + censor_words + off_schedule_defaults."""
    from db.config import (
        save_quick_amounts_pg,
        save_censor_words_pg,
        save_off_schedule_defaults_pg,
    )

    qa = _read_json(QUICK_AMOUNTS_FILE, {})
    if qa:
        if dry_run:
            logger.info("[DRY RUN] Would upsert shortage_quick_amounts (%d keys)", len(qa))
        else:
            save_quick_amounts_pg(qa)
            logger.info("Migrated shortage_quick_amounts (%d keys)", len(qa))

    censor_raw = _read_json(CHAT_CENSOR_FILE, {})
    censor_words = []
    if isinstance(censor_raw, dict):
        censor_words = list(censor_raw.get("words") or [])
    elif isinstance(censor_raw, list):
        censor_words = censor_raw
    if censor_words:
        if dry_run:
            logger.info("[DRY RUN] Would upsert %d censor words", len(censor_words))
        else:
            save_censor_words_pg(censor_words)
            logger.info("Migrated %d censor words", len(censor_words))

    off_raw = _read_json(OFF_SCHEDULE_FILE, {})
    if off_raw:
        if dry_run:
            logger.info("[DRY RUN] Would upsert off_schedule_defaults")
        else:
            save_off_schedule_defaults_pg(off_raw)
            logger.info("Migrated off_schedule_defaults")


def migrate_fleet(dry_run: bool) -> None:
    raw = _read_json(FLEET_FILE)
    if raw is None:
        logger.info("No fleet file found, skipping")
        return

    trucks_list: list[int] = []
    truck_types: dict[int, str] = {}

    if isinstance(raw, dict):
        trucks_list = [int(t) for t in (raw.get("trucks") or []) if str(t).isdigit() or isinstance(t, int)]
        for k, v in (raw.get("truck_types") or {}).items():
            try:
                truck_types[int(k)] = str(v)
            except Exception:
                pass
    elif isinstance(raw, list):
        trucks_list = [int(t) for t in raw if isinstance(t, int) or str(t).isdigit()]

    if dry_run:
        logger.info("[DRY RUN] Would upsert %d fleet trucks + %d types", len(trucks_list), len(truck_types))
        return

    from db.fleet import save_fleet_pg, save_truck_types_pg
    if trucks_list:
        save_fleet_pg(trucks_list)
        logger.info("Migrated %d fleet trucks", len(trucks_list))
    if truck_types:
        save_truck_types_pg(truck_types)
        logger.info("Migrated %d truck type overrides", len(truck_types))


def migrate_state(dry_run: bool) -> None:
    """Migrate live state + all history snapshots."""
    from db.state import save_state_pg, archive_state_pg

    # Live state
    state_raw = _read_json(STATE_FILE)
    if state_raw and isinstance(state_raw, dict):
        run_date_key = state_raw.get("run_date_key") or state_raw.get("run_date")
        if not run_date_key:
            today = date.today().isoformat()
            run_date_key = today
        if dry_run:
            logger.info("[DRY RUN] Would upsert live state for run_date_key=%s", run_date_key)
        else:
            save_state_pg(str(run_date_key), state_raw)
            logger.info("Migrated live state (run_date_key=%s)", run_date_key)

    # History snapshots
    history_dir = BASE_DIR / HISTORY_DIR
    count = 0
    if history_dir.is_dir():
        for f in sorted(history_dir.glob("state_*.json")):
            m = re.match(r"(?i)^state_(\d{4}-\d{2}-\d{2})\.json$", f.name)
            if not m:
                continue
            run_date_key = m.group(1)
            payload = _read_json(f)
            if not payload:
                continue
            count += 1
            if not dry_run:
                archive_state_pg(run_date_key, payload)
    if dry_run:
        logger.info("[DRY RUN] Would archive %d state snapshots", count)
    else:
        logger.info("Archived %d state history snapshots", count)


def migrate_auth(dry_run: bool) -> None:
    from db.auth import save_auth_users_pg, save_auth_requests_pg

    # Users
    users_raw = _read_json(AUTH_USERS_FILE)
    if users_raw:
        users_block = users_raw
        if isinstance(users_raw, dict) and isinstance(users_raw.get("users"), dict):
            users_block = users_raw["users"]
        if dry_run:
            logger.info("[DRY RUN] Would upsert %d users", len(users_block) if isinstance(users_block, dict) else 0)
        else:
            save_auth_users_pg(users_block if isinstance(users_block, dict) else {})
            logger.info("Migrated %d users", len(users_block) if isinstance(users_block, dict) else 0)

    # Requests
    requests_raw = _read_json(AUTH_REQUESTS_FILE)
    if requests_raw:
        requests_block = requests_raw
        if isinstance(requests_raw, dict) and isinstance(requests_raw.get("requests"), dict):
            requests_block = requests_raw["requests"]
        if isinstance(requests_block, dict):
            if dry_run:
                logger.info("[DRY RUN] Would upsert %d auth requests", len(requests_block))
            else:
                save_auth_requests_pg(requests_block)
                logger.info("Migrated %d auth requests", len(requests_block))

    # Sessions
    sessions_raw = _read_json(SESSIONS_FILE) or {}
    if sessions_raw:
        import time
        now_ts = time.time()
        valid_sessions = {
            sid: s for sid, s in sessions_raw.items()
            if float(s.get("expires_at") or 0) > now_ts
        }
        if valid_sessions:
            if dry_run:
                logger.info("[DRY RUN] Would import %d non-expired sessions", len(valid_sessions))
            else:
                from db.connection import get_conn
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        for session_id, s in valid_sessions.items():
                            cur.execute(
                                """
                                INSERT INTO auth_sessions
                                    (session_id, username, role, created_at, expires_at)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (session_id) DO NOTHING
                                """,
                                (
                                    session_id,
                                    str(s.get("username") or ""),
                                    str(s.get("role") or ""),
                                    float(s.get("created_at") or now_ts),
                                    float(s.get("expires_at") or now_ts),
                                ),
                            )
                logger.info("Migrated %d active auth sessions", len(valid_sessions))


def migrate_communications(dry_run: bool) -> None:
    raw = _read_json(COMMUNICATIONS_FILE)
    if not raw:
        return
    messages = raw if isinstance(raw, list) else (raw.get("messages") or [])
    if not messages:
        return
    if dry_run:
        logger.info("[DRY RUN] Would insert %d chat messages", len(messages))
        return
    from db.connection import get_conn
    inserted = 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            for idx, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    continue
                try:
                    ts_val = float(msg.get("ts") or 0)
                except Exception:
                    ts_val = 0.0
                msg_id = str(msg.get("id") or f"m{int(ts_val*1000)}-{idx}")
                cur.execute(
                    """
                    INSERT INTO chat_messages (message_id, ts, channel, username, message)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (message_id) DO NOTHING
                    """,
                    (
                        msg_id,
                        ts_val,
                        str(msg.get("channel") or "Team"),
                        str(msg.get("username") or "Unknown"),
                        str(msg.get("message") or "")[:1000],
                    ),
                )
                inserted += 1
    logger.info("Migrated %d chat messages", inserted)


def migrate_audit(dry_run: bool) -> None:
    entries = _read_json(AUDIT_HISTORY_FILE, [])
    if not isinstance(entries, list) or not entries:
        logger.info("No audit history to migrate")
        return
    if dry_run:
        logger.info("[DRY RUN] Would insert %d audit entries", len(entries))
        return
    from db.audit import save_audit_entries_pg
    save_audit_entries_pg(entries)
    logger.info("Migrated %d audit entries", len(entries))


def migrate_batch(dry_run: bool) -> None:
    entries = _read_json(BATCH_HISTORY_FILE, [])
    if not isinstance(entries, list) or not entries:
        logger.info("No batch history to migrate")
        return
    if dry_run:
        logger.info("[DRY RUN] Would insert %d batch history entries", len(entries))
        return
    from db.batch import save_batch_history_pg
    save_batch_history_pg(entries)
    logger.info("Migrated %d batch history entries", len(entries))


def migrate_durations(dry_run: bool) -> None:
    records = _read_json(DURATIONS_FILE, [])
    if not isinstance(records, list) or not records:
        logger.info("No load duration history to migrate")
        return
    if dry_run:
        logger.info("[DRY RUN] Would insert %d duration records", len(records))
        return
    from db.durations import append_load_duration_pg
    count = 0
    for record in records:
        if isinstance(record, dict):
            append_load_duration_pg(record)
            count += 1
    logger.info("Migrated %d load duration records", count)


def migrate_audit_photos(dry_run: bool) -> None:
    """Scan audit_photo_archive directory and migrate all manifests."""
    root = BASE_DIR / AUDIT_PHOTO_DIR
    if not root.is_dir():
        logger.info("No audit photo archive directory found, skipping")
        return

    total = 0
    for manifest_path in root.rglob("audit_photo_manifest.json"):
        entries = _read_json(manifest_path, [])
        if not isinstance(entries, list):
            continue
        if dry_run:
            total += len(entries)
            continue
        from db.config import append_audit_photo_pg
        for entry in entries:
            if isinstance(entry, dict):
                append_audit_photo_pg(entry)
                total += 1

    if dry_run:
        logger.info("[DRY RUN] Would insert ~%d audit photo entries", total)
    else:
        logger.info("Migrated %d audit photo manifest entries", total)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

ALL_STEPS = ["schema", "config", "fleet", "state", "auth", "communications",
             "audit", "batch", "durations", "photos"]

STEP_FUNCS = {
    "config":         migrate_config,
    "fleet":          migrate_fleet,
    "state":          migrate_state,
    "auth":           migrate_auth,
    "communications": migrate_communications,
    "audit":          migrate_audit,
    "batch":          migrate_batch,
    "durations":      migrate_durations,
    "photos":         migrate_audit_photos,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate TruckApp JSON files → PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument(
        "--only",
        help=f"Comma-separated subset of steps: {','.join(ALL_STEPS)}",
    )
    args = parser.parse_args()

    dry_run: bool = args.dry_run
    if dry_run:
        logger.info("=== DRY RUN — no data will be written ===")

    steps = ALL_STEPS
    if args.only:
        steps = [s.strip() for s in args.only.split(",") if s.strip()]
        invalid = set(steps) - set(ALL_STEPS)
        if invalid:
            logger.error("Unknown steps: %s", invalid)
            sys.exit(1)

    if "schema" in steps:
        apply_schema(dry_run)

    for step in steps:
        if step == "schema":
            continue
        func = STEP_FUNCS.get(step)
        if func:
            logger.info("--- Migrating: %s ---", step)
            func(dry_run)

    logger.info("Migration complete%s.", " (dry run)" if dry_run else "")


if __name__ == "__main__":
    main()
