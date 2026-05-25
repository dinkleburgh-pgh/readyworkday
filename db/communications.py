"""
db/communications.py
PostgreSQL replacements for _load_communications_messages() /
_save_communications_messages() / _append_communications_message().
"""

from __future__ import annotations

import logging
import time
from typing import Sequence

from db.connection import get_conn

logger = logging.getLogger(__name__)

MAX_MESSAGES = 500
MAX_MESSAGE_LENGTH = 1000


def load_messages_pg(
    channel: str = "Team",
    limit: int = MAX_MESSAGES,
) -> list[dict]:
    """Return the most recent *limit* non-deleted messages for *channel*."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT message_id, ts, channel, username, message
                FROM chat_messages
                WHERE channel = %s AND deleted_at IS NULL
                ORDER BY ts DESC
                LIMIT %s
                """,
                (channel, limit),
            )
            rows = cur.fetchall()
    # Return in chronological order (oldest first, matching JSON file convention).
    rows_asc = list(reversed(rows))
    return [
        {
            "id": r[0],
            "ts": float(r[1]),
            "channel": r[2],
            "username": r[3],
            "message": r[4],
        }
        for r in rows_asc
    ]


def append_message_pg(
    channel: str,
    username: str,
    message: str,
    message_id: str | None = None,
    ts: float | None = None,
) -> tuple[bool, str]:
    """
    Insert a single chat message.
    Returns (success: bool, error_message: str).
    """
    text = str(message or "").strip()[:MAX_MESSAGE_LENGTH]
    if not text:
        return False, "Message cannot be empty."
    msg_id = str(
        message_id
        or f"m{int((ts or time.time()) * 1000)}-{int(time.perf_counter_ns() % 1_000_000)}"
    )
    ts_val = float(ts or time.time())
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_messages (message_id, ts, channel, username, message)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (message_id) DO NOTHING
                    """,
                    (msg_id, ts_val, str(channel or "Team"), str(username or ""), text),
                )
        return True, ""
    except Exception as exc:
        logger.exception("append_message_pg failed")
        return False, str(exc)


def delete_message_pg(message_id: str, actor: str = "") -> bool:
    """Soft-delete a single message by ID. Returns True if a row was affected."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE chat_messages SET deleted_at = NOW() WHERE message_id = %s",
                (str(message_id),),
            )
            return cur.rowcount > 0


def prune_messages_by_age_pg(max_age_days: float) -> tuple[int, int]:
    """
    Hard-delete messages older than *max_age_days* days.
    Returns (total_before, deleted_count).
    """
    cutoff_ts = time.time() - max_age_days * 86400
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM chat_messages WHERE deleted_at IS NULL")
            total_before = int((cur.fetchone() or (0,))[0])
            cur.execute(
                "DELETE FROM chat_messages WHERE ts < %s", (cutoff_ts,)
            )
            deleted = cur.rowcount
    return total_before, deleted


def keep_latest_messages_pg(keep_count: int = MAX_MESSAGES) -> tuple[int, int]:
    """
    Retain only the most recent *keep_count* non-deleted messages.
    Returns (total_before, deleted_count).
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM chat_messages WHERE deleted_at IS NULL")
            total_before = int((cur.fetchone() or (0,))[0])
            cur.execute(
                """
                DELETE FROM chat_messages
                WHERE message_id NOT IN (
                    SELECT message_id
                    FROM chat_messages
                    WHERE deleted_at IS NULL
                    ORDER BY ts DESC
                    LIMIT %s
                )
                """,
                (keep_count,),
            )
            deleted = cur.rowcount
    return total_before, deleted


def clear_all_messages_pg(channel: str | None = None) -> int:
    """Hard-delete all messages (optionally scoped to a channel)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            if channel:
                cur.execute(
                    "DELETE FROM chat_messages WHERE channel = %s", (channel,)
                )
            else:
                cur.execute("DELETE FROM chat_messages")
            return cur.rowcount


def latest_message_ts_pg(channel: str = "Team") -> float:
    """Return the timestamp of the newest non-deleted message, or 0.0."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT MAX(ts) FROM chat_messages "
                "WHERE channel = %s AND deleted_at IS NULL",
                (channel,),
            )
            row = cur.fetchone()
    val = (row[0] if row else None)
    return float(val) if val is not None else 0.0
