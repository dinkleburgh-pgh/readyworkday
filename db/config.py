"""
db/config.py
PostgreSQL replacements for:
  - load_quick_amounts()        → shortage_quick_amounts key
  - load_chat_censor_words()    → censor_words key
  - _save_chat_censor_words()
  - load_off_schedule_defaults() → off_schedule_defaults key
  - save_off_schedule_defaults()
  - Audit photo manifest         → audit_photos table (helpers here for
                                   schema consistency with audit.py)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from db.connection import get_conn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Generic config key helpers
# ---------------------------------------------------------------------------

def get_config_pg(config_key: str, default: Any = None) -> Any:
    """Retrieve a config value by key.  Returns *default* if absent."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT value FROM config WHERE key = %s",
                (config_key,),
            )
            row = cur.fetchone()
    if row is None:
        return default
    val = row[0]
    # psycopg2 returns JSONB as Python object directly; handle string fallback.
    if isinstance(val, str):
        try:
            val = json.loads(val)
        except Exception:
            pass
    return val


def set_config_pg(config_key: str, value: Any) -> None:
    """Upsert a config key with a JSON-serialisable value."""
    payload = json.dumps(value, ensure_ascii=False, default=str)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO config (key, value, updated_at)
                VALUES (%s, %s::jsonb, NOW())
                ON CONFLICT (key) DO UPDATE
                    SET value      = EXCLUDED.value,
                        updated_at = NOW()
                """,
                (config_key, payload),
            )


# ---------------------------------------------------------------------------
# Shortage quick amounts
# ---------------------------------------------------------------------------

def load_quick_amounts_pg() -> dict:
    return get_config_pg("shortage_quick_amounts", {})


def save_quick_amounts_pg(amounts: dict) -> None:
    set_config_pg("shortage_quick_amounts", amounts)


# ---------------------------------------------------------------------------
# Chat censor words
# ---------------------------------------------------------------------------

def load_censor_words_pg() -> set[str]:
    raw = get_config_pg("censor_words", [])
    if isinstance(raw, list):
        return {str(w).strip().lower() for w in raw if str(w).strip()}
    return set()


def save_censor_words_pg(words) -> bool:
    try:
        word_list = sorted(
            {str(w).strip().lower() for w in (words or []) if str(w).strip()}
        )
        set_config_pg("censor_words", word_list)
        return True
    except Exception:
        logger.exception("save_censor_words_pg failed")
        return False


# ---------------------------------------------------------------------------
# Off-schedule defaults
# ---------------------------------------------------------------------------

def load_off_schedule_defaults_pg() -> dict[int, list[int]]:
    raw = get_config_pg("off_schedule_defaults", {})
    if not isinstance(raw, dict):
        return {}
    result: dict[int, list[int]] = {}
    for day_key, trucks_raw in raw.items():
        try:
            day_num = int(day_key)
        except Exception:
            continue
        trucks = []
        if isinstance(trucks_raw, list):
            for t in trucks_raw:
                try:
                    trucks.append(int(t))
                except Exception:
                    pass
        result[day_num] = trucks
    return result


def save_off_schedule_defaults_pg(schedule) -> None:
    normalized = {
        str(day): list(trucks)
        for day, trucks in (schedule or {}).items()
    }
    set_config_pg("off_schedule_defaults", normalized)


# ---------------------------------------------------------------------------
# Role workflow settings
# ---------------------------------------------------------------------------

def load_role_workflow_settings_pg() -> dict:
    return get_config_pg("role_workflow_settings", {})


def save_role_workflow_settings_pg(settings: dict) -> None:
    set_config_pg("role_workflow_settings", settings)


# ---------------------------------------------------------------------------
# Audit photo manifest  (metadata layer; files stay on filesystem)
# ---------------------------------------------------------------------------

def load_audit_photos_pg(
    run_date: str | None = None,
    truck: int | None = None,
    limit: int = 500,
) -> list[dict]:
    clauses: list[str] = []
    params: list = []
    if run_date:
        clauses.append("run_date = %s"); params.append(run_date)
    if truck is not None:
        clauses.append("truck = %s"); params.append(int(truck))
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT entry_id, ts, run_date, photo_day, truck, route,
               photo_day_num, loaded_day_num, loaded_previous_date,
               loaded_previous_context, actor, source, note,
               relative_path, original_bytes, compressed_bytes,
               jpeg_quality, max_dimension
        FROM audit_photos
        {where}
        ORDER BY ts DESC
        LIMIT %s
    """
    params.append(limit)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return [
        {
            "entry_id": r[0],
            "ts": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
            "run_date": r[2],
            "photo_day": r[3],
            "truck": r[4],
            "route": r[5],
            "photo_day_num": r[6],
            "loaded_day_num": r[7],
            "loaded_previous_date": r[8],
            "loaded_previous_context": r[9],
            "actor": r[10],
            "source": r[11],
            "note": r[12],
            "relative_path": r[13],
            "original_bytes": r[14],
            "compressed_bytes": r[15],
            "jpeg_quality": r[16],
            "max_dimension": r[17],
        }
        for r in rows
    ]


def append_audit_photo_pg(entry: dict) -> bool:
    """Insert an audit photo manifest entry."""
    from datetime import datetime as _dt
    ts_raw = entry.get("ts")
    try:
        ts_val = _dt.fromisoformat(str(ts_raw)) if ts_raw else _dt.now()
    except Exception:
        ts_val = _dt.now()
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_photos
                        (entry_id, ts, run_date, photo_day, truck, route,
                         photo_day_num, loaded_day_num, loaded_previous_date,
                         loaded_previous_context, actor, source, note,
                         relative_path, original_bytes, compressed_bytes,
                         jpeg_quality, max_dimension)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (entry_id) DO NOTHING
                    """,
                    (
                        str(entry.get("entry_id") or ""),
                        ts_val,
                        str(entry.get("run_date") or ""),
                        str(entry.get("photo_day") or ""),
                        int(entry.get("truck") or 0),
                        int(entry.get("route") or 0),
                        entry.get("photo_day_num"),
                        entry.get("loaded_day_num"),
                        str(entry.get("loaded_previous_date") or ""),
                        str(entry.get("loaded_previous_context") or ""),
                        str(entry.get("actor") or ""),
                        str(entry.get("source") or "upload"),
                        str(entry.get("note") or ""),
                        str(entry.get("relative_path") or ""),
                        entry.get("original_bytes"),
                        entry.get("compressed_bytes"),
                        entry.get("jpeg_quality"),
                        entry.get("max_dimension"),
                    ),
                )
        return True
    except Exception:
        logger.exception("append_audit_photo_pg failed")
        return False


def delete_audit_photos_pg(entry_ids: list[str]) -> int:
    """Hard-delete audit photo rows by entry_id list.  Returns deleted count."""
    ids = [str(x) for x in (entry_ids or []) if str(x).strip()]
    if not ids:
        return 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM audit_photos WHERE entry_id = ANY(%s)", (ids,)
            )
            return cur.rowcount


def list_audit_photo_run_dates_pg() -> list[str]:
    """Return all distinct run_date values that have audit photo entries."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT run_date FROM audit_photos ORDER BY run_date DESC"
            )
            rows = cur.fetchall()
    return [r[0] for r in rows]
