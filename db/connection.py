"""
db/connection.py
PostgreSQL connection pool for TruckApp.

Environment variables (all required unless noted):
  TRUCKAPP_PG_HOST     — DB hostname (default: localhost)
  TRUCKAPP_PG_PORT     — DB port     (default: 5432)
  TRUCKAPP_PG_DBNAME   — Database name (required)
  TRUCKAPP_PG_USER     — DB user (required)
  TRUCKAPP_PG_PASSWORD — DB password (required)
  TRUCKAPP_PG_MINCONN  — Pool min connections (default: 2)
  TRUCKAPP_PG_MAXCONN  — Pool max connections (default: 10)

Usage in Streamlit:
    import streamlit as st
    from db.connection import get_pool

    @st.cache_resource
    def _pool():
        return get_pool()
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager

try:
    import psycopg2
    from psycopg2.pool import ThreadedConnectionPool
except ImportError as _psycopg2_missing:
    raise ImportError(
        "psycopg2-binary is not installed in the current Python environment. "
        "Run: pip install psycopg2-binary"
    ) from _psycopg2_missing

_pool_instance: ThreadedConnectionPool | None = None

logger = logging.getLogger(__name__)


def _dsn() -> dict:
    return {
        "host": os.environ.get("TRUCKAPP_PG_HOST", "localhost"),
        "port": int(os.environ.get("TRUCKAPP_PG_PORT", "5432")),
        "dbname": os.environ["TRUCKAPP_PG_DBNAME"],
        "user": os.environ["TRUCKAPP_PG_USER"],
        "password": os.environ["TRUCKAPP_PG_PASSWORD"],
        "sslmode": os.environ.get("TRUCKAPP_PG_SSLMODE", "prefer"),
        "connect_timeout": int(os.environ.get("TRUCKAPP_PG_CONNECT_TIMEOUT", "10")),
        # Keep connections alive through TrueNAS network idle timeouts.
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 5,
        "keepalives_count": 3,
    }


def init_pool() -> ThreadedConnectionPool:
    """Create (or return existing) the module-level connection pool."""
    global _pool_instance
    if _pool_instance is not None:
        return _pool_instance

    minconn = int(os.environ.get("TRUCKAPP_PG_MINCONN", "2"))
    maxconn = int(os.environ.get("TRUCKAPP_PG_MAXCONN", "10"))
    dsn = _dsn()
    logger.info(
        "Initialising PostgreSQL pool %s:%s/%s (min=%d max=%d)",
        dsn["host"], dsn["port"], dsn["dbname"], minconn, maxconn,
    )
    _pool_instance = ThreadedConnectionPool(minconn, maxconn, **dsn)
    return _pool_instance


def get_pool() -> ThreadedConnectionPool:
    """Return the pool, creating it on first call."""
    if _pool_instance is None:
        return init_pool()
    return _pool_instance


@contextmanager
def get_conn(max_stale_retries: int = 2):
    """
    Context manager that checks out a live connection from the pool, commits
    on success, and rolls back on error.

    Stale connection handling (common after a PostgreSQL restart or TrueNAS
    network idle timeout):
      - Before yielding, checks ``conn.closed`` (0 = open, 1 = closed,
        2 = broken).  A non-zero value means the connection was left dead
        in the pool; it is disposed and the pool is asked for another one.
      - Up to *max_stale_retries* additional attempts are made.
      - If every attempt returns a stale connection, ``_force_pool_reset()``
        tears down the entire pool so the next call rebuilds from scratch.

    Broken-during-use handling:
      - If ``psycopg2.OperationalError`` is raised *inside* the ``with``
        block, the broken connection is disposed (not returned to the pool)
        so the pool replaces it on the next checkout.

    Usage::

        from db.connection import get_conn
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
    pool = get_pool()
    conn = None
    last_stale_exc: Exception | None = None

    for attempt in range(max_stale_retries + 1):
        conn = pool.getconn()
        if conn.closed == 0:
            break  # got a live connection
        # Connection is closed or broken — dispose and let the pool allocate a fresh one.
        logger.warning(
            "Stale connection on checkout (closed=%s); disposing (attempt %d/%d)",
            conn.closed, attempt + 1, max_stale_retries + 1,
        )
        last_stale_exc = psycopg2.OperationalError(
            f"Stale pooled connection (closed={conn.closed})"
        )
        try:
            pool.putconn(conn, close=True)
        except Exception:
            pass
        conn = None
    else:
        # Loop completed without break: every attempt returned a stale connection.
        _force_pool_reset()
        raise last_stale_exc or psycopg2.OperationalError(
            "All pooled connections are stale; pool has been reset — retry the operation."
        )

    try:
        yield conn
        conn.commit()
    except psycopg2.OperationalError as exc:
        # Connection broke during the operation — dispose so the pool replaces it.
        logger.warning("OperationalError during query; disposing broken connection: %s", exc)
        try:
            conn.rollback()
        except Exception:
            pass
        try:
            pool.putconn(conn, close=True)
        except Exception:
            pass
        conn = None
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        if conn is not None:
            pool.putconn(conn)


def _force_pool_reset() -> None:
    """
    Tear down the current pool so the next ``get_pool()`` call rebuilds it
    from scratch.  Call this when the pool is known to be fully dead (e.g.
    after a PostgreSQL server restart).

    The ``@st.cache_resource``-cached reference in the main app becomes a
    dangling pointer but is harmless — ``get_conn()`` always goes through
    ``get_pool()`` / ``_pool_instance``, not the cached object.
    """
    global _pool_instance
    logger.warning("Forcing PostgreSQL connection pool reset.")
    try:
        if _pool_instance is not None:
            _pool_instance.closeall()
    except Exception:
        pass
    finally:
        _pool_instance = None


def close_pool() -> None:
    """Shut down the pool cleanly (call on app teardown)."""
    global _pool_instance
    if _pool_instance is not None:
        _pool_instance.closeall()
        _pool_instance = None
