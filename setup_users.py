import os
import bcrypt
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client

# 1. Load .env
ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=ROOT / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

def hash_password(password: str) -> str:
    """Securely hashes passwords using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[-] Error: SUPABASE_URL or SUPABASE_KEY is missing in the environment.")
        return

    print("[*] Connecting to Supabase...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    users_to_create = [
        {
            "username": "admin",
            "password": "EduAdmin@2026",
            "role": "Admin",
            "email": "admin@eduverse.ai",
            "id": 999
        },
        {
            "username": "teacher",
            "password": "EduTeacher@2026",
            "role": "Teacher",
            "email": "teacher@eduverse.ai",
            "id": 998
        }
    ]

    for user_info in users_to_create:
        username = user_info["username"]
        email = user_info["email"]
        password = user_info["password"]
        role = user_info["role"]
        uid = user_info["id"]

        print(f"\n[*] Processing user: {username} ({role})...")
        password_hash = hash_password(password)

        # Before inserting check if user already exists by username
        res = supabase.table("users").select("*").eq("username", username).execute()
        if res.data:
            existing_user = res.data[0]
            existing_id = existing_user["id"]
            print(f"[+] User '{username}' already exists (ID: {existing_id}). Updating details...")
            supabase.table("users").update({
                "email": email,
                "password_hash": password_hash,
                "role": role
            }).eq("id", existing_id).execute()
            print(f"[+] Updated user '{username}' successfully.")
        else:
            print(f"[+] User '{username}' does not exist. Inserting...")
            new_user = {
                "id": uid,
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "role": role
            }
            try:
                supabase.table("users").insert(new_user).execute()
                print(f"[+] Inserted user '{username}' with fixed ID {uid}.")
            except Exception as e:
                # If fixed ID fails, let supabase auto-generate or insert without ID
                print(f"[-] Insertion with ID {uid} failed ({e}). Retrying without manual ID...")
                del new_user["id"]
                supabase.table("users").insert(new_user).execute()
                print(f"[+] Inserted user '{username}' with auto-generated ID.")

    # Keep local SQLite in sync as well
    db_path = ROOT / "eduverse.db"
    if db_path.exists():
        import sqlite3
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            for user_info in users_to_create:
                username = user_info["username"]
                email = user_info["email"]
                password_hash = hash_password(user_info["password"])
                role = user_info["role"]
                uid = user_info["id"]

                cur.execute("SELECT id FROM users WHERE username = ?", (username,))
                row = cur.fetchone()
                if row:
                    cur.execute(
                        "UPDATE users SET email = ?, password_hash = ?, role = ? WHERE id = ?",
                        (email, password_hash, role, row[0])
                    )
                else:
                    cur.execute(
                        "INSERT INTO users (id, username, password_hash, role, email) VALUES (?, ?, ?, ?, ?)",
                        (uid, username, password_hash, role, email)
                    )
            conn.commit()
            conn.close()
            print("[+] Local SQLite database updated successfully in sync.")
        except Exception as sqlite_err:
            print(f"[-] Failed to update local SQLite database: {sqlite_err}")

    print("\n==============================================")
    print("[*] Verifying users table in Supabase:")
    print("==============================================")
    for username in ["admin", "teacher"]:
        res = supabase.table("users").select("*").eq("username", username).execute()
        if res.data:
            print(f"Row for '{username}': {res.data[0]}")
        else:
            print(f"[-] Row for '{username}' NOT FOUND!")

if __name__ == "__main__":
    main()
