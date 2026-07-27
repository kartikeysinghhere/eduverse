import os
import sqlite3
import bcrypt
import logging
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
from utils.db import get_supabase_client, get_supabase_service_client
from postgrest.types import CountMethod

logger = logging.getLogger("eduverse.auth")
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=ROOT / ".env", override=True)

DB_MODE = os.environ.get("DB_MODE", "supabase")

MAX_USERNAME_LENGTH = 150
MAX_PASSWORD_LENGTH = 128

def get_db_connection():
    return sqlite3.connect(str(ROOT / "eduverse.db"))

def verify_password(password: str, hashed: str) -> bool:
    if not password or not hashed:
        return False

    if len(password) > MAX_PASSWORD_LENGTH:
        return False

    try:
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error("Password verification internal error occurred.")
        return False

def sign_in(username, password):
    if not username or not password:
        return None

    if len(username) > MAX_USERNAME_LENGTH or len(password) > MAX_PASSWORD_LENGTH:
        logger.warning(f"Authentication rejected due to excessive input lengths.")
        return None

    login_id = username.strip()

    if DB_MODE == "supabase":
        try:
            supabase = get_supabase_service_client()
            response = supabase.table("users").select("*").eq("username", login_id).execute()
            if not response.data and "@" in login_id:
                response = supabase.table("users").select("*").eq("email", login_id).execute()

            if response.data:
                user = response.data[0]
                if isinstance(user, dict):
                    hashed = user.get('password_hash', '')
                    if isinstance(hashed, str) and verify_password(password, hashed):
                        return user
            return None

        except Exception as e:
            logger.error("Supabase authentication encountered a connection/query error.")
            st.error("Authentication service is temporarily unavailable.")
            return None

    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        if "@" in login_id:
            cur.execute("SELECT * FROM users WHERE username = ? OR email = ?", (login_id, login_id))
        else:
            cur.execute("SELECT * FROM users WHERE username = ?", (login_id,))
        row = cur.fetchone()
        conn.close()

        if row:
            user = dict(row)
            if verify_password(password, user.get('password_hash', '')):
                return user
        return None

    except Exception as e:
        logger.error("SQLite fallback authentication encountered a connection/query error.")
        st.error("Authentication service is temporarily unavailable.")
        return None

def _generate_unique_username(base_username: str) -> str:
    """Generate a unique username, appending a random 4-digit suffix on collision."""
    import random as _rand
    candidate = base_username

    if DB_MODE == "supabase":
        try:
            supabase = get_supabase_service_client()
            for _attempt in range(10):
                res = supabase.table("users").select("id").eq("username", candidate).execute()
                if not res.data:
                    return candidate
                candidate = f"{base_username}{_rand.randint(1000, 9999)}"
            return f"{base_username}{_rand.randint(10000, 99999)}"
        except Exception as e:
            logger.error(f"Username uniqueness check failed: {e}")
            return f"{base_username}{_rand.randint(1000, 9999)}"

    # SQLite fallback
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        for _attempt in range(10):
            cur.execute("SELECT id FROM users WHERE username = ?", (candidate,))
            if not cur.fetchone():
                conn.close()
                return candidate
            candidate = f"{base_username}{_rand.randint(1000, 9999)}"
        conn.close()
        return f"{base_username}{_rand.randint(10000, 99999)}"
    except Exception:
        return f"{base_username}{_rand.randint(1000, 9999)}"


def _create_user_record(email: str, name: str) -> dict | None:
    """Create a new user record in the database for a Google OAuth sign-in. Returns the created user dict or None."""
    import secrets as _secrets

    base_username = name.lower().replace(" ", "")
    if not base_username:
        base_username = email.split("@")[0].lower()

    username = _generate_unique_username(base_username)
    # Generate a random password hash — user will always log in via Google
    random_pw_hash = bcrypt.hashpw(_secrets.token_bytes(32), bcrypt.gensalt()).decode('utf-8')

    if DB_MODE == "supabase":
        from typing import cast, Any
        try:
            supabase = get_supabase_service_client()
            # The auto-increment sequence may be out of sync after migration with explicit IDs.
            # Compute a safe next ID by querying the current max.
            max_res = supabase.table("users").select("id").order("id", desc=True).limit(1).execute()
            data_list = cast(list[dict[str, Any]], max_res.data)
            next_id = (int(data_list[0]["id"]) + 1) if data_list else 1000

            res = supabase.table("users").insert({
                "id": next_id,
                "username": username,
                "password_hash": random_pw_hash,
                "role": "Student",
                "email": email
            }).execute()
            if res.data:
                res_data_list = cast(list[dict[str, Any]], res.data)
                logger.info(f"[Auto-Register] Created new user '{username}' (email: {email}, id: {next_id}) in Supabase")
                return res_data_list[0]
            return None
        except Exception as e:
            logger.error(f"Failed to create user in Supabase: {e}")
            return None

    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash, role, email) VALUES (?, ?, ?, ?)",
            (username, random_pw_hash, "Student", email)
        )
        conn.commit()
        new_id = cur.lastrowid
        cur.execute("SELECT * FROM users WHERE id = ?", (new_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            logger.info(f"[Auto-Register] Created new user '{username}' (email: {email}, id: {new_id}) in SQLite")
            return dict(row)
        return None
    except Exception as e:
        logger.error(f"Failed to create user in SQLite: {e}")
        return None


def create_student_profile(user_id: int, name: str) -> bool:
    """Generate realistic random student data and insert into students, grades, and attendance tables.
    Uses the same statistical distributions as data_generator.py for consistency."""
    import numpy as np
    import random as _rand
    from datetime import datetime, timedelta

    departments = ['CS', 'EE', 'ME', 'Civil', 'AI', 'DS', 'MBA', 'BBA']

    # --- Generate realistic student metrics (matching data_generator.py) ---
    study_hours = round(float(np.clip(np.random.normal(24.0, 3.5), 5, 30)), 1)
    attendance_pct = int(np.clip(np.random.normal(86, 7), 60, 100))
    assignments_completed = int(np.clip(np.random.normal(16, 2.5), 5, 20))

    # generate_score logic from data_generator.py
    base_pct = 0.50 + (study_hours / 30.0) * 0.45
    variation = float(np.random.normal(0, 0.08))
    final_pct = max(0.35, min(0.99, base_pct + variation))
    internal_marks = round(final_pct * 100)

    # pct_to_gpa logic from data_generator.py
    pct = internal_marks
    if pct >= 93:
        gpa = 4.0
    elif pct >= 90:
        gpa = 3.7
    elif pct >= 87:
        gpa = 3.3
    elif pct >= 83:
        gpa = 3.0
    elif pct >= 80:
        gpa = 2.7
    elif pct >= 77:
        gpa = 2.3
    elif pct >= 73:
        gpa = 2.0
    elif pct >= 70:
        gpa = 1.7
    else:
        if pct < 40:
            gpa = 0.0
        else:
            gpa = round(0.0 + (pct - 40) * (1.7 - 0.0) / (70 - 40), 2)
    final_gpa = max(1.5, gpa)

    prev_gpa = round(float(np.clip(np.random.normal(final_gpa, 0.20), 1.5, 4.0)), 2)
    risk = 1 if final_gpa < 2.0 else 0

    student_record = {
        "student_id": user_id,
        "name": name,
        "department": _rand.choice(departments),
        "semester": _rand.randint(1, 8),
        "attendance_pct": attendance_pct,
        "internal_marks": internal_marks,
        "assignments_completed": assignments_completed,
        "study_hours": study_hours,
        "prev_gpa": prev_gpa,
        "final_gpa": final_gpa,
        "risk": risk
    }
    # Note: assigned_teacher_id is left as NULL — new Google students won't appear
    # in any teacher's filtered view, which is correct (teacher dashboard handles
    # empty results with a fallback on lines 30-31 and 73-74).

    # --- Generate grades for 6 subjects ---
    subjects = ['Mathematics', 'Physics', 'Computer Science', 'Data Structures', 'AI', 'Ethics']
    grade_records = []
    for sub in subjects:
        marks = int(np.clip(np.random.normal(internal_marks, 8), 30, 100))
        grade_records.append({"student_id": user_id, "Subject": sub, "Marks": marks})

    # --- Generate 24 days of attendance ---
    attendance_records = []
    dates = [datetime(2026, 5, 1) + timedelta(days=i) for i in range(24)]
    att_prob = attendance_pct / 100.0
    statuses = np.random.choice(['Present', 'Absent'], size=24, p=[att_prob, 1 - att_prob])
    for d, status in zip(dates, statuses):
        date_key = "date" if DB_MODE == "supabase" else "Date"
        status_key = "status" if DB_MODE == "supabase" else "Status"
        attendance_records.append({
            "student_id": user_id,
            date_key: d.strftime('%Y-%m-%d'),
            status_key: str(status)
        })

    # --- Insert everything ---
    if DB_MODE == "supabase":
        try:
            supabase = get_supabase_service_client()
            supabase.table("students").insert(student_record).execute()
            supabase.table("grades").insert(grade_records).execute()
            supabase.table("attendance").insert(attendance_records).execute()
            logger.info(f"[Auto-Register] Created student profile for user_id={user_id}: "
                        f"GPA={final_gpa}, dept={student_record['department']}, "
                        f"{len(grade_records)} grades, {len(attendance_records)} attendance records")
            return True
        except Exception as e:
            logger.error(f"Failed to create student profile in Supabase: {e}")
            return False

    # SQLite fallback
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO students (student_id, name, department, semester, attendance_pct,
                internal_marks, assignments_completed, study_hours, prev_gpa, final_gpa, risk)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, student_record['department'], student_record['semester'],
              attendance_pct, internal_marks, assignments_completed, study_hours,
              prev_gpa, final_gpa, risk))

        for g in grade_records:
            cur.execute("INSERT INTO grades (student_id, Subject, Marks) VALUES (?, ?, ?)",
                        (user_id, g['Subject'], g['Marks']))

        for a in attendance_records:
            cur.execute("INSERT INTO attendance (student_id, Date, Status) VALUES (?, ?, ?)",
                        (user_id, a.get('Date', a.get('date')), a.get('Status', a.get('status'))))

        conn.commit()
        conn.close()
        logger.info(f"[Auto-Register] Created student profile for user_id={user_id} in SQLite")
        return True
    except Exception as e:
        logger.error(f"Failed to create student profile in SQLite: {e}")
        return False


def sign_in_with_google(google_user_info):
    """Authenticates a user via Google OAuth. If the email exists, returns the user.
    If not, auto-creates a new Student user + full student profile with random data."""
    if not google_user_info or not google_user_info.get("email"):
        logger.error("No email found in google_user_info")
        return None

    email = google_user_info["email"].strip()
    google_name = google_user_info.get("name", "").strip() or email.split("@")[0]

    if DB_MODE == "supabase":
        try:
            supabase = get_supabase_service_client()
            response = supabase.table("users").select("*").eq("email", email).execute()
            if response.data:
                logger.info(f"[Google Login] Returning user found: {email}")
                return response.data[0]
        except Exception as e:
            logger.error(f"Supabase sign_in_with_google lookup error: {e}")
            return None

        # Email not found — auto-create new student
        logger.info(f"[Google Login] New user detected: {email}. Auto-creating student account...")
        new_user = _create_user_record(email, google_name)
        if not new_user:
            logger.error(f"[Google Login] Failed to create user record for {email}")
            return None

        profile_ok = create_student_profile(new_user['id'], google_name)
        if not profile_ok:
            logger.warning(f"[Google Login] Student profile creation failed for user {new_user['id']}, "
                           "but user record was created. Dashboard will use fallback data.")

        # Clear fetch_table cache so the new student data is visible immediately
        import streamlit as _st
        _st.cache_data.clear()
        return new_user

    # SQLite path
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cur.fetchone()

        if row:
            conn.close()
            logger.info(f"[Google Login] Returning user found: {email}")
            return dict(row)
        conn.close()
    except Exception as e:
        logger.error(f"SQLite sign_in_with_google lookup error: {e}")
        return None

    # Email not found — auto-create new student
    logger.info(f"[Google Login] New user detected: {email}. Auto-creating student account...")
    new_user = _create_user_record(email, google_name)
    if not new_user:
        logger.error(f"[Google Login] Failed to create user record for {email}")
        return None

    profile_ok = create_student_profile(new_user['id'], google_name)
    if not profile_ok:
        logger.warning(f"[Google Login] Student profile creation failed for user {new_user['id']}, "
                       "but user record was created. Dashboard will use fallback data.")

    import streamlit as _st
    _st.cache_data.clear()
    return new_user


def require_role(allowed_roles: list):
    if not st.session_state.get("user") or st.session_state.user.get("role") not in allowed_roles:
        st.error("Access denied")
        st.stop()

def init_rate_limit_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS failed_logins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to init rate limit db: {e}")

init_rate_limit_db()

from datetime import datetime, timedelta

def is_login_blocked(username: str) -> bool:
    if not username:
        return False
    if DB_MODE == "supabase":
        try:
            supabase = get_supabase_service_client()
            five_mins_ago = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
            res = supabase.table("failed_logins").select("id", count=CountMethod.exact).eq("username", username).gte("timestamp", five_mins_ago).execute()
            return res.count is not None and res.count >= 5
        except Exception as e:
            logger.warning(f"Supabase unavailable, falling back to SQLite. Error: {e}")
            
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM failed_logins WHERE username = ? AND timestamp >= datetime('now', '-5 minutes')", (username,))
        count = cur.fetchone()[0]
        conn.close()
        return count >= 5
    except Exception:
        return False

def record_attempt(username: str):
    if not username:
        return
    if DB_MODE == "supabase":
        try:
            supabase = get_supabase_service_client()
            supabase.table("failed_logins").insert({"username": username}).execute()
            return
        except Exception as e:
            logger.warning(f"Supabase unavailable, falling back to SQLite. Error: {e}")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO failed_logins (username) VALUES (?)", (username,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def reset_attempts(username: str):
    if not username:
        return
    if DB_MODE == "supabase":
        try:
            supabase = get_supabase_service_client()
            supabase.table("failed_logins").delete().eq("username", username).execute()
            return
        except Exception as e:
            logger.warning(f"Supabase unavailable, falling back to SQLite. Error: {e}")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM failed_logins WHERE username = ?", (username,))
        conn.commit()
        conn.close()
    except Exception:
        pass
