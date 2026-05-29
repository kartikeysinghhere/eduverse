import os
import sqlite3
import bcrypt
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
import streamlit as st
import json
from pathlib import Path

# Resolve absolute root dynamically
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
DB_MODE = os.environ.get("DB_MODE", "supabase")

def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase URL and Key must be set in environment variables.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# Auth helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def sign_in(username, password):
    # Dynamic routing for auth
    if DB_MODE == "supabase" and SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase = get_supabase_client()
            response = supabase.table("users").select("*").eq("username", username).execute()
            if response.data:
                user = response.data[0]
                if verify_password(password, user['password_hash']):
                    return user
        except Exception as e:
            print(f"Supabase auth error: {e}. Falling back to SQLite.")
            
    # Fallback to local SQLite
    try:
        conn = sqlite3.connect(str(ROOT / "eduverse.db"))
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

# Internal cached fetcher with hashable arguments
@st.cache_data(ttl=60)
def _fetch_table_cached(table_name, filters_json, db_mode):
    filters = json.loads(filters_json) if filters_json else None
    
    # 1. Supabase Mode
    if db_mode == "supabase" and SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase = get_supabase_client()
            query = supabase.table(table_name).select("*")
            if filters:
                for k, v in filters.items():
                    query = query.eq(k, v)
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Supabase fetch failed for {table_name}: {e}. Trying local SQLite.")
            
    # 2. SQLite Mode (Primary or Fallback)
    try:
        conn = sqlite3.connect(str(ROOT / "eduverse.db"))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        query = f"SELECT * FROM {table_name}"
        params = []
        
        if filters:
            where_clauses = []
            for k, v in filters.items():
                where_clauses.append(f"{k} = ?")
                params.append(v)
            query += " WHERE " + " AND ".join(where_clauses)
            
        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"SQLite fetch error for {table_name}: {e}")
        return []

# Public interface for general data fetching
def fetch_table(table_name, filters=None):
    # Convert filters to a JSON string to make them hashable for st.cache_data
    filters_json = json.dumps(filters, sort_keys=True) if filters else None
    return _fetch_table_cached(table_name, filters_json, DB_MODE)

# Logging (Non-blocking background-style execution in case of Supabase offline)
def log_action(user_id, action):
    # Write to local SQLite first to ensure audit trail is preserved
    try:
        conn = sqlite3.connect(str(ROOT / "eduverse.db"))
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO analytics_logs (user_id, action, timestamp)
        VALUES (?, ?, ?)
        """, (user_id, action, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQLite logging error: {e}")

    # Write to Supabase asynchronously / with try-except to avoid blocking UI
    if DB_MODE == "supabase" and SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase = get_supabase_client()
            supabase.table("analytics_logs").insert({
                "user_id": user_id,
                "action": action,
                "timestamp": datetime.now().isoformat()
            }).execute()
        except Exception as e:
            print(f"Supabase logging error: {e}")

def seed_data():
    pass
