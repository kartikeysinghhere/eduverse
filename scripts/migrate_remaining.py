import os
import time
import pandas as pd
import numpy as np
import datetime
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

# Load environment configuration
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

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

def main():
    print("====================================================")
    print("      EduVerse Remaining 400 Students Seeder        ")
    print("====================================================")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_KEY are not configured!")
        return
        
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # ------------------------------------------------------
    # STEP 1: Check how many students exist
    # ------------------------------------------------------
    print("Step 1: Checking current students count...")
    res = supabase.table("students").select("id", count="exact").execute()
    current_count = res.count
    print(f"Current student count in Supabase: {current_count}")
    
    # Reset extra students if already seeded (ensuring exactly the starting 100 students exist)
    if current_count > 100:
        print(f"Found {current_count} students. Safely resetting extra students (id > 100) to starting state...")
        try:
            supabase.table("marks").delete().gt("student_id", 100).execute()
            supabase.table("attendance").delete().gt("student_id", 100).execute()
            supabase.table("students").delete().gt("id", 100).execute()
            
            # Re-verify count
            res = supabase.table("students").select("id", count="exact").execute()
            current_count = res.count
            print(f"Reset complete. Student count is now exactly: {current_count}")
        except Exception as e:
            print(f"Error during state reset: {e}")
            return
            
    # ------------------------------------------------------
    # STEP 2: Read sample_data.csv and load 400 remaining rows
    # ------------------------------------------------------
    print("\nStep 2: Loading dataset and skipping first 100 students...")
    csv_path = ROOT / "data" / "sample_data.csv"
    if not csv_path.exists():
        print(f"Error: sample_data.csv not found at {csv_path}!")
        return
        
    df = pd.read_csv(csv_path)
    # Skip the first 100 rows, take rows 100 to 499 (index-based 100 to 500)
    df_400 = df.iloc[100:500]
    print(f"Successfully prepared {len(df_400)} student records from CSV (IDs 101 to 500).")
    
    # ------------------------------------------------------
    # STEP 3: Insert 400 students in batches of 50
    # ------------------------------------------------------
    print("\nStep 3: Inserting 400 students in batches of 50...")
    students_list = []
    for _, row in df_400.iterrows():
        sid = int(row['student_id'])
        sname = row['name']
        students_list.append({
            "id": sid,
            "name": sname,
            "gender": guess_gender(sname),
            "enrollment_date": get_enrollment_date(int(row['semester'])),
            "study_hours_per_week": float(row['study_hours']),
            "class_name": row['department'],
            "status": "Active"
        })
        
    batch_size = 50
    total_inserted = 100  # Starts with the pre-existing 100 students
    
    for i in range(0, len(students_list), batch_size):
        batch = students_list[i : i + batch_size]
        supabase.table("students").insert(batch).execute()
        total_inserted += len(batch)
        print(f"Inserted batch {i // batch_size + 1} — total so far: {total_inserted}")
        time.sleep(1.0)
        
    print("All 400 new students successfully inserted.")

    # ------------------------------------------------------
    # STEP 4: Generate & Insert Weekday Attendance
    # ------------------------------------------------------
    print("\nStep 4: Generating and inserting 60 weekday attendance logs per new student...")
    # Generate 60 weekdays starting from March 2, 2026 (a Monday)
    start_date = datetime.date(2026, 3, 2)
    dates = []
    curr = start_date
    while len(dates) < 60:
        if curr.weekday() < 5:  # 0 = Monday, ..., 4 = Friday
            dates.append(curr.strftime('%Y-%m-%d'))
        curr += datetime.timedelta(days=1)
        
    attendance_records = []
    np.random.seed(42)
    
    for _, row in df_400.iterrows():
        sid = int(row['student_id'])
        # 80% Present, 12% Absent, 8% Late
        statuses = np.random.choice(['Present', 'Absent', 'Late'], size=60, p=[0.80, 0.12, 0.08])
        for d, status in zip(dates, statuses):
            attendance_records.append({
                "student_id": sid,
                "date": d,
                "status": status
            })
            
    print(f"Total attendance records generated: {len(attendance_records)}")
    
    # Batch insert in chunks of 300
    att_batch_size = 300
    for i in range(0, len(attendance_records), att_batch_size):
        batch = attendance_records[i : i + att_batch_size]
        supabase.table("attendance").insert(batch).execute()
        if (i + att_batch_size) % 3000 == 0 or (i + len(batch)) == len(attendance_records):
            print(f"  Pushed {i + len(batch)} / {len(attendance_records)} attendance logs...")
            
    print("Attendance migration successfully completed.")

    # ------------------------------------------------------
    # STEP 5: Generate & Insert Marks Records
    # ------------------------------------------------------
    print("\nStep 5: Generating and inserting marks for the 400 new students...")
    # Get subject IDs
    res_subjects = supabase.table("subjects").select("id").execute()
    subject_ids = [row['id'] for row in res_subjects.data]
    print(f"Found active subjects: {subject_ids}")
    
    marks_records = []
    
    for _, row in df_400.iterrows():
        sid = int(row['student_id'])
        base_marks = float(row['internal_marks'])
        
        for sub_id in subject_ids:
            for exam in ["Midterm", "Final"]:
                score = int(np.clip(np.random.normal(base_marks, 8), 30, 100))
                marks_records.append({
                    "student_id": sid,
                    "subject_id": sub_id,
                    "exam_type": exam,
                    "score": score,
                    "max_score": 100
                })
                
    print(f"Total marks records generated: {len(marks_records)}")
    
    # Batch insert in chunks of 200
    marks_batch_size = 200
    for i in range(0, len(marks_records), marks_batch_size):
        batch = marks_records[i : i + marks_batch_size]
        supabase.table("marks").insert(batch).execute()
        if (i + marks_batch_size) % 1000 == 0 or (i + len(batch)) == len(marks_records):
            print(f"  Pushed {i + len(batch)} / {len(marks_records)} marks records...")
            
    print("Marks migration successfully completed.")

    # ------------------------------------------------------
    # STEP 6: Final Verification & Reporting
    # ------------------------------------------------------
    print("\n====================================================")
    print("             FINAL MIGRATION VERIFICATION           ")
    print("====================================================")
    
    cnt_students = supabase.table("students").select("*", count="exact").limit(0).execute().count
    cnt_attendance = supabase.table("attendance").select("*", count="exact").limit(0).execute().count
    cnt_marks = supabase.table("marks").select("*", count="exact").limit(0).execute().count
    
    print(f"SELECT COUNT(*) FROM students    -> Current: {cnt_students} | Target: 500")
    print(f"SELECT COUNT(*) FROM attendance  -> Current: {cnt_attendance} | Target: ~30000")
    print(f"SELECT COUNT(*) FROM marks       -> Current: {cnt_marks} | Target: ~10000")
    print("====================================================")

if __name__ == "__main__":
    main()
