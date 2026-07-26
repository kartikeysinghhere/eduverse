import os
from streamlit.testing.v1 import AppTest
from utils.auth import reset_attempts, get_db_connection
from utils.db import get_supabase_client, get_supabase_service_client
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=ROOT / ".env", override=True)
DB_MODE = os.environ.get("DB_MODE", "supabase")

print(f"--- TESTING IN {DB_MODE.upper()} MODE ---")

reset_attempts("admin")
print("Reset attempts for admin.")

at = AppTest.from_file("app.py").run()
at.button[0].click().run()

at.text_input(key="login_username").input("admin").run()
at.text_input(key="login_password").input("wrongpassword").run()

for i in range(1, 6):
    at.button[0].click().run() # Click the login button
    err = at.error[0].value if at.error else None
    print(f"Attempt {i} -> Error: {err}")

# 6th attempt
at.button[0].click().run()
err = at.error[0].value if at.error else None
print(f"Attempt 6 -> Error: {err}")

print("\n--- DATABASE CHECK ---")
if DB_MODE == "supabase":
    client = get_supabase_service_client()
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
        print(row)
