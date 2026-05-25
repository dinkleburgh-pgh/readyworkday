"""
db/batch.py
PostgreSQL replacements for _load_batch_history() / _save_batch_history() /
_append_batch_history_entry().
"""

from __future__ import annotations

import logging
from datetime import datetime

from db.connection import get_conn

logger = logging.getLogger(__name__)


def load_batch_history_pg(
    run_date: str | None = None,
    days_back: int | None = None,
) -> list[dict]:
    """Return batch history rows as a list of dicts."""
    clauses: list[str] = []
    params: list = []
    if run_date:
        clauses.append("run_date = %s")
        params.append(run_date)
    if days_back is not None:
        clauses.append("ts >= NOW() - (%s || ' days')::interval")
        params.append(str(int(days_back)))

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT entry_id, ts, run_date, load_day_num, truck, route, batch_id,
               wearers, action
        FROM batch_history
        {where}
        ORDER BY ts
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    return [
        {
            "entry_id": r[0],
            "ts": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
            "run_date": r[2],
            "load_day_num": r[3],
            "truck": r[4],
            "route": r[5],
            "batch_id": r[6],
            "wearers": r[7],
            "action": r[8] or "assign",
        }
        for r in rows
    ]


def append_batch_entry_pg(entry: dict) -> bool:
    """Insert a single batch history entry dict.  Returns True on success."""
    try:
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

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO batch_history
                        (entry_id, ts, run_date, load_day_num, truck, route,
                         batch_id, wearers, action)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (entry_id) DO NOTHING
                    """,
                    (
                        str(entry.get("entry_id") or ""),
                        ts_val,
                        str(entry.get("run_date") or ""),
                        entry.get("load_day_num"),
                        int(entry.get("truck") or 0),
                        int(entry.get("route") or 0),
                        entry.get("batch_id"),
                        int(entry.get("wearers") or 0),
                        str(entry.get("action") or "assign"),
                    ),
                )
        return True
    except Exception:
        logger.exception("append_batch_entry_pg failed")
        return False


def save_batch_history_pg(entries: list[dict]) -> bool:
    """Bulk upsert (used when the app rewrites the full list)."""
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
                        INSERT INTO batch_history
                            (entry_id, ts, run_date, load_day_num, truck, route,
                             batch_id, wearers, action)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (entry_id) DO NOTHING
                        """,
                        (
                            str(entry.get("entry_id") or ""),
                            ts_val,
                            str(entry.get("run_date") or ""),
                            entry.get("load_day_num"),
                            int(entry.get("truck") or 0),
                            int(entry.get("route") or 0),
                            entry.get("batch_id"),
                            int(entry.get("wearers") or 0),
                            str(entry.get("action") or "assign"),
                        ),
                    )
        return True
    except Exception:
        logger.exception("save_batch_history_pg failed")
        return False
