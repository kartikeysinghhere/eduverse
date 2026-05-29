import os
import bcrypt
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def main():
    print("====================================================")
    print("      EduVerse Supabase Password Reset Utility      ")
    print("====================================================")
    
    # Step 1: Generate hashes
    admin_pw = os.environ.get("EDUVERSE_ADMIN_PASSWORD")
    teacher_pw = os.environ.get("EDUVERSE_TEACHER_PASSWORD")
    
    if not admin_pw or not teacher_pw:
        print("[!] Error: EDUVERSE_ADMIN_PASSWORD and EDUVERSE_TEACHER_PASSWORD must be set in environment variables!")
        return
        
    admin_hash = bcrypt.hashpw(admin_pw.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')
    teacher_hash = bcrypt.hashpw(teacher_pw.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')
    
    print("\n--- STEP 1 & 2: GENERATED BCRYPT HASHES ---")
    print(f"Admin Username  : admin")
    print(f"Admin Password  : [REDACTED]")
    print(f"Admin Hash      : [REDACTED]")
    
    print(f"\nTeacher Username: teacher")
    print(f"Teacher Password: [REDACTED]")
    print(f"Teacher Hash    : [REDACTED]")
    
    # Step 3: Attempt Supabase Update
    print("\n--- STEP 3: ATTEMPTING SUPABASE API UPDATE ---")
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: Supabase credentials not found in env!")
        return
        
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Connected to Supabase successfully!")
        
        # 1. Update Admin
        res_admin = supabase.table("users").update({"password_hash": admin_hash}).eq("username", "admin").execute()
        print("Admin update query completed.")
        
        # 2. Update Teacher
        res_teacher = supabase.table("users").update({"password_hash": teacher_hash}).eq("username", "teacher").execute()
        print("Teacher update query completed.")
        
    except Exception as e:
        print("Supabase client update failed:", e)
        
    print("\n[+] Done.")

if __name__ == "__main__":
    main()
