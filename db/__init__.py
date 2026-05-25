# db package — PostgreSQL persistence layer for TruckApp
# Import the pool accessor so callers can do: from db import get_pool
try:
    from db.connection import get_pool, init_pool, _force_pool_reset
except ImportError:
    get_pool = None  # type: ignore[assignment]
    init_pool = None  # type: ignore[assignment]
    _force_pool_reset = None  # type: ignore[assignment]
