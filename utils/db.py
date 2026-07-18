import os
import sqlite3
import bcrypt
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
import streamlit as st
import json
from pathlib import Path
import time

# Resolve absolute root dynamically
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env", override=True)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
DB_MODE = os.environ.get("DB_MODE", "supabase")

# Whitelist of allowed table and column names to prevent SQL injection
VALID_TABLES = {"users", "students", "grades", "marks", "attendance", "departments", "analytics_logs", "subjects", "teachers"}
VALID_FILTER_COLUMNS = {"student_id", "user_id", "username", "email", "role", "department", "id"}

# Initialize global tracking variables in system/module namespace
if "APP_START_TIME" not in globals():
    globals()["APP_START_TIME"] = time.time()

if "QUERY_COUNTER" not in globals():
    globals()["QUERY_COUNTER"] = 0

def get_uptime_seconds() -> float:
    return time.time() - globals().get("APP_START_TIME", time.time())

def get_query_count() -> int:
    return globals().get("QUERY_COUNTER", 0)

def increment_query_count():
    globals()["QUERY_COUNTER"] = globals().get("QUERY_COUNTER", 0) + 1

@st.cache_data(ttl=15)
def get_db_latency() -> float:
    start = time.perf_counter()
    try:
        if DB_MODE == "supabase" and SUPABASE_URL and SUPABASE_KEY:
            supabase = get_supabase_client()
            supabase.table("users").select("id").limit(1).execute()
        else:
            conn = sqlite3.connect(str(ROOT / "eduverse.db"))
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            conn.close()
    except Exception:
        pass
    return (time.perf_counter() - start) * 1000.0

@st.cache_resource
def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase URL and Key must be set in environment variables.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# Auth helper functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')



# Internal cached fetcher with hashable arguments
@st.cache_data(ttl=60)
def _fetch_table_cached(table_name, filters_json, db_mode):
    # Validate table name against whitelist to prevent SQL injection
    if table_name not in VALID_TABLES:
        raise ValueError(f"Invalid table name: '{table_name}'. Allowed tables: {VALID_TABLES}")

    # Validate filter column names against whitelist
    if filters_json:
        filters = json.loads(filters_json)
        for k in filters.keys():
            if k not in VALID_FILTER_COLUMNS:
                raise ValueError(f"Invalid filter column: '{k}'. Allowed columns: {VALID_FILTER_COLUMNS}")

    # This represents a query invocation hitting the DB (uncached/expired)
    # Return directly from Supabase or SQLite
    if db_mode == "supabase" and SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase = get_supabase_client()
            query = supabase.table(table_name).select("*")
            if filters_json:
                filters = json.loads(filters_json)
                for k, v in filters.items():
                    query = query.eq(k, v)
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Supabase fetch failed for {table_name}: {e}. Trying local SQLite.")
            
    try:
        conn = sqlite3.connect(str(ROOT / "eduverse.db"))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # table_name and column names are validated against whitelists above
        query = f"SELECT * FROM {table_name}"
        params = []
        
        if filters_json:
            filters = json.loads(filters_json)
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
    increment_query_count()
    # Convert filters to a JSON string to make them hashable for st.cache_data
    filters_json = json.dumps(filters, sort_keys=True) if filters else None
    return _fetch_table_cached(table_name, filters_json, DB_MODE)

# Logging (Non-blocking background-style execution in case of Supabase offline)
def log_action(user_id, action):
    increment_query_count()
    # Write to local SQLite only if not in Supabase mode (avoids ephemeral filesystem issues in production)
    if DB_MODE != "supabase":
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
        increment_query_count()
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
