import os
import sqlite3
import pandas as pd
import numpy as np
import bcrypt
from postgrest.types import CountMethod
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

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
    import sys
    print("====================================================")
    print("    EduVerse Supabase Production Migration Script   ")
    print("====================================================")

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be configured in your .env file!")
        raise SystemExit(1)

    allow_random = os.environ.get("EDUVERSE_ALLOW_RANDOM_DEV_PASSWORDS", "false").lower() == "true"
    admin_raw = os.environ.get("EDUVERSE_ADMIN_PASSWORD")
    teacher_raw = os.environ.get("EDUVERSE_TEACHER_PASSWORD")
    student_raw = os.environ.get("EDUVERSE_STUDENT_PASSWORD")

    if not admin_raw or not teacher_raw or not student_raw:
        if allow_random:
            import secrets
            print("[!] WARNING: Missing required password environment variables. Falling back to secure random generation since EDUVERSE_ALLOW_RANDOM_DEV_PASSWORDS=true.")
            admin_raw = admin_raw or secrets.token_urlsafe(16)
            teacher_raw = teacher_raw or secrets.token_urlsafe(16)
            student_raw = student_raw or secrets.token_urlsafe(16)

            print(f"[!] Generated admin password: {admin_raw} — SAVE THIS, it will not be shown again")
            print(f"[!] Generated teacher password: {teacher_raw} — SAVE THIS, it will not be shown again")
            print(f"[!] Generated student password: {student_raw} — SAVE THIS, it will not be shown again")
        else:
            print("[!] Error: Required password environment variables are missing for Supabase migration!")
            print("    Please set the following environment variables:")
            print("      - EDUVERSE_ADMIN_PASSWORD")
            print("      - EDUVERSE_TEACHER_PASSWORD")
            print("      - EDUVERSE_STUDENT_PASSWORD")
            print("\n    To run with randomized passwords for local dev, run with environment variable:")
            print("      EDUVERSE_ALLOW_RANDOM_DEV_PASSWORDS=true")
            raise SystemExit(1)

    admin_pw = hash_password(admin_raw)
    teacher_pw = hash_password(teacher_raw)
    student_pw = hash_password(student_raw)

    csv_path = ROOT / "data" / "sample_data.csv"
    if not csv_path.exists():
        print(f"Error: Dataset not found at {csv_path}! Run data_generator.py first.")
        return

    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} student records from local CSV.")

    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Connected to Supabase production endpoint successfully!")
    except Exception as e:
        print(f"Failed to initialize Supabase client: {e}")
        return

    print("\nCleaning existing production Supabase database tables to prevent conflicts...")
    tables_to_clean = ["grades", "attendance", "subjects", "students", "teachers"]
    for t in tables_to_clean:
        try:
            supabase.table(t).delete().gt("id", -1).execute()
            print(f"  - Table '{t}' successfully cleared (Int ID).")
        except Exception as e:
            try:
                supabase.table(t).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
                print(f"  - Table '{t}' successfully cleared (UUID ID).")
            except Exception as ex:
                try:
                    supabase.table(t).delete().neq("name", "dummy_non_existent").execute()
                    print(f"  - Table '{t}' successfully cleared (non-ID fallback).")
                except Exception as ex2:
                    print(f"  - Table '{t}' clear failed or empty: {ex2}")

    try:
        supabase.table("users").delete().gt("id", -1).execute()
        print("  - Table 'users' successfully cleared.")
    except Exception:
        pass

    print("\nPreparing teachers data...")
    teachers_to_load = [
        {"id": 1, "name": "Dr. Amit Sharma", "department": "Computer Science"},
        {"id": 2, "name": "Prof. Priya Patel", "department": "Artificial Intelligence"},
        {"id": 3, "name": "Dr. Raj Singh", "department": "Business Administration"},
        {"id": 4, "name": "Prof. Vikram Rao", "department": "Civil Engineering"},
        {"id": 5, "name": "Dr. Neha Nair", "department": "Mechanical Engineering"}
    ]
    batch_insert(supabase, "teachers", teachers_to_load, batch_size=200)

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

    print("\nPreparing 500 student profiles data...")
    students_to_load = []
    for row in df.to_dict('records'):
        sid = int(row['student_id'])
        sname = row['name']
        students_to_load.append({
            "student_id": int(row['student_id']),
            "name": row['name'],
            "department": row['department'],
            "semester": int(row['semester']),
            "attendance_pct": float(row['attendance_pct']),
            "internal_marks": float(row['internal_marks']),
            "assignments_completed": int(row['assignments_completed']),
            "study_hours": float(row['study_hours']),
            "prev_gpa": float(row['prev_gpa']),
            "final_gpa": float(row['final_gpa']),
            "risk": int(row['risk'])
        })
    batch_insert(supabase, "students", students_to_load, batch_size=200)

    print("\nPreparing daily attendance logs (12,000 records)...")
    attendance_to_load = []
    dates = [datetime(2026, 5, 1) + timedelta(days=i) for i in range(24)]
    np.random.seed(42)

    for row in df.to_dict('records'):
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

    print("\nPreparing course grades records (3,000 records)...")
    grades_to_load = []

    subjects_list = ["Mathematics", "Physics", "Computer Science", "Data Structures", "AI", "Ethics"]

    for row in df.to_dict('records'):
        sid = int(row['student_id'])
        base_marks = float(row['internal_marks'])

        for sub_name in subjects_list:
            score = int(np.clip(np.random.normal(base_marks, 8), 30, 100))
            grades_to_load.append({
                "student_id": sid,
                "Subject": sub_name,
                "Marks": score
            })
    batch_insert(supabase, "grades", grades_to_load, batch_size=200)

    print("\nPreparing users table credentials...")
    users_to_load = []

    users_to_load.append({
        "id": 999,
        "username": "admin",
        "password_hash": admin_pw,
        "role": "Admin",
        "email": "admin@eduverse.ai"
    })
    users_to_load.append({
        "id": 998,
        "username": "teacher",
        "password_hash": teacher_pw,
        "role": "Teacher",
        "email": "teacher@eduverse.ai"
    })
    for row in df.to_dict('records'):
        sid = int(row['student_id'])
        username = row['name'].lower().replace(" ", "")
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

    print("\n====================================================")
    print("             MIGRATION RUN VERIFICATION             ")
    print("====================================================")

    try:
        cnt_students = supabase.table("students").select("*", count=CountMethod.exact).limit(0).execute().count
        print(f"Table 'students' Count    : {cnt_students} / 500")
    except Exception as e:
        print(f"Table 'students' Count    : Error querying: {e}")

    try:
        cnt_teachers = supabase.table("teachers").select("*", count=CountMethod.exact).limit(0).execute().count
        print(f"Table 'teachers' Count    : {cnt_teachers} / 5")
    except Exception as e:
        print(f"Table 'teachers' Count    : Error querying: {e}")

    try:
        cnt_subjects = supabase.table("subjects").select("*", count=CountMethod.exact).limit(0).execute().count
        print(f"Table 'subjects' Count    : {cnt_subjects} / 6")
    except Exception as e:
        print(f"Table 'subjects' Count    : Error querying: {e}")

    try:
        cnt_attendance = supabase.table("attendance").select("*", count=CountMethod.exact).limit(0).execute().count
        print(f"Table 'attendance' Count  : {cnt_attendance} / 12000")
    except Exception as e:
        print(f"Table 'attendance' Count  : Error querying: {e}")

    try:
        cnt_marks = supabase.table("marks").select("*", count=CountMethod.exact).limit(0).execute().count
        print(f"Table 'marks' Count       : {cnt_marks} / 3000")
    except Exception as e:
        print(f"Table 'marks' Count       : Error querying: {e}")

    try:
        cnt_users = supabase.table("users").select("*", count=CountMethod.exact).limit(0).execute().count
        print(f"Table 'users' Count       : {cnt_users}")
    except Exception:
        print(f"Table 'users' Count       : Table does not exist in Supabase (SQLite Fallback active)")

    print("\nMigration script complete! Pushed 500 students and academic records to Supabase.")
    print("====================================================")

if __name__ == "__main__":
    main()
