import streamlit as st

def add_notification(message, type="info"):
    if "notifications" not in st.session_state:
        st.session_state.notifications = []
    st.session_state.notifications.append({"message": message, "type": type})

def show_notifications():
    if "notifications" in st.session_state and st.session_state.notifications:
        for note in st.session_state.notifications:
            if note["type"] == "warning":
                st.warning(note["message"])
            elif note["type"] == "error":
                st.error(note["message"])
            elif note["type"] == "success":
                st.success(note["message"])
            else:
                st.info(note["message"])
        # Clear notifications after showing
        st.session_state.notifications = []

def check_low_attendance(attendance_pct):
    if attendance_pct < 75:
        add_notification(f"Warning: Your attendance is critically low at {attendance_pct}%.", "warning")

def check_assignment_due(due_date_str):
    from datetime import datetime
    try:
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        days_left = (due_date - datetime.now()).days
        if 0 <= days_left <= 2:
            add_notification(f"Alert: Assignment '{due_date_str}' is due in {days_left} days!", "info")
    except Exception:
        pass
