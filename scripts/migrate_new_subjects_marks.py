import os
import pandas as pd
import numpy as np
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

# Load environment configuration
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def main():
    print("====================================================")
    print("      EduVerse 4 New Subjects Marks Seeder          ")
    print("====================================================")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_KEY are not configured!")
        return
        
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 1. Get all subject IDs from database and identify the 4 newly added ones
    print("Step 1: Fetching subject IDs from Supabase subjects table...")
    res_subjects = supabase.table("subjects").select("*").execute()
    subjects_data = res_subjects.data
    
    # Original subjects are [1, 2, 3, 4, 5, 6]. The 4 newly added ones are those with id not in that list.
    original_subject_ids = {1, 2, 3, 4, 5, 6}
    new_subjects = [r for r in subjects_data if r['id'] not in original_subject_ids]
    new_subject_ids = [r['id'] for r in new_subjects]
    new_subject_names = [r['name'] for r in new_subjects]
    
    print(f"Detected 4 newly added subjects:")
    for r in new_subjects:
        print(f"  - ID: {r['id']}, Name: {r['name']}, Semester: {r['semester']}")
        
    if len(new_subject_ids) != 4:
        print(f"Warning: Expected 4 new subjects, but found {len(new_subject_ids)}. Proceeding with: {new_subject_ids}")

    # 2. Read sample_data.csv to get base internal marks for all 500 students
    print("\nStep 2: Loading dataset for all 500 students...")
    csv_path = ROOT / "data" / "sample_data.csv"
    if not csv_path.exists():
        print(f"Error: sample_data.csv not found at {csv_path}!")
        return
        
    df = pd.read_csv(csv_path)
    print(f"Successfully loaded {len(df)} student profiles.")

    # 3. Generate marks records for the 4 newly added subjects
    print("\nStep 3: Generating marks for all 500 students x 4 subjects x 2 exams (4,000 records)...")
    marks_records = []
    np.random.seed(42)
    
    for _, row in df.iterrows():
        sid = int(row['student_id'])
        base_marks = float(row['internal_marks'])
        
        for sub_id in new_subject_ids:
            for exam in ["Midterm", "Final"]:
                # Normal distribution centered around student's internal marks
                score = int(np.clip(np.random.normal(base_marks, 8), 30, 100))
                marks_records.append({
                    "student_id": sid,
                    "subject_id": sub_id,
                    "exam_type": exam,
                    "score": score,
                    "max_score": 100
                })
                
    total_records = len(marks_records)
    print(f"Generated exactly {total_records} marks records.")

    # 4. Batch insert in chunks of 200
    print(f"\nStep 4: Inserting {total_records} records into 'marks' table in batches of 200...")
    batch_size = 200
    for i in range(0, total_records, batch_size):
        batch = marks_records[i : i + batch_size]
        supabase.table("marks").insert(batch).execute()
        if (i + batch_size) % 1000 == 0 or (i + len(batch)) == total_records:
            print(f"  Pushed {i + len(batch)} / {total_records} records...")
            
    print("New marks migration successfully completed.")

    # 5. Final Verification Count
    print("\n====================================================")
    print("             FINAL MARKS VERIFICATION               ")
    print("====================================================")
    
    cnt_marks = supabase.table("marks").select("*", count="exact").limit(0).execute().count
    print(f"SELECT COUNT(*) FROM marks -> Current Total: {cnt_marks}")
    print("====================================================")

if __name__ == "__main__":
    main()
