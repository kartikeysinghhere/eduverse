import os
import sqlite3
import bcrypt
import logging
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path

# Configure secure logging
logger = logging.getLogger("eduverse.auth")
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

DB_MODE = os.environ.get("DB_MODE", "supabase")

# Maximum input lengths to prevent DoS attacks
MAX_USERNAME_LENGTH = 150
MAX_PASSWORD_LENGTH = 128

def get_db_connection():
    return sqlite3.connect(str(ROOT / "eduverse.db"))

def verify_password(password: str, hashed: str) -> bool:
    """Verifies a password against its bcrypt hash safely with input length safeguards."""
    if not password or not hashed:
        return False
        
    # Safeguard: Prevent CPU exhaustion from extremely long inputs
    if len(password) > MAX_PASSWORD_LENGTH:
        return False

    try:
        # bcrypt requires bytes for both arguments
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error("Password verification internal error occurred.")
        return False

def sign_in(username, password):
    """
    Authenticates a user securely against Supabase or SQLite.
    Fails closed in case of database or connection errors.
    """
    # 1. Input Sanitization & Validation Safeguards
    if not username or not password:
        return None
        
    if len(username) > MAX_USERNAME_LENGTH or len(password) > MAX_PASSWORD_LENGTH:
        logger.warning(f"Authentication rejected due to excessive input lengths.")
        return None

    # Strip whitespace to prevent formatting issues. The login field accepts
    # either the canonical username (admin/teacher) or the registered email.
    login_id = username.strip()

    # 2. Supabase Authentication Flow
    if DB_MODE == "supabase":
        try:
            from supabase import create_client
            URL = os.environ.get("SUPABASE_URL")
            KEY = os.environ.get("SUPABASE_KEY")
            
            if not URL or not KEY:
                logger.error("Supabase environment configuration missing.")
                return None
                
            supabase = create_client(URL, KEY)
            # Fetch user securely by username first, then by email. This keeps
            # existing admin/teacher logins stable while allowing email login.
            response = supabase.table("users").select("*").eq("username", login_id).execute()
            if not response.data and "@" in login_id:
                response = supabase.table("users").select("*").eq("email", login_id).execute()
            
            if response.data:
                user = response.data[0]
                if verify_password(password, user.get('password_hash', '')):
                    return user
            return None
            
        except Exception as e:
            # Safe logging: Log failure without leaking connection strings or tracebacks
            logger.error("Supabase authentication encountered a connection/query error.")
            return None

    # 3. SQLite Fallback Flow
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Safe Parametrized Query
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
        return None

def sign_in_with_google(google_user_info):
    """
    Checks if email exists in users table.
    If yes, returns the existing user.
    If no, returns None (no auto-creation).
    """
    if not google_user_info or not google_user_info.get("email"):
        logger.error("No email found in google_user_info")
        return None
        
    email = google_user_info["email"].strip()
    
    # 1. Supabase Mode
    if DB_MODE == "supabase":
        try:
            from supabase import create_client
            URL = os.environ.get("SUPABASE_URL")
            KEY = os.environ.get("SUPABASE_KEY")
            
            if not URL or not KEY:
                logger.error("Supabase environment configuration missing.")
                return None
                
            supabase = create_client(URL, KEY)
            # Check if email exists
            response = supabase.table("users").select("*").eq("email", email).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Supabase sign_in_with_google error: {e}")
            return None
            
    # 2. SQLite Fallback Flow
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Check by email
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error(f"SQLite sign_in_with_google error: {e}")
        return None

def require_role(allowed_roles: list):
    if not st.session_state.get("user") or st.session_state.user.get("role") not in allowed_roles:
        st.error("Access denied")
        st.stop()
