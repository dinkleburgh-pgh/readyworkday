"""Quick smoke test for all db modules. Run with:
    python db/_test_all.py
Env vars must be set (or loaded from .env) before running.
"""
import os, sys

# Load .env manually if running outside the app
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

from db.connection import init_pool, close_pool, get_conn
from db.config import (
    load_quick_amounts_pg, load_censor_words_pg, load_off_schedule_defaults_pg
)
from db.auth import load_auth_users_pg, load_auth_requests_pg, load_sessions_pg
from db.state import load_state_pg, load_archived_state_pg, list_archived_run_dates_pg
from db.fleet import load_fleet_pg, load_truck_types_pg
from db.audit import load_audit_entries_pg
from db.batch import load_batch_history_pg
from db.durations import load_duration_history_pg
from db.communications import load_messages_pg

PASS = "\033[92m[OK]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
errors = []

def check(label, fn, *args, assert_fn=None, **kwargs):
    try:
        result = fn(*args, **kwargs)
        if assert_fn:
            assert_fn(result)
        print(f"{PASS} {label}: {_summarize(result)}")
        return result
    except Exception as e:
        print(f"{FAIL} {label}: {e}")
        errors.append((label, e))
        return None

def _summarize(v):
    if isinstance(v, dict):
        return f"{len(v)} keys"
    if isinstance(v, (list, set)):
        return f"{len(v)} entries"
    if v is None:
        return "None"
    return str(v)[:80]

print("=== DB CONNECTIVITY ===")
init_pool()
print(f"{PASS} Pool initialized\n")

print("=== CONFIG ===")
amounts = check("Quick amounts", load_quick_amounts_pg, assert_fn=lambda r: r and len(r) > 0)
check("Censor words", load_censor_words_pg, assert_fn=lambda r: r and len(r) > 0)
check("Off-schedule defaults", load_off_schedule_defaults_pg)

print("\n=== FLEET ===")
check("Fleet trucks", load_fleet_pg)
check("Truck type overrides", load_truck_types_pg)

print("\n=== AUTH ===")
users = check("Users", load_auth_users_pg, assert_fn=lambda r: r and len(r) > 0)
check("Auth requests", load_auth_requests_pg)
check("Sessions", load_sessions_pg)

print("\n=== STATE ===")
dates = check("Archived run dates", list_archived_run_dates_pg, assert_fn=lambda r: r and len(r) > 0)
if dates:
    latest = dates[0]  # dates are DESC, so [0] is the most recent
    check(f"Archived state ({latest})", load_archived_state_pg, latest, assert_fn=lambda r: r is not None)

print("\n=== AUDIT / BATCH / DURATIONS ===")
run_date = dates[-1] if dates else None
check("Audit entries", load_audit_entries_pg, run_date)
check("Batch history", load_batch_history_pg, run_date)
check("Load durations", load_duration_history_pg)

print("\n=== COMMUNICATIONS ===")
check("Chat messages", load_messages_pg, "Team")

print("\n=== WRITE TEST ===")
try:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO config (key, value) VALUES ('_test_canary', '{}'::jsonb) ON CONFLICT (key) DO UPDATE SET value='{}'::jsonb")
            cur.execute("DELETE FROM config WHERE key='_test_canary'")
    print(f"{PASS} Write test: INSERT + DELETE committed successfully")
except Exception as e:
    print(f"{FAIL} Write test: {e}")
    errors.append(("write_test", e))

close_pool()

print()
if errors:
    print(f"\033[91m=== {len(errors)} FAILURE(S) ===\033[0m")
    for label, err in errors:
        print(f"  - {label}: {err}")
    sys.exit(1)
else:
    print("\033[92m=== ALL CHECKS PASSED ===\033[0m")
