import os
import sqlite3
import bcrypt
import logging
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
from utils.db import get_supabase_client

logger = logging.getLogger("eduverse.auth")
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env", override=True)

DB_MODE = os.environ.get("DB_MODE", "supabase")

MAX_USERNAME_LENGTH = 150
MAX_PASSWORD_LENGTH = 128

def get_db_connection():
    return sqlite3.connect(str(ROOT / "eduverse.db"))

def verify_password(password: str, hashed: str) -> bool:
    if not password or not hashed:
        return False

    if len(password) > MAX_PASSWORD_LENGTH:
        return False

    try:
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error("Password verification internal error occurred.")
        return False

def sign_in(username, password):
    if not username or not password:
        return None

    if len(username) > MAX_USERNAME_LENGTH or len(password) > MAX_PASSWORD_LENGTH:
        logger.warning(f"Authentication rejected due to excessive input lengths.")
        return None

    login_id = username.strip()

    if DB_MODE == "supabase":
        try:
            supabase = get_supabase_client()
            response = supabase.table("users").select("*").eq("username", login_id).execute()
            if not response.data and "@" in login_id:
                response = supabase.table("users").select("*").eq("email", login_id).execute()

            if response.data:
                user = response.data[0]
                if verify_password(password, user.get('password_hash', '')):
                    return user
            return None

        except Exception as e:
            logger.error("Supabase authentication encountered a connection/query error.")
            st.error("Authentication service is temporarily unavailable.")
            return None

    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        if "@" in login_id:
            cur.execute("SELECT * FROM users WHERE username = ? OR email = ?", (login_id, login_id))
        else:
            cur.execute("SELECT * FROM users WHERE username = ?", (login_id,))
        row = cur.fetchone()
        conn.close()

        if row:
            user = dict(row)
            if verify_password(password, user.get('password_hash', '')):
                return user
        return None

    except Exception as e:
        logger.error("SQLite fallback authentication encountered a connection/query error.")
        st.error("Authentication service is temporarily unavailable.")
        return None

def sign_in_with_google(google_user_info):
    """Authenticates a user via Google OAuth by matching their verified email against the database."""
    if not google_user_info or not google_user_info.get("email"):
        logger.error("No email found in google_user_info")
        return None

    email = google_user_info["email"].strip()

    if DB_MODE == "supabase":
        try:
            supabase = get_supabase_client()
            response = supabase.table("users").select("*").eq("email", email).execute()
            if response.data:
                return response.data[0]

            return None
        except Exception as e:
            logger.error(f"Supabase sign_in_with_google error: {e}")
            return None

    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cur.fetchone()

        if row:
            conn.close()
            return dict(row)

        return None
    except Exception as e:
        logger.error(f"SQLite sign_in_with_google error: {e}")
        return None

def require_role(allowed_roles: list):
    if not st.session_state.get("user") or st.session_state.user.get("role") not in allowed_roles:
        st.error("Access denied")
        st.stop()

def init_rate_limit_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS failed_logins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to init rate limit db: {e}")

init_rate_limit_db()

from datetime import datetime, timedelta

def is_login_blocked(username: str) -> bool:
    if not username:
        return False
    if DB_MODE == "supabase":
        try:
            supabase = get_supabase_client()
            five_mins_ago = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
            res = supabase.table("failed_logins").select("id", count="exact").eq("username", username).gte("timestamp", five_mins_ago).execute()
            return res.count is not None and res.count >= 5
        except Exception:
            pass
            
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM failed_logins WHERE username = ? AND timestamp >= datetime('now', '-5 minutes')", (username,))
        count = cur.fetchone()[0]
        conn.close()
        return count >= 5
    except Exception:
        return False

def record_attempt(username: str):
    if not username:
        return
    if DB_MODE == "supabase":
        try:
            supabase = get_supabase_client()
            supabase.table("failed_logins").insert({"username": username}).execute()
            return
        except Exception:
            pass
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO failed_logins (username) VALUES (?)", (username,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def reset_attempts(username: str):
    if not username:
        return
    if DB_MODE == "supabase":
        try:
            supabase = get_supabase_client()
            supabase.table("failed_logins").delete().eq("username", username).execute()
            return
        except Exception:
            pass
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM failed_logins WHERE username = ?", (username,))
        conn.commit()
        conn.close()
    except Exception:
        pass
