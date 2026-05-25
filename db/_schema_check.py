import os
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

from db.connection import init_pool, get_conn
init_pool()
with get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema='public'
            ORDER BY table_name, ordinal_position
        """)
        rows = cur.fetchall()

current_table = None
for table, col, dtype in rows:
    if table != current_table:
        print(f"\n[{table}]")
        current_table = table
    print(f"  {col}: {dtype}")
