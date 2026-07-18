import sqlite3
import pandas as pd
import numpy as np
import bcrypt
import os
from datetime import datetime, timedelta
from pathlib import Path

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def main():
    import sys
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
            print("[!] Error: Required password environment variables are missing!")
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

    ROOT = Path(__file__).resolve().parent
    db_path = str(ROOT / "eduverse.db")
    csv_path = str(ROOT / "data" / "sample_data.csv")
    
    print(f"Seeding SQLite database at: {db_path}")
    print(f"Reading student data from: {csv_path}")
    
    if not os.path.exists(csv_path):
        print("Error: sample_data.csv not found!")
        return
        
    df = pd.read_csv(csv_path)
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # 1. Drop existing tables if they exist
    tables = ["users", "students", "grades", "attendance", "departments", "analytics_logs"]
    
    import sys
    if "--force" not in sys.argv:
        print(f"\nWARNING: This will DROP the following tables: {', '.join(tables)}")
        confirm = input("Type 'yes' to proceed: ")
        if confirm.strip().lower() != "yes":
            print("Aborting database seed.")
            return

    for t in tables:
        cur.execute(f"DROP TABLE IF EXISTS {t}")
        
    # 2. Create tables
    cur.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        email TEXT NOT NULL
    )
    """)
    
    cur.execute("""
    CREATE TABLE students (
        student_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        semester INTEGER NOT NULL,
        attendance_pct REAL NOT NULL,
        internal_marks REAL NOT NULL,
        assignments_completed INTEGER NOT NULL,
        study_hours REAL NOT NULL,
        prev_gpa REAL NOT NULL,
        final_gpa REAL NOT NULL,
        risk INTEGER NOT NULL
    )
    """)
    
    cur.execute("""
    CREATE TABLE grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        Subject TEXT NOT NULL,
        Marks INTEGER NOT NULL,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    )
    """)
    
    cur.execute("""
    CREATE TABLE attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        Date TEXT NOT NULL,
        Status TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    )
    """)
    
    cur.execute("""
    CREATE TABLE departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        avg_gpa REAL NOT NULL,
        total_students INTEGER NOT NULL
    )
    """)
    
    cur.execute("""
    CREATE TABLE analytics_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    """)
    
    print("Tables created successfully.")
    
    # 3. Seed Users
    # Hashed passwords (pre-validated and hashed at start)
    
    # Standard Admin (using high ID to avoid student conflicts)
    cur.execute("INSERT INTO users (id, username, password_hash, role, email) VALUES (?, ?, ?, ?, ?)",
                (999, "admin", admin_pw, "Admin", "admin@eduverse.ai"))
                
    # Standard Teacher (using high ID to avoid student conflicts)
    cur.execute("INSERT INTO users (id, username, password_hash, role, email) VALUES (?, ?, ?, ?, ?)",
                (998, "teacher", teacher_pw, "Teacher", "teacher@eduverse.ai"))
                
    # Standard Student (maps to student_id 1 Aarav Sharma)
    cur.execute("INSERT INTO users (id, username, password_hash, role, email) VALUES (?, ?, ?, ?, ?)",
                (1, "student", student_pw, "Student", "student@eduverse.ai"))
                
    # Seed other students as users so they can log in using their lowercase name!
    for _, row in df.iterrows():
        sid = int(row['student_id'])
        if sid == 1:
            continue # already added as "student"
            
        username = row['name'].lower().replace(" ", "")
        email = f"{username}@eduverse.ai"
        cur.execute("INSERT INTO users (id, username, password_hash, role, email) VALUES (?, ?, ?, ?, ?)",
                    (sid, username, student_pw, "Student", email))
                    
    print("Users seeded successfully.")
    
    # 4. Seed Students
    for _, row in df.iterrows():
        cur.execute("""
        INSERT INTO students (student_id, name, department, semester, attendance_pct, internal_marks, assignments_completed, study_hours, prev_gpa, final_gpa, risk)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (int(row['student_id']), row['name'], row['department'], int(row['semester']), 
              float(row['attendance_pct']), float(row['internal_marks']), int(row['assignments_completed']), float(row['study_hours']),
              float(row['prev_gpa']), float(row['final_gpa']), int(row['risk'])))
              
    print("Students seeded successfully.")
    
    # 5. Seed Grades
    # We will generate realistic subject marks centered around student's internal marks
    subjects = ['Mathematics', 'Physics', 'Computer Science', 'Data Structures', 'AI', 'Ethics']
    np.random.seed(42)
    
    for _, row in df.iterrows():
        sid = int(row['student_id'])
        base_marks = float(row['internal_marks'])
        
        for sub in subjects:
            marks = int(np.clip(np.random.normal(base_marks, 8), 30, 100))
            cur.execute("INSERT INTO grades (student_id, Subject, Marks) VALUES (?, ?, ?)",
                        (sid, sub, marks))
                        
    print("Grades seeded successfully.")
    
    # 6. Seed Attendance
    dates = [datetime(2026, 5, 1) + timedelta(days=i) for i in range(24)]
    
    for _, row in df.iterrows():
        sid = int(row['student_id'])
        pct = float(row['attendance_pct']) / 100.0
        
        statuses = np.random.choice(['Present', 'Absent'], size=24, p=[pct, 1 - pct])
        
        for d, status in zip(dates, statuses):
            cur.execute("INSERT INTO attendance (student_id, Date, Status) VALUES (?, ?, ?)",
                        (sid, d.strftime('%Y-%m-%d'), status))
                        
    print("Attendance seeded successfully.")
    
    # 7. Seed Departments
    dept_stats = df.groupby('department').agg(
        avg_gpa=('final_gpa', 'mean'),
        total_students=('student_id', 'count')
    ).reset_index()
    
    for _, row in dept_stats.iterrows():
        cur.execute("INSERT INTO departments (name, avg_gpa, total_students) VALUES (?, ?, ?)",
                    (row['department'], round(float(row['avg_gpa']), 2), int(row['total_students'])))
                    
    print("Departments seeded successfully.")
    
    conn.commit()
    conn.close()
    print("SQLite database seeding complete!")

if __name__ == "__main__":
    main()
