import os
import sqlite3
import bcrypt
import logging
from dotenv import load_dotenv
from pathlib import Path

# Configure secure logging
logger = logging.getLogger("eduverse.auth")
logging.basicConfig(level=logging.INFO)

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

    # Strip whitespace to prevent formatting issues
    username = username.strip()

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
            # Fetch user securely
            response = supabase.table("users").select("*").eq("username", username).execute()
            
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
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
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