import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=ROOT / '.env', override=True)

from utils.auth import record_attempt, is_login_blocked, reset_attempts, get_db_connection
from utils.db import get_supabase_client

print('DB MODE:', os.environ.get('DB_MODE'))
print("Resetting attempts...")
reset_attempts("admin")

print("Checking initial block state:", is_login_blocked("admin"))

for i in range(1, 6):
    record_attempt("admin")
    print(f"Recorded attempt {i}")

print("Checking block state after 5 attempts:", is_login_blocked("admin"))

print("\n--- DATABASE CHECK ---")
if os.environ.get("DB_MODE") == "supabase":
    client = get_supabase_client()
    res = client.table("failed_logins").select("*").eq("username", "admin").execute()
    print(f"Supabase Rows: {len(res.data)}")
    for row in res.data:
        print(row)
else:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM failed_logins WHERE username = 'admin'")
    rows = cur.fetchall()
    print(f"SQLite Rows: {len(rows)}")
    for row in rows:
        print(dict(row))
