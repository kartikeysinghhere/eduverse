import os
import bcrypt
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
DB_MODE = os.environ.get("DB_MODE", "supabase")

def hash_password(password: str) -> str:
    """Securely hashes passwords using bcrypt with salt rounds matching sign_in."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12)).decode('utf-8')

def setup_user(username, email, password, role):
    """Idempotently creates or updates a user in both Supabase and SQLite fallback databases."""
    if not email or not password:
        print(f"[-] Missing credentials for role {role}. Skipping.")
        return
        
    password_hash = hash_password(password)
    
    # 1. Supabase Setup
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            from supabase import create_client
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            
            # Check by username
            res = supabase.table("users").select("*").eq("username", username).execute()
            if res.data:
                user_id = res.data[0]["id"]
                supabase.table("users").update({
                    "email": email,
                    "password_hash": password_hash,
                    "role": role
                }).eq("id", user_id).execute()
                print(f"[+] Updated existing {role} user (username: {username}) in Supabase.")
            else:
                # Check by email
                res_email = supabase.table("users").select("*").eq("email", email).execute()
                if res_email.data:
                    user_id = res_email.data[0]["id"]
                    supabase.table("users").update({
                        "username": username,
                        "password_hash": password_hash,
                        "role": role
                    }).eq("id", user_id).execute()
                    print(f"[+] Updated existing {role} user (email: {email}) in Supabase.")
                else:
                    new_user = {
                        "username": username,
                        "email": email,
                        "password_hash": password_hash,
                        "role": role,
                        "created_at": datetime.now().isoformat()
                    }
                    new_user["id"] = 999 if role == "Admin" else 998
                    try:
                        supabase.table("users").insert(new_user).execute()
                        print(f"[+] Created new {role} user with ID {new_user['id']} in Supabase.")
                    except Exception:
                        # Fallback if manual ID causes constraint error
                        del new_user["id"]
                        supabase.table("users").insert(new_user).execute()
                        print(f"[+] Created new {role} user (auto-generated ID) in Supabase.")
        except Exception as e:
            print(f"[-] Supabase configuration or update failed for {role}: {e}")
            
    # 2. SQLite Fallback Setup
    db_path = ROOT / "eduverse.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            
            cur.execute("SELECT id FROM users WHERE username = ?", (username,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    "UPDATE users SET email = ?, password_hash = ?, role = ? WHERE id = ?",
                    (email, password_hash, role, row[0])
                )
                print(f"[+] Updated existing {role} user (username: {username}) in SQLite.")
            else:
                cur.execute("SELECT id FROM users WHERE email = ?", (email,))
                row_email = cur.fetchone()
                if row_email:
                    cur.execute(
                        "UPDATE users SET username = ?, password_hash = ?, role = ? WHERE id = ?",
                        (username, password_hash, role, row_email[0])
                    )
                    print(f"[+] Updated existing {role} user (email: {email}) in SQLite.")
                else:
                    static_id = 999 if role == "Admin" else 998
                    try:
                        cur.execute(
                            "INSERT INTO users (id, username, password_hash, role, email) VALUES (?, ?, ?, ?, ?)",
                            (static_id, username, password_hash, role, email)
                        )
                        print(f"[+] Created new {role} user with ID {static_id} in SQLite.")
                    except sqlite3.IntegrityError:
                        cur.execute(
                            "INSERT INTO users (username, password_hash, role, email) VALUES (?, ?, ?, ?)",
                            (username, password_hash, role, email)
                        )
                        print(f"[+] Created new {role} user (auto-generated ID) in SQLite.")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[-] SQLite fallback database update failed for {role}: {e}")

def main():
    print("====================================================")
    # Using dynamic, environment-based credentials safely (never hardcoded/printed)
    print("      EduVerse Administrative User Seeding Script      ")
    print("====================================================")
    
    admin_email = os.environ.get("EDUVERSE_ADMIN_EMAIL")
    admin_password = os.environ.get("EDUVERSE_ADMIN_PASSWORD")
    
    teacher_email = os.environ.get("EDUVERSE_TEACHER_EMAIL")
    teacher_password = os.environ.get("EDUVERSE_TEACHER_PASSWORD")
    
    if not admin_email or not admin_password or not teacher_email or not teacher_password:
        print("[!] Error: Missing required environment variables!")
        print("    Please ensure the following environment variables are set:")
        print("      - EDUVERSE_ADMIN_EMAIL")
        print("      - EDUVERSE_ADMIN_PASSWORD")
        print("      - EDUVERSE_TEACHER_EMAIL")
        print("      - EDUVERSE_TEACHER_PASSWORD")
        print("\n[!] Local Running Instructions:")
        print("    Option A: Add them to your local '.env' file.")
        print("    Option B: Run with temporary environment variables in PowerShell:")
        print("      $env:EDUVERSE_ADMIN_EMAIL='admin@eduverse.ai'")
        print("      $env:EDUVERSE_ADMIN_PASSWORD='YourSecureAdminPassword'")
        print("      $env:EDUVERSE_TEACHER_EMAIL='teacher@eduverse.ai'")
        print("      $env:EDUVERSE_TEACHER_PASSWORD='YourSecureTeacherPassword'")
        print("      python setup_users.py")
        print("\n[!] Render Running Instructions:")
        print("    Go to the Render Dashboard -> Select your Service -> Environment tab.")
        print("    Add these 4 keys and click 'Save Changes' to trigger an automatic redeploy.")
        return
        
    admin_username = admin_email.split("@")[0].strip()
    teacher_username = teacher_email.split("@")[0].strip()
    
    print("[*] Processing Admin user setup...")
    setup_user(admin_username, admin_email.strip(), admin_password, "Admin")
    
    print("\n[*] Processing Teacher user setup...")
    setup_user(teacher_username, teacher_email.strip(), teacher_password, "Teacher")
    
    print("\n[+] Database user setup execution completed successfully!")

if __name__ == "__main__":
    main()
