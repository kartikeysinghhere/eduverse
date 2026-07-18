import os
import sqlite3
import pandas as pd
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def get_sqlite_schema(table_name):
    try:
        conn = sqlite3.connect(str(ROOT / "eduverse.db"))
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table_name})")
        rows = cur.fetchall()
        conn.close()
        # Returns a list of column names
        return sorted([row[1] for row in rows])
    except Exception as e:
        print(f"Error reading SQLite schema for {table_name}: {e}")
        return []

def get_supabase_schema(table_name, supabase):
    try:
        # Fetch 1 row to get keys
        res = supabase.table(table_name).select("*").limit(1).execute()
        if res.data:
            return sorted(list(res.data[0].keys()))
        else:
            # If empty, we can't easily get schema this way, but we assume it has data
            print(f"Warning: Supabase table {table_name} is empty, cannot verify schema automatically via data.")
            return []
    except Exception as e:
        print(f"Error reading Supabase schema for {table_name}: {e}")
        return []

def main():
    print("====================================================")
    print("      EduVerse Schema Sync Verification             ")
    print("====================================================")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("FAIL: SUPABASE_URL and SUPABASE_KEY are not configured.")
        return
        
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    tables_to_check = ["students", "grades"]
    all_passed = True
    
    for table in tables_to_check:
        print(f"\nChecking table: '{table}'")
        sqlite_cols = get_sqlite_schema(table)
        supabase_cols = get_supabase_schema(table, supabase)
        
        if not sqlite_cols:
            print(f"  [-] SQLite table '{table}' missing or error.")
            all_passed = False
            continue
            
        if not supabase_cols:
            print(f"  [-] Supabase table '{table}' missing, empty, or error.")
            all_passed = False
            continue
            
        print(f"  SQLite   Columns: {sqlite_cols}")
        print(f"  Supabase Columns: {supabase_cols}")
        
        if sqlite_cols == supabase_cols:
            print(f"  [+] PASS: Schemas match perfectly.")
        else:
            print(f"  [-] FAIL: Schemas do not match.")
            all_passed = False

    print("\n====================================================")
    if all_passed:
        print(" OVERALL RESULT: PASS (Ready for deployment)")
    else:
        print(" OVERALL RESULT: FAIL (Fix schema mismatches before deployment)")
    print("====================================================")

if __name__ == "__main__":
    main()
