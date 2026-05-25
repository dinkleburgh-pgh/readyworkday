"""
db/audit.py
PostgreSQL replacements for _load_audit_history() / _save_audit_history() /
_append_audit_history_entry() / _delete_audit_history_entry() /
_mark_audit_warning_applied().
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from db.connection import get_conn

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_audit_entries_pg(
    run_date: str | None = None,
    truck: int | None = None,
    days_back: int | None = None,
) -> list[dict]:
    """
    Fetch audit entries.  All filter args are optional; omitting all returns
    the full history (up to 10 000 rows).

    Returns rows in the same dict shape used by the app.
    """
    clauses: list[str] = []
    params: list[Any] = []

    if run_date:
        clauses.append("run_date = %s")
        params.append(run_date)
    if truck is not None:
        clauses.append("truck = %s")
        params.append(int(truck))
    if days_back is not None:
        clauses.append(
            "ts >= NOW() - (%s || ' days')::interval"
        )
        params.append(str(int(days_back)))

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT entry_id, ts, run_date, load_day_num, applied_day_num,
               loaded_day_num, truck, route, item, qty, note, actor, source,
               warn_next_load, warn_applied_run_date
        FROM audit_entries
        {where}
        ORDER BY ts
        LIMIT 10000
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    out: list[dict] = []
    for r in rows:
        out.append({
            "entry_id": r[0],
            "ts": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
            "run_date": r[2],
            "load_day_num": r[3],
            "applied_day_num": r[4],
            "loaded_day_num": r[5],
            "truck": r[6],
            "route": r[7],
            "item": r[8],
            "qty": r[9],
            "note": r[10] or "",
            "actor": r[11] or "",
            "source": r[12] or "workflow",
            "warn_next_load": bool(r[13]),
            "warn_applied_run_date": r[14],
        })
    return out


# ---------------------------------------------------------------------------
# Append / upsert single entry
# ---------------------------------------------------------------------------

def append_audit_entry_pg(entry: dict) -> bool:
    """Insert a single audit entry dict.  Returns True on success."""
    try:
        ts_raw = entry.get("ts")
        ts_val: datetime
        if isinstance(ts_raw, str):
            ts_val = datetime.fromisoformat(ts_raw)
        elif isinstance(ts_raw, datetime):
            ts_val = ts_raw
        else:
            ts_val = datetime.now()

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_entries
                        (entry_id, ts, run_date, load_day_num, applied_day_num,
                         loaded_day_num, truck, route, item, qty, note, actor,
                         source, warn_next_load, warn_applied_run_date)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (entry_id) DO NOTHING
                    """,
                    (
                        str(entry.get("entry_id") or ""),
                        ts_val,
                        str(entry.get("run_date") or ""),
                        entry.get("load_day_num"),
                        entry.get("applied_day_num"),
                        entry.get("loaded_day_num"),
                        int(entry.get("truck") or 0),
                        int(entry.get("route") or 0),
                        str(entry.get("item") or ""),
                        int(entry.get("qty") or 1),
                        str(entry.get("note") or ""),
                        str(entry.get("actor") or ""),
                        str(entry.get("source") or "workflow"),
                        bool(entry.get("warn_next_load", False)),
                        entry.get("warn_applied_run_date"),
                    ),
                )
        return True
    except Exception:
        logger.exception("append_audit_entry_pg failed for entry_id=%s", entry.get("entry_id"))
        return False


# ---------------------------------------------------------------------------
# Bulk replace (used when the app rewrites the whole list)
# ---------------------------------------------------------------------------

def save_audit_entries_pg(entries: list[dict]) -> bool:
    """
    Bulk upsert a list of audit entries.  Used when the app calls
    _save_audit_history() with a mutated full list (e.g. after deleting).
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                for entry in entries:
                    ts_raw = entry.get("ts")
                    if isinstance(ts_raw, str):
                        try:
                            ts_val = datetime.fromisoformat(ts_raw)
                        except Exception:
                            ts_val = datetime.now()
                    elif isinstance(ts_raw, datetime):
                        ts_val = ts_raw
                    else:
                        ts_val = datetime.now()

                    cur.execute(
                        """
                        INSERT INTO audit_entries
                            (entry_id, ts, run_date, load_day_num, applied_day_num,
                             loaded_day_num, truck, route, item, qty, note, actor,
                             source, warn_next_load, warn_applied_run_date)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (entry_id) DO UPDATE
                            SET warn_next_load        = EXCLUDED.warn_next_load,
                                warn_applied_run_date = EXCLUDED.warn_applied_run_date,
                                note                  = EXCLUDED.note
                        """,
                        (
                            str(entry.get("entry_id") or ""),
                            ts_val,
                            str(entry.get("run_date") or ""),
                            entry.get("load_day_num"),
                            entry.get("applied_day_num"),
                            entry.get("loaded_day_num"),
                            int(entry.get("truck") or 0),
                            int(entry.get("route") or 0),
                            str(entry.get("item") or ""),
                            int(entry.get("qty") or 1),
                            str(entry.get("note") or ""),
                            str(entry.get("actor") or ""),
                            str(entry.get("source") or "workflow"),
                            bool(entry.get("warn_next_load", False)),
                            entry.get("warn_applied_run_date"),
                        ),
                    )
        return True
    except Exception:
        logger.exception("save_audit_entries_pg failed")
        return False


# ---------------------------------------------------------------------------
# Delete / update
# ---------------------------------------------------------------------------

def delete_audit_entry_pg(entry_id: str) -> bool:
    """Hard-delete a single audit entry.  Returns True if a row was removed."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM audit_entries WHERE entry_id = %s", (str(entry_id),)
            )
            return cur.rowcount > 0


def mark_audit_warning_applied_pg(entry_id: str, run_date: str) -> bool:
    """Set warn_applied_run_date on an entry.  Returns True on success."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE audit_entries "
                "SET warn_applied_run_date = %s "
                "WHERE entry_id = %s",
                (str(run_date), str(entry_id)),
            )
            return cur.rowcount > 0
