import bcrypt
import sqlite3
import os
from dotenv import load_dotenv
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils.db import get_supabase_service_client

load_dotenv(override=True)

new_password = "EduAdmin_99!"
hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Update Supabase
try:
    supabase = get_supabase_service_client()
    supabase.table('users').update({'password_hash': hashed}).eq('username', 'admin').execute()
    print("Updated admin password in Supabase.")
except Exception as e:
    print(f"Supabase update failed: {e}")

# Update SQLite
try:
    conn = sqlite3.connect("eduverse.db")
    cur = conn.cursor()
    cur.execute("UPDATE users SET password_hash = ? WHERE username = 'admin'", (hashed,))
    conn.commit()
    conn.close()
    print("Updated admin password in SQLite.")
except Exception as e:
    print(f"SQLite update failed: {e}")
