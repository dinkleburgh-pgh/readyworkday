"""
db/fleet.py
PostgreSQL replacements for load_fleet_file() / save_fleet_file()
and load_truck_types() / save_truck_types().
"""

from __future__ import annotations

import logging

from db.connection import get_conn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fleet trucks list
# ---------------------------------------------------------------------------

def load_fleet_pg() -> list[int]:
    """Return sorted list of enabled truck numbers."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT truck_num FROM fleet_trucks WHERE enabled = TRUE ORDER BY truck_num"
            )
            rows = cur.fetchall()
    return [r[0] for r in rows]


def save_fleet_pg(truck_nums: list[int]) -> None:
    """
    Replace the full fleet list.  Trucks already in the table keep their
    truck_type; new trucks default to 'Uniform'.  Trucks removed from the
    list are soft-deleted (enabled = FALSE) rather than hard-deleted.
    """
    nums = sorted({int(t) for t in (truck_nums or [])})
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Insert any trucks that don't exist yet.
            for truck_num in nums:
                cur.execute(
                    """
                    INSERT INTO fleet_trucks (truck_num, truck_type, is_spare, enabled)
                    VALUES (%s, 'Uniform', FALSE, TRUE)
                    ON CONFLICT (truck_num) DO UPDATE SET enabled = TRUE, updated_at = NOW()
                    """,
                    (truck_num,),
                )
            # Soft-disable trucks no longer in the list.
            if nums:
                cur.execute(
                    "UPDATE fleet_trucks SET enabled = FALSE, updated_at = NOW() "
                    "WHERE truck_num != ALL(%s)",
                    (nums,),
                )
            else:
                cur.execute(
                    "UPDATE fleet_trucks SET enabled = FALSE, updated_at = NOW()"
                )


# ---------------------------------------------------------------------------
# Truck types
# ---------------------------------------------------------------------------

def load_truck_types_pg() -> dict[int, str]:
    """Return {truck_num: truck_type} for all trucks in the table."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT truck_num, truck_type FROM fleet_trucks")
            rows = cur.fetchall()
    return {r[0]: r[1] for r in rows}


def save_truck_types_pg(types: dict[int, str]) -> None:
    """
    Upsert truck types.  Creates the truck row if it doesn't exist.
    *types* is {truck_num: truck_type_str}.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            for truck_num_raw, truck_type in (types or {}).items():
                truck_num = int(truck_num_raw)
                truck_type_str = str(truck_type or "Uniform").strip() or "Uniform"
                cur.execute(
                    """
                    INSERT INTO fleet_trucks (truck_num, truck_type, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (truck_num) DO UPDATE
                        SET truck_type = EXCLUDED.truck_type,
                            updated_at = NOW()
                    """,
                    (truck_num, truck_type_str),
                )
