"""
db/durations.py
PostgreSQL replacements for load_duration_history() /
append_load_duration() / remove_abnormal_loadtimes().
"""

from __future__ import annotations

import logging
from datetime import datetime

from db.connection import get_conn

logger = logging.getLogger(__name__)


def load_duration_history_pg(
    days_back: int | None = None,
    max_rows: int = 2000,
) -> list[dict]:
    """Return load duration records (up to *max_rows*), newest last."""
    params: list = []
    where = ""
    if days_back is not None:
        where = "WHERE ts >= EXTRACT(EPOCH FROM NOW() - (%s || ' days')::interval)"
        params.append(str(int(days_back)))

    sql = f"""
        SELECT id, ts, ts_iso, run_date, load_date, truck, route, load_day_num, seconds
        FROM load_durations
        {where}
        ORDER BY ts DESC
        LIMIT %s
    """
    params.append(max_rows)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    # Return in ascending ts order (oldest first), matching JSON file convention.
    out = []
    for r in reversed(rows):
        out.append({
            "ts": float(r[1]),
            "ts_iso": (
                r[2].isoformat()
                if hasattr(r[2], "isoformat") and r[2]
                else (str(r[1]) if r[1] else "")
            ),
            "run_date": r[3] or "",
            "load_date": r[4] or "",
            "truck": r[5],
            "route": r[6],
            "load_day_num": r[7],
            "seconds": r[8],
        })
    return out


def append_load_duration_pg(record: dict) -> None:
    """Insert a single load-duration record."""
    ts_iso_raw = record.get("ts_iso")
    ts_iso_val: datetime | None = None
    if ts_iso_raw:
        try:
            ts_iso_val = datetime.fromisoformat(str(ts_iso_raw))
        except Exception:
            ts_iso_val = None

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO load_durations
                        (ts, ts_iso, run_date, load_date, truck, route, load_day_num, seconds)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        float(record.get("ts") or 0),
                        ts_iso_val,
                        str(record.get("run_date") or ""),
                        str(record.get("load_date") or ""),
                        int(record.get("truck") or 0),
                        int(record.get("route") or 0),
                        record.get("load_day_num"),
                        int(record.get("seconds") or 0),
                    ),
                )
    except Exception:
        logger.exception("append_load_duration_pg failed")


def remove_abnormal_loadtimes_pg(
    min_seconds: int = 120,
    max_seconds: int = 1800,
) -> tuple[int, int]:
    """
    Delete duration records outside [min_seconds, max_seconds].
    Returns (total_before, deleted_count).
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM load_durations")
            total_before = int((cur.fetchone() or (0,))[0])
            cur.execute(
                "DELETE FROM load_durations "
                "WHERE seconds < %s OR seconds > %s",
                (min_seconds, max_seconds),
            )
            deleted = cur.rowcount
    return total_before, deleted


def trim_duration_history_pg(max_rows: int = 2000) -> int:
    """Keep only the most recent *max_rows* records.  Returns deleted count."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM load_durations
                WHERE id NOT IN (
                    SELECT id FROM load_durations ORDER BY ts DESC LIMIT %s
                )
                """,
                (max_rows,),
            )
            return cur.rowcount
