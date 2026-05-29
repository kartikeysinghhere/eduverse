import os
import sqlite3
import bcrypt
from dotenv import load_dotenv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

DB_MODE = os.environ.get("DB_MODE", "supabase")

HARDCODED_USERS = {
    "admin": {
        "id": 999,
        "username": "admin",
        "role": "Admin",
        "email": "admin@eduverse.ai",
        "password": "EduAdmin@2026"
    },
    "teacher": {
        "id": 998,
        "username": "teacher",
        "role": "Teacher",
        "email": "teacher@eduverse.ai",
        "password": "EduTeacher@2026"
    }
}

def get_db_connection():
    return sqlite3.connect(str(ROOT / "eduverse.db"))

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def sign_in(username, password):
    if DB_MODE == "supabase":
        # Step 1: Try Supabase users table (bcrypt verify)
        try:
            from supabase import create_client
            URL = os.environ.get("SUPABASE_URL")
            KEY = os.environ.get("SUPABASE_KEY")
            if URL and KEY:
                supabase = create_client(URL, KEY)
                response = supabase.table("users").select("*").eq("username", username).execute()
                if response.data:
                    user = response.data[0]
                    if verify_password(password, user['password_hash']):
                        return user
        except Exception as e:
            print(f"Supabase auth error: {e}")
            
        # Step 2: If Supabase fails -> try hardcoded users
        if username in HARDCODED_USERS:
            h_user = HARDCODED_USERS[username]
            if password == h_user["password"]:
                return {
                    "id": h_user["id"],
                    "username": h_user["username"],
                    "role": h_user["role"],
                    "email": h_user["email"]
                }
                
        # Step 3: If both fail -> return None
        return None
    
    # Fallback/Default to SQLite
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        conn.close()
        
        if row:
            user = dict(row)
            if verify_password(password, user['password_hash']):
                return user
        return None
    except Exception as e:
        print(f"SQLite auth error: {e}")
        return None
