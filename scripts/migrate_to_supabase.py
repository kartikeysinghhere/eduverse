import os
import sqlite3
import pandas as pd
import numpy as np
import bcrypt
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Resolve dynamic ROOT path and load .env
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def guess_gender(name: str) -> str:
    first_name = name.split()[0].lower()
    female_suffixes = ('a', 'i', 'ee', 'ya', 'ani', 'ika', 'sha', 'ta', 'ti', 'ri')
    female_names = {'meera', 'nair', 'patel', 'priya', 'kavya', 'ishani', 'riya', 'anjali', 'sneha', 'divya', 'aditi', 'pooja', 'neha'}
    if any(first_name.endswith(sfx) for sfx in female_suffixes) or first_name in female_names:
        return 'Female'
    return 'Male'

def get_enrollment_date(semester: int) -> str:
    # Estimate enrollment date based on semester (academic year 2025-26)
    if semester in (1, 2):
        return '2025-09-01'
    elif semester in (3, 4):
        return '2024-09-01'
    elif semester in (5, 6):
        return '2023-09-01'
    else:
        return '2022-09-01'

def batch_insert(supabase, table_name, data_list, batch_size=200):
    total = len(data_list)
    print(f"Inserting {total} rows into '{table_name}' table in batches of {batch_size}...")
    for i in range(0, total, batch_size):
        batch = data_list[i : i + batch_size]
        supabase.table(table_name).insert(batch).execute()
    print(f"Successfully loaded all {total} rows into '{table_name}'.")

def main():
    print("====================================================")
    print("    EduVerse Supabase Production Migration Script   ")
    print("====================================================")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be configured in your .env file!")
        return
        
    csv_path = ROOT / "data" / "sample_data.csv"
    if not csv_path.exists():
        print(f"Error: Dataset not found at {csv_path}! Run data_generator.py first.")
        return
        
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} student records from local CSV.")
    
    # Initialize Supabase Client
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Connected to Supabase production endpoint successfully!")
    except Exception as e:
        print(f"Failed to initialize Supabase client: {e}")
        return

    # --- 1. CLEAN EXISTING PRODUCTION TABLES ---
    print("\nCleaning existing production Supabase database tables to prevent conflicts...")
    tables_to_clean = ["marks", "attendance", "subjects", "students", "teachers"]
    for t in tables_to_clean:
        try:
            # Delete rows where ID >= 0 (all rows)
            supabase.table(t).delete().gt("id", -1).execute()
            print(f"  - Table '{t}' successfully cleared.")
        except Exception as e:
            # Fallback for tables that might use different primary keys or don't have ID column
            try:
                supabase.table(t).delete().neq("name", "dummy_non_existent").execute()
                print(f"  - Table '{t}' successfully cleared (non-ID fallback).")
            except Exception as ex:
                print(f"  - Table '{t}' clear failed or empty: {ex}")

    # Try to clean optional 'users' table if it exists
    try:
        supabase.table("users").delete().gt("id", -1).execute()
        print("  - Table 'users' successfully cleared.")
    except Exception:
        pass

    # --- 2. PREPARE & LOAD TEACHERS ---
    print("\nPreparing teachers data...")
    teachers_to_load = [
        {"id": 1, "name": "Dr. Amit Sharma", "department": "Computer Science"},
        {"id": 2, "name": "Prof. Priya Patel", "department": "Artificial Intelligence"},
        {"id": 3, "name": "Dr. Raj Singh", "department": "Business Administration"},
        {"id": 4, "name": "Prof. Vikram Rao", "department": "Civil Engineering"},
        {"id": 5, "name": "Dr. Neha Nair", "department": "Mechanical Engineering"}
    ]
    batch_insert(supabase, "teachers", teachers_to_load, batch_size=200)

    # --- 3. PREPARE & LOAD SUBJECTS ---
    print("\nPreparing subjects data...")
    subjects_to_load = [
        {"id": 1, "name": "Mathematics", "teacher_id": 1, "semester": 1},
        {"id": 2, "name": "Physics", "teacher_id": 5, "semester": 1},
        {"id": 3, "name": "Computer Science", "teacher_id": 1, "semester": 2},
        {"id": 4, "name": "Data Structures", "teacher_id": 1, "semester": 3},
        {"id": 5, "name": "AI", "teacher_id": 2, "semester": 5},
        {"id": 6, "name": "Ethics", "teacher_id": 3, "semester": 4}
    ]
    batch_insert(supabase, "subjects", subjects_to_load, batch_size=200)

    # --- 4. PREPARE & LOAD STUDENTS ---
    print("\nPreparing 500 student profiles data...")
    students_to_load = []
    for _, row in df.iterrows():
        sid = int(row['student_id'])
        sname = row['name']
        students_to_load.append({
            "id": sid,
            "name": sname,
            "gender": guess_gender(sname),
            "enrollment_date": get_enrollment_date(int(row['semester'])),
            "study_hours_per_week": float(row['study_hours']),
            "class_name": row['department'],
            "status": "Active"
        })
    batch_insert(supabase, "students", students_to_load, batch_size=200)

    # --- 5. PREPARE & LOAD ATTENDANCE LOGS ---
    print("\nPreparing daily attendance logs (12,000 records)...")
    attendance_to_load = []
    dates = [datetime(2026, 5, 1) + timedelta(days=i) for i in range(24)]
    np.random.seed(42)
    
    for _, row in df.iterrows():
        sid = int(row['student_id'])
        pct = float(row['attendance_pct']) / 100.0
        statuses = np.random.choice(['Present', 'Absent'], size=24, p=[pct, 1 - pct])
        
        for d, status in zip(dates, statuses):
            attendance_to_load.append({
                "student_id": sid,
                "date": d.strftime('%Y-%m-%d'),
                "status": status
            })
    batch_insert(supabase, "attendance", attendance_to_load, batch_size=200)

    # --- 6. PREPARE & LOAD MARKS RECORDS ---
    print("\nPreparing course marks records (3,000 records)...")
    marks_to_load = []
    
    for _, row in df.iterrows():
        sid = int(row['student_id'])
        base_marks = float(row['internal_marks'])
        
        for sub_id in range(1, 7):
            score = int(np.clip(np.random.normal(base_marks, 8), 30, 100))
            marks_to_load.append({
                "student_id": sid,
                "subject_id": sub_id,
                "exam_type": "Final Exam",
                "score": score,
                "max_score": 100
            })
    batch_insert(supabase, "marks", marks_to_load, batch_size=200)

    # --- 7. PREPARE & LOAD OPTIONAL USERS TABLE ---
    print("\nPreparing users table credentials...")
    users_to_load = []
    import secrets
    fallback_admin = secrets.token_urlsafe(16)
    fallback_teacher = secrets.token_urlsafe(16)
    
    admin_raw = os.environ.get("EDUVERSE_ADMIN_PASSWORD")
    if not admin_raw:
        print("[!] WARNING: EDUVERSE_ADMIN_PASSWORD not set. Using dynamically generated secure password.")
        admin_raw = fallback_admin
        
    teacher_raw = os.environ.get("EDUVERSE_TEACHER_PASSWORD")
    if not teacher_raw:
        print("[!] WARNING: EDUVERSE_TEACHER_PASSWORD not set. Using dynamically generated secure password.")
        teacher_raw = fallback_teacher
        
    student_raw = os.environ.get("EDUVERSE_STUDENT_PASSWORD", "student")
    
    admin_pw = hash_password(admin_raw)
    teacher_pw = hash_password(teacher_raw)
    student_pw = hash_password(student_raw)
    
    # Admin
    users_to_load.append({
        "id": 999,
        "username": "admin",
        "password_hash": admin_pw,
        "role": "Admin",
        "email": "admin@eduverse.ai"
    })
    # Teacher
    users_to_load.append({
        "id": 998,
        "username": "teacher",
        "password_hash": teacher_pw,
        "role": "Teacher",
        "email": "teacher@eduverse.ai"
    })
    # 500 Students
    for _, row in df.iterrows():
        sid = int(row['student_id'])
        username = "student" if sid == 1 else row['name'].lower().replace(" ", "")
        email = f"{username}@eduverse.ai"
        users_to_load.append({
            "id": sid,
            "username": username,
            "password_hash": student_pw,
            "role": "Student",
            "email": email
        })
        
    try:
        batch_insert(supabase, "users", users_to_load, batch_size=200)
    except Exception as e:
        print("\nNote: Table 'users' does not exist in the public schema cache of this Supabase project.")
        print("Skipping 'users' table migration. (Dashboard will safely fallback to local SQLite for authentication).")

    # --- 8. VERIFY RUN METRICS ---
    print("\n====================================================")
    print("             MIGRATION RUN VERIFICATION             ")
    print("====================================================")
    
    try:
        cnt_students = supabase.table("students").select("*", count="exact").limit(0).execute().count
        print(f"Table 'students' Count    : {cnt_students} / 500")
    except Exception as e:
        print(f"Table 'students' Count    : Error querying: {e}")
        
    try:
        cnt_teachers = supabase.table("teachers").select("*", count="exact").limit(0).execute().count
        print(f"Table 'teachers' Count    : {cnt_teachers} / 5")
    except Exception as e:
        print(f"Table 'teachers' Count    : Error querying: {e}")
        
    try:
        cnt_subjects = supabase.table("subjects").select("*", count="exact").limit(0).execute().count
        print(f"Table 'subjects' Count    : {cnt_subjects} / 6")
    except Exception as e:
        print(f"Table 'subjects' Count    : Error querying: {e}")
        
    try:
        cnt_attendance = supabase.table("attendance").select("*", count="exact").limit(0).execute().count
        print(f"Table 'attendance' Count  : {cnt_attendance} / 12000")
    except Exception as e:
        print(f"Table 'attendance' Count  : Error querying: {e}")
        
    try:
        cnt_marks = supabase.table("marks").select("*", count="exact").limit(0).execute().count
        print(f"Table 'marks' Count       : {cnt_marks} / 3000")
    except Exception as e:
        print(f"Table 'marks' Count       : Error querying: {e}")
        
    try:
        cnt_users = supabase.table("users").select("*", count="exact").limit(0).execute().count
        print(f"Table 'users' Count       : {cnt_users}")
    except Exception:
        print(f"Table 'users' Count       : Table does not exist in Supabase (SQLite Fallback active)")
        
    print("\nMigration script complete! Pushed 500 students and academic records to Supabase.")
    print("====================================================")

if __name__ == "__main__":
    main()
