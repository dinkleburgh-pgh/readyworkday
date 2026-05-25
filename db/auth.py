"""
db/auth.py
PostgreSQL replacements for:
  _load_auth_users()       / _save_auth_users()
  _load_auth_requests()    / _save_auth_requests()
  _load_sessions()         / _save_sessions()
  _write_auth_session()    / _restore_from_session_store()
"""

from __future__ import annotations

import logging
import secrets
import time

from db.connection import get_conn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def load_auth_users_pg() -> dict[str, dict]:
    """
    Return {username: {name, password_hash, role, enabled}} mapping.
    Keys are lowercase canonical usernames, matching the app convention.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, display_name, password_hash, role, enabled "
                "FROM users ORDER BY username"
            )
            rows = cur.fetchall()
    result: dict[str, dict] = {}
    for username, display_name, password_hash, role, enabled in rows:
        result[str(username).lower()] = {
            "name": str(display_name or username),
            "password": str(password_hash),
            "role": str(role),
            "enabled": bool(enabled),
        }
    return result


def save_auth_users_pg(users: dict[str, dict]) -> None:
    """
    Full replace of the users table from the in-memory dict.
    Existing rows are upserted; users absent from *users* are disabled
    (not deleted) to preserve audit history.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            incoming_usernames: list[str] = []
            for username_raw, user_data in (users or {}).items():
                username = str(username_raw or "").strip().lower()
                if not username:
                    continue
                incoming_usernames.append(username)
                display_name = str(user_data.get("name") or username)
                password_hash = str(user_data.get("password") or "")
                role = str(user_data.get("role") or "guest")
                enabled = bool(user_data.get("enabled", True))
                cur.execute(
                    """
                    INSERT INTO users
                        (username, display_name, password_hash, role, enabled, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (username) DO UPDATE
                        SET display_name  = EXCLUDED.display_name,
                            password_hash = EXCLUDED.password_hash,
                            role          = EXCLUDED.role,
                            enabled       = EXCLUDED.enabled,
                            updated_at    = NOW()
                    """,
                    (username, display_name, password_hash, role, enabled),
                )
            # Soft-disable any users no longer present.
            if incoming_usernames:
                cur.execute(
                    "UPDATE users SET enabled = FALSE, updated_at = NOW() "
                    "WHERE username != ALL(%s)",
                    (incoming_usernames,),
                )


def upsert_user_pg(
    username: str,
    *,
    display_name: str | None = None,
    password_hash: str | None = None,
    role: str | None = None,
    enabled: bool | None = None,
) -> None:
    """Upsert a single user row.  Only supplied fields are updated."""
    username_key = str(username or "").strip().lower()
    if not username_key:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username FROM users WHERE username = %s", (username_key,)
            )
            exists = cur.fetchone() is not None
            if not exists:
                cur.execute(
                    """
                    INSERT INTO users (username, display_name, password_hash, role, enabled)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        username_key,
                        display_name or username_key,
                        password_hash or "",
                        role or "guest",
                        True if enabled is None else bool(enabled),
                    ),
                )
            else:
                parts = []
                params: list = []
                if display_name is not None:
                    parts.append("display_name = %s"); params.append(display_name)
                if password_hash is not None:
                    parts.append("password_hash = %s"); params.append(password_hash)
                if role is not None:
                    parts.append("role = %s"); params.append(role)
                if enabled is not None:
                    parts.append("enabled = %s"); params.append(enabled)
                if parts:
                    parts.append("updated_at = NOW()")
                    params.append(username_key)
                    cur.execute(
                        f"UPDATE users SET {', '.join(parts)} WHERE username = %s",
                        params,
                    )


# ---------------------------------------------------------------------------
# Auth access requests
# ---------------------------------------------------------------------------

def load_auth_requests_pg() -> dict[str, dict]:
    """Return {request_id: {...}} mapping, app-compatible format."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT request_id, username, display_name, requested_role, "
                "status, note, created_at, resolved_at, resolved_by "
                "FROM user_requests ORDER BY created_at"
            )
            rows = cur.fetchall()
    result: dict[str, dict] = {}
    for (req_id, username, display_name, requested_role,
         status, note, created_at, resolved_at, resolved_by) in rows:
        result[str(req_id)] = {
            "request_id": str(req_id),
            "username": str(username),
            "name": str(display_name or username or ""),
            "role": str(requested_role or ""),
            "status": str(status or "pending"),
            "note": str(note or ""),
            "created_at": created_at.isoformat() if created_at else None,
            "resolved_at": resolved_at.isoformat() if resolved_at else None,
            "resolved_by": str(resolved_by or "") if resolved_by else None,
        }
    return result


def save_auth_requests_pg(requests: dict[str, dict]) -> None:
    """Full upsert of the requests dict."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            for req_id_raw, req_data in (requests or {}).items():
                req_id = str(req_id_raw or "").strip()
                if not req_id:
                    continue
                cur.execute(
                    """
                    INSERT INTO user_requests
                        (request_id, username, display_name, requested_role,
                         status, note, resolved_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (request_id) DO UPDATE
                        SET username       = EXCLUDED.username,
                            display_name   = EXCLUDED.display_name,
                            requested_role = EXCLUDED.requested_role,
                            status         = EXCLUDED.status,
                            note           = EXCLUDED.note,
                            resolved_by    = EXCLUDED.resolved_by
                    """,
                    (
                        req_id,
                        str(req_data.get("username") or ""),
                        str(req_data.get("name") or ""),
                        str(req_data.get("role") or ""),
                        str(req_data.get("status") or "pending"),
                        str(req_data.get("note") or ""),
                        req_data.get("resolved_by") or None,
                    ),
                )


# ---------------------------------------------------------------------------
# Server-side auth sessions
# ---------------------------------------------------------------------------

def load_sessions_pg() -> dict:
    """Return {session_id: {username, role, created_at, expires_at}} dict."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT session_id, username, role, created_at, expires_at "
                "FROM auth_sessions"
            )
            rows = cur.fetchall()
    return {
        r[0]: {
            "username": r[1],
            "role": r[2],
            "created_at": float(r[3]),
            "expires_at": float(r[4]),
        }
        for r in rows
    }


def prune_sessions_pg(now_ts: float | None = None) -> int:
    """Delete expired sessions.  Returns number of rows deleted."""
    ts = now_ts if now_ts is not None else time.time()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM auth_sessions WHERE expires_at <= %s", (ts,)
            )
            return cur.rowcount


def write_auth_session_pg(
    username: str,
    role: str,
    expiry_days: int = 30,
) -> str | None:
    """
    Persist a server-side session and return its session_id token.
    Prunes expired sessions as a side effect.
    """
    try:
        session_id = secrets.token_hex(32)
        now_ts = time.time()
        expires_at = now_ts + expiry_days * 86400
        prune_sessions_pg(now_ts)
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO auth_sessions
                        (session_id, username, role, created_at, expires_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (session_id) DO NOTHING
                    """,
                    (session_id, str(username), str(role), now_ts, expires_at),
                )
        return session_id
    except Exception:
        logger.exception("write_auth_session_pg failed")
        return None


def resolve_session_pg(session_id: str) -> dict | None:
    """
    Look up a session by ID, enforce expiry, and return
    {username, role} or None if the session is missing/expired.
    """
    if not session_id:
        return None
    now_ts = time.time()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT username, role, expires_at "
                "FROM auth_sessions WHERE session_id = %s",
                (session_id,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    username, role, expires_at = row
    if float(expires_at) <= now_ts:
        return None
    return {"username": str(username), "role": str(role)}


def delete_session_pg(session_id: str) -> None:
    """Explicitly invalidate a session (logout)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM auth_sessions WHERE session_id = %s", (session_id,)
            )
