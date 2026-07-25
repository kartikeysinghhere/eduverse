import os
import sqlite3
import bcrypt
from typing import Any
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
import streamlit as st
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env", override=True)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
DB_MODE = os.environ.get("DB_MODE", "supabase")

VALID_TABLES = {"users", "students", "grades", "marks", "attendance", "departments", "analytics_logs", "subjects", "teachers"}
VALID_FILTER_COLUMNS = {"student_id", "user_id", "username", "email", "role", "department", "id"}

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

@st.cache_resource
def get_supabase_service_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("Supabase URL and Service Role Key must be set in environment variables.")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')



@st.cache_data(ttl=60)
def _fetch_table_cached(table_name: str, filters_json: str | None, db_mode: str) -> list[Any]:
    if table_name not in VALID_TABLES:
        raise ValueError(f"Invalid table name: '{table_name}'. Allowed tables: {VALID_TABLES}")

    if filters_json:
        filters = json.loads(filters_json)
        for k in filters.keys():
            if k not in VALID_FILTER_COLUMNS:
                raise ValueError(f"Invalid filter column: '{k}'. Allowed columns: {VALID_FILTER_COLUMNS}")

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
        st.error("Database connection failed while fetching data.")
        return []

def fetch_table(table_name: str, filters: dict | None = None) -> list[Any]:
    increment_query_count()
    filters_json = json.dumps(filters, sort_keys=True) if filters else None
    return _fetch_table_cached(table_name, filters_json, DB_MODE)

def log_action(user_id: int, action: str) -> None:
    increment_query_count()
    
    if DB_MODE == "supabase" and SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase = get_supabase_client()
            supabase.table("analytics_logs").insert({
                "user_id": user_id,
                "action": action,
                "timestamp": datetime.now().isoformat()
            }).execute()
            return
        except Exception as e:
            print(f"Supabase logging error: {e}. Falling back to SQLite.")

    # SQLite (Fallback or Primary)
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

def seed_data():
    pass

def insert_records(table_name: str, records: list[Any]) -> bool:
    """Inserts a list of dictionary records into the specified table, supporting both Supabase and local SQLite."""
    increment_query_count()
    
    if DB_MODE == "supabase" and SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase = get_supabase_client()
            supabase.table(table_name).insert(records).execute()
            st.cache_data.clear()
            return True
        except Exception as e:
            print(f"Supabase insert error for {table_name}: {e}. Falling back to SQLite.")
            
    # SQLite (Fallback or Primary)
    try:
        conn = sqlite3.connect(str(ROOT / "eduverse.db"))
        cur = conn.cursor()
        
        if len(records) > 0:
            keys = list(records[0].keys())
            columns = ", ".join(keys)
            placeholders = ", ".join(["?"] * len(keys))
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            
            data_tuples = [tuple(r[k] for k in keys) for r in records]
            cur.executemany(query, data_tuples)
            
        conn.commit()
        conn.close()
        st.cache_data.clear()
        return True
    except Exception as e:
        print(f"SQLite insert error for {table_name}: {e}")
        return False
