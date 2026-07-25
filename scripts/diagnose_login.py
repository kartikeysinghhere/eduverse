"""
End-to-end login diagnostic and fix.
Steps 1-6 as requested by user.
"""
import os, sys, sqlite3, bcrypt
from typing import cast
from pathlib import Path
from dotenv import load_dotenv

# ROOT = the education/ project root (parent of scripts/)
ROOT = Path(__file__).resolve().parent.parent
env_path = ROOT / ".env"
print(f"Loading .env from: {env_path} (exists: {env_path.exists()})")
load_dotenv(dotenv_path=str(env_path), override=True)

SEPARATOR = "=" * 60

# ── STEP 1: Print DB_MODE ──────────────────────────────────────
print(f"\n{SEPARATOR}")
print("STEP 1: Current DB_MODE")
print(SEPARATOR)
db_mode = os.environ.get("DB_MODE", "sqlite")
print(f"DB_MODE = {db_mode}")

db_path = ROOT / "eduverse.db"
client = None

# ── STEP 2: Test connection to whichever DB is active ──────────
print(f"\n{SEPARATOR}")
print(f"STEP 2: Test {db_mode} connection")
print(SEPARATOR)

if db_mode == "supabase":
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    print(f"SUPABASE_URL = {url}")
    print(f"SUPABASE_KEY = {key[:20]}..." if key else "SUPABASE_KEY = (empty)")

    if not key.startswith("eyJ"):
        print(f"\nFATAL: SUPABASE_KEY is NOT a valid JWT.")
        print(f"  Real Supabase keys start with 'eyJ...'")
        print(f"  Your key starts with '{key[:25]}'")
        print(f"  Every Supabase query will fail. Cannot proceed with supabase mode.")
        sys.exit(1)

    try:
        from supabase import create_client
        client = create_client(url, key)
        res = client.table("users").select("id,username,role").limit(1).execute()
        print(f"Connection SUCCESS. Sample result: {res.data}")
    except Exception as e:
        print(f"Connection FAILED: {type(e).__name__}: {e}")
        sys.exit(1)

elif db_mode == "sqlite":
    print(f"SQLite DB path: {db_path}")
    print(f"File exists: {db_path.exists()}")
    if not db_path.exists():
        print("FATAL: eduverse.db does not exist!")
        sys.exit(1)
    print(f"File size: {db_path.stat().st_size} bytes")
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()
    print(f"Connection SUCCESS. Users table has {count} rows.")

# ── STEP 3: Query admin user row ───────────────────────────────
print(f"\n{SEPARATOR}")
print("STEP 3: Query admin user row")
print(SEPARATOR)

stored_hash = None

if db_mode == "sqlite":
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = 'admin'")
    row = cur.fetchone()
    conn.close()

    if row:
        admin = dict(row)
        print(f"  id            = {admin.get('id')}")
        print(f"  username      = {admin.get('username')}")
        print(f"  role          = {admin.get('role')}")
        print(f"  email         = {admin.get('email')}")
        print(f"  password_hash = {admin.get('password_hash')}")
        stored_hash = admin.get("password_hash", "")
    else:
        print("  *** admin user NOT FOUND in users table! ***")

elif db_mode == "supabase":
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    client = create_client(url, key)
    res = client.table("users").select("*").eq("username", "admin").execute()
    if res.data:
        admin = cast(dict, res.data[0])
        print(f"  id            = {admin.get('id')}")
        print(f"  username      = {admin.get('username')}")
        print(f"  role          = {admin.get('role')}")
        print(f"  email         = {admin.get('email')}")
        print(f"  password_hash = {admin.get('password_hash')}")
        stored_hash = admin.get("password_hash", "")
    else:
        print("  *** admin user NOT FOUND in users table! ***")

# ── STEP 4: bcrypt.checkpw verification ────────────────────────
print(f"\n{SEPARATOR}")
print("STEP 4: bcrypt.checkpw('TempAdmin123!', stored_hash)")
print(SEPARATOR)

test_password = "TempAdmin123!"
match = False

if stored_hash and isinstance(stored_hash, str):
    try:
        match = bcrypt.checkpw(test_password.encode("utf-8"), stored_hash.encode("utf-8"))
        print(f"  Result: {match}")
    except Exception as e:
        print(f"  bcrypt error: {e}")
        match = False
else:
    print("  Cannot verify — no admin row or no hash found.")

# ── STEP 5 & 6: If mismatch, re-seed and re-verify ────────────
if not match:
    print(f"\n{SEPARATOR}")
    print("STEP 5: Password DOES NOT match. Resetting now...")
    print(SEPARATOR)

    new_hash = bcrypt.hashpw(test_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    print(f"  New bcrypt hash for 'TempAdmin123!': {new_hash}")

    if db_mode == "sqlite":
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE username = 'admin'")
        row = cur.fetchone()

        if row:
            cur.execute(
                "UPDATE users SET password_hash = ? WHERE username = 'admin'",
                (new_hash,)
            )
            print(f"  Updated existing admin user (id={row[0]}) with new password hash.")
        else:
            cur.execute(
                "INSERT INTO users (id, username, password_hash, role, email) VALUES (?, ?, ?, ?, ?)",
                (999, "admin", new_hash, "Admin", "admin@eduverse.ai")
            )
            print(f"  Inserted new admin user (id=999) with password hash.")

        conn.commit()
        conn.close()

    elif db_mode == "supabase":
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")

        client = create_client(url, key)
        res = client.table("users").select("id").eq("username", "admin").execute()
        if res.data:
            client.table("users").update({"password_hash": new_hash}).eq("username", "admin").execute()
            print(f"  Updated admin in Supabase with new hash.")
        else:
            client.table("users").insert({
                "id": 999, "username": "admin", "password_hash": new_hash,
                "role": "Admin", "email": "admin@eduverse.ai"
            }).execute()
            print(f"  Inserted admin into Supabase.")

    print(f"\n{SEPARATOR}")
    print("STEP 6: Re-verify after reset")
    print(SEPARATOR)

    if db_mode == "sqlite":
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE username = 'admin'")
        row = cur.fetchone()
        conn.close()

        if row:
            fresh_hash = dict(row)["password_hash"]
            print(f"  Re-read hash from DB: {fresh_hash}")
            verify = bcrypt.checkpw(test_password.encode("utf-8"), fresh_hash.encode("utf-8"))
            print(f"  bcrypt.checkpw('TempAdmin123!', fresh_hash) = {verify}")

            if verify:
                print(f"\n  >>> CONFIRMED: 'TempAdmin123!' now matches the stored hash.")
                print(f"      Login with username='admin' password='TempAdmin123!' WILL work.")
            else:
                print(f"\n  STILL DOES NOT MATCH.")
        else:
            print("  Admin row still not found after insert.")

    elif db_mode == "supabase":
        assert client is not None, "Supabase client should have been created"
        res = client.table("users").select("password_hash").eq("username", "admin").execute()
        if res.data:
            row = cast(dict, res.data[0])
            fresh_hash = cast(str, row["password_hash"])
            print(f"  Re-read hash from Supabase: {fresh_hash}")
            verify = bcrypt.checkpw(test_password.encode("utf-8"), fresh_hash.encode("utf-8"))
            print(f"  bcrypt.checkpw('TempAdmin123!', fresh_hash) = {verify}")
            if verify:
                print(f"\n  >>> CONFIRMED: 'TempAdmin123!' now matches the stored hash.")
            else:
                print(f"\n  STILL DOES NOT MATCH.")

else:
    print(f"\n{SEPARATOR}")
    print("RESULT: Password already matches!")
    print(SEPARATOR)
    print(f"  'TempAdmin123!' already matches the stored hash.")
    print(f"  Login with username='admin' password='TempAdmin123!' should work.")

print(f"\n{SEPARATOR}")
print("FINAL STATE")
print(SEPARATOR)
print(f"  DB_MODE     = {db_mode}")
print(f"  DB file     = {db_path}")
print(f"  Target user = admin")
print(f"  Target pass = TempAdmin123!")
print(f"\n  IMPORTANT: Restart Streamlit for .env changes to take effect!")
print(f"  Stop the running instance, then run: streamlit run app.py")
