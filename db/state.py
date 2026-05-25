"""
db/state.py
PostgreSQL replacements for load_state() / save_state() / archive / history.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from db.connection import get_conn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_for_pg(obj: Any) -> Any:
    """Recursively convert Python types that JSON/JSONB can't handle natively."""
    if isinstance(obj, set):
        return sorted(list(obj))
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _serialize_for_pg(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_pg(i) for i in obj]
    return obj


# ---------------------------------------------------------------------------
# Live state
# ---------------------------------------------------------------------------

def load_state_pg(run_date_key: str) -> dict:
    """
    Load the serialised state blob for *run_date_key* (e.g. "2026-05-24").
    Returns an empty dict when no row exists yet.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT payload FROM app_state WHERE run_date_key = %s",
                (run_date_key,),
            )
            row = cur.fetchone()
    if row is None:
        return {}
    payload = row[0]
    # psycopg2 returns JSONB as a Python dict already; guard both cases.
    if isinstance(payload, str):
        payload = json.loads(payload)
    return payload if isinstance(payload, dict) else {}


def save_state_pg(run_date_key: str, state_dict: dict) -> None:
    """
    Upsert the serialised state blob for *run_date_key*.
    Accepts the raw session_state dict; handles sets / dates transparently.
    """
    payload = _serialize_for_pg(state_dict)
    payload_json = json.dumps(payload, ensure_ascii=False, default=str)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app_state (run_date_key, payload, updated_at)
                VALUES (%s, %s::jsonb, NOW())
                ON CONFLICT (run_date_key) DO UPDATE
                    SET payload    = EXCLUDED.payload,
                        updated_at = NOW()
                """,
                (run_date_key, payload_json),
            )


# ---------------------------------------------------------------------------
# State history / archive
# ---------------------------------------------------------------------------

def archive_state_pg(run_date_key: str, payload: dict) -> None:
    """
    Write a snapshot into state_history.  Uses INSERT … ON CONFLICT DO UPDATE
    so re-archiving the same day overwrites the previous snapshot.
    """
    serialized = json.dumps(_serialize_for_pg(payload), ensure_ascii=False, default=str)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO state_history (run_date_key, payload, archived_at)
                VALUES (%s, %s::jsonb, NOW())
                ON CONFLICT (run_date_key) DO UPDATE
                    SET payload     = EXCLUDED.payload,
                        archived_at = NOW()
                """,
                (run_date_key, serialized),
            )


def load_archived_state_pg(run_date_key: str) -> dict | None:
    """Return the archived state for a given run-date, or None if absent."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT payload FROM state_history WHERE run_date_key = %s",
                (run_date_key,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    payload = row[0]
    if isinstance(payload, str):
        payload = json.loads(payload)
    return payload if isinstance(payload, dict) else {}


def list_archived_run_dates_pg() -> list[str]:
    """Return sorted list of run-date keys that have a history snapshot."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT run_date_key FROM state_history ORDER BY run_date_key DESC"
            )
            rows = cur.fetchall()
    return [r[0] for r in rows]
