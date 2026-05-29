import streamlit as st
import os
import json
import requests
import time
from collections import defaultdict
from dotenv import load_dotenv
from pathlib import Path
from utils.auth import sign_in
from utils.db import log_action
from utils.notifications import show_notifications

@st.cache_resource
def get_login_tracker():
    return defaultdict(list)

def is_login_blocked(username: str) -> bool:
    if not username:
        return False
    tracker = get_login_tracker()
    now = time.time()
    # Keep only attempts in the last 5 minutes (300 seconds)
    tracker[username] = [t for t in tracker[username] if now - t < 300]
    return len(tracker[username]) >= 5

def record_attempt(username: str):
    if not username:
        return
    tracker = get_login_tracker()
    tracker[username].append(time.time())

def reset_attempts(username: str):
    tracker = get_login_tracker()
    if username in tracker:
        tracker[username] = []


ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=ROOT / ".env")

# Page configuration
st.set_page_config(
    page_title="EduVerse | AI-Powered Analytics",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide sidebar instantly on app load for unauthenticated users (prevents brief flash)
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.markdown("""
        <style>
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="stSidebarCollapseButton"] {
            display: none !important;
        }
        .stApp [data-testid="stSidebar"] {
            display: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "analytics_data" not in st.session_state:
    st.session_state.analytics_data = {"visits": {}, "searches": []}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "assistant", "content": "Hello! I am your EduVerse AI Assistant. Kaise help kar sakta hoon?"}]

# Session expiry check: if session older than 24 hours (86400 seconds), force logout automatically
if st.session_state.get("logged_in") and "login_time" in st.session_state:
    if time.time() - st.session_state.login_time > 86400:
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.role = None
        st.warning("Session expired. Please log in again.")
        st.rerun()


# Load CSS
def load_css():
    with open(ROOT / "assets" / "style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()


# Sidebar Navigation
def sidebar_nav():
    
    if not st.session_state.logged_in:
        # Hide sidebar completely when not logged in to prevent it from showing behind the login form
        st.markdown("""
            <style>
            [data-testid="stSidebar"] {
                display: none !important;
            }
            [data-testid="stSidebarCollapseButton"] {
                display: none !important;
            }
            .stApp [data-testid="stSidebar"] {
                display: none !important;
            }
            </style>
        """, unsafe_allow_html=True)
        return "Landing Page"

    st.sidebar.markdown('<div class="sidebar-logo">EduVerse</div>', unsafe_allow_html=True)

    # Sidebar User Profile
    user = st.session_state.user
    initials = "".join([n[0] for n in user['username'].split()[:2]]).upper()
    if not initials: initials = user['username'][:2].upper()

    st.sidebar.markdown(f"""
        <div class="sidebar-user-card fade-in">
            <div class="avatar-circle">{initials}</div>
            <div style="font-weight: 800; font-size: 1.2rem; letter-spacing: -0.5px;">{user['username']}</div>
            <div style="margin-top: 8px;"><span class="role-badge">{st.session_state.role}</span></div>
        </div>
    """, unsafe_allow_html=True)

    # Search Bar for Analytics Tracking
    st.sidebar.markdown('<p style="color: #475569; font-size: 0.75rem; font-weight: 800; margin-left: 20px; margin-bottom: 5px; letter-spacing: 2px;">SEARCH</p>', unsafe_allow_html=True)
    search_query = st.sidebar.text_input("", placeholder="Find insights...", key="global_search_input", label_visibility="collapsed")
    if search_query:
        if "last_search" not in st.session_state or st.session_state.last_search != search_query:
            st.session_state.analytics_data["searches"].append(search_query)
            st.session_state.last_search = search_query

    pages = {
        "Student": ["Dashboard", "My Grades", "Attendance", "AI Insights", "How It Works", "🤖 AI Chat"],
        "Teacher": ["Dashboard", "Student Management", "Upload Marks", "Analytics", "How It Works", "🤖 AI Chat"],
        "Admin": ["Dashboard", "User Management", "System Health", "Reports", "Audit Logs", "Smart Analytics", "How It Works", "🤖 AI Chat"]
    }
    
    available_pages = pages.get(st.session_state.role, [])
    
    if "selection" not in st.session_state:
        st.session_state.selection = available_pages[0]

    st.sidebar.markdown('<p style="color: #475569; font-size: 0.75rem; font-weight: 800; margin-left: 20px; margin-top: 20px; margin-bottom: 15px; letter-spacing: 2px;">PLATFORM NAV</p>', unsafe_allow_html=True)
    
    for page in available_pages:
        label = f"✨ {page}" if st.session_state.selection == page else page
        if st.sidebar.button(label, key=f"nav_{page}", use_container_width=True):
            st.session_state.selection = page
            # Track Page Visit
            st.session_state.analytics_data["visits"][page] = st.session_state.analytics_data["visits"].get(page, 0) + 1
            st.rerun()

    st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
    if st.sidebar.button("🚪 Logout", key="logout_btn", use_container_width=True):
        try:
            log_action(st.session_state.user['id'], "Logout")
        except Exception:
            pass
        # Completely clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
        
    return st.session_state.selection

# Main App Logic
def main():
    selection = sidebar_nav()
    show_notifications()

    if not st.session_state.logged_in:
        show_landing_page()
    else:
        # Route to specific dashboards based on role
        if selection == "How It Works":
            import pages.how_it_works as how_it_works
            how_it_works.show()
        elif selection == "🤖 AI Chat":
            from pages import ai_insights
            ai_insights.show_chat()
        elif st.session_state.role == "Student":
            if selection == "AI Insights":
                import pages.ai_insights as ai_insights
                ai_insights.show()
            else:
                import pages.student_dashboard as student
                student.show(selection)
        elif st.session_state.role == "Teacher":
            import pages.teacher_dashboard as teacher
            teacher.show(selection)
        elif st.session_state.role == "Admin":
            if selection == "Smart Analytics":
                import pages.analytics as analytics
                analytics.show()
            else:
                import pages.admin_dashboard as admin
                admin.show(selection)
        elif selection == "AI Insights":
            from pages import ai_insights
            ai_insights.show()


def show_landing_page():
    # Render unauthenticated marker element to trigger zero-scroll CSS overrides
    st.markdown('<div class="unauthenticated-root"></div>', unsafe_allow_html=True)
    # Inject CSS for vertical centering and zero padding
    st.markdown("""
        <style>
        .main .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
        }
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if not st.session_state.get("show_login", False):
        st.markdown("""
            <div class="hero-container fade-in">
                <div class="sidebar-logo" style="font-size: 3.5rem; margin-bottom: 5px; line-height: 1;">EduVerse</div>
                <p style="font-size: 1.1rem; color: #94a3b8; max-width: 800px; margin: 0 auto 2rem; font-weight: 400; line-height: 1.4;">
                    The <span class="gradient-text" style="font-weight: 800;">World-Class</span> Intelligence layer for modern education.<br/>
                    AI-powered analytics that feel like the future.
                </p>
                <div style="display: flex; justify-content: center; gap: 1.5rem; margin-bottom: 1.8rem; margin-top: 2.5rem;">
                    <div class="glass-card floating-card" style="padding: 1.5rem 2.5rem;">
                        <span style="font-size: 2.8rem; font-weight: 900; color: #00f2fe; display: block;">1,200+</span>
                        <span style="color: #64748b; font-weight: 700; letter-spacing: 1px; font-size: 0.85rem;">STUDENTS</span>
                    </div>
                    <div class="glass-card floating-card" style="padding: 1.5rem 2.5rem; animation-delay: 1s;">
                        <span style="font-size: 2.8rem; font-weight: 900; color: #43e97b; display: block;">95%</span>
                        <span style="color: #64748b; font-weight: 700; letter-spacing: 1px; font-size: 0.85rem;">PASS RATE</span>
                    </div>
                    <div class="glass-card floating-card" style="padding: 1.5rem 2.5rem; animation-delay: 2s;">
                        <span style="font-size: 2.8rem; font-weight: 900; color: #fa709a; display: block;">AI</span>
                        <span style="color: #64748b; font-weight: 700; letter-spacing: 1px; font-size: 0.85rem;">INSIGHTS</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
            <style>
            div[data-testid="stColumn"] button {
                min-width: 300px !important;
                margin-top: 2.5rem !important;
                font-size: 1.1rem !important;
                padding: 0.8rem 2rem !important;
                height: auto !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1.5, 1, 1.5])
        with col2:
            if st.button("Launch Platform →", use_container_width=True):
                st.session_state.show_login = True
                st.rerun()
    else:
        # Compact Top Header - margin-bottom set to 0 to avoid dark bar
        st.markdown('<div style="text-align: center; margin-bottom: 0rem; margin-top: 0.5rem;"><div class="sidebar-logo" style="font-size: 2.8rem; margin-bottom: 0; line-height: 1;">EduVerse</div><p style="color: #64748b; font-weight: 600; margin-top: 2px; font-size: 0.9rem; margin-bottom: 0.4rem;">AI-Powered Education Analytics</p></div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1.8, 1])
        with col2:
            st.markdown("""
                <style>
                [data-testid="column"]:nth-of-type(2) {
                    background: rgba(255, 255, 255, 0.03) !important;
                    backdrop-filter: blur(20px) !important;
                    border: 1px solid rgba(255, 255, 255, 0.08) !important;
                    border-radius: 20px !important;
                    padding: 1.4rem 2rem !important;
                    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3) !important;
                }
                </style>
            """, unsafe_allow_html=True)
            
            # Using div with style instead of h1/h2 to avoid anchor links (⛓)
            st.markdown('<div class="gradient-text" style="text-align: center; font-size: 2rem; font-weight: 900; letter-spacing: -1.5px; margin-bottom: 2px;">Welcome Back</div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align: center; color: #94a3b8; font-size: 0.9rem; margin-bottom: 0.8rem;">Secure entry to your EduVerse account</div>', unsafe_allow_html=True)
            
            username = st.text_input("Username", placeholder="e.g. admin")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            if st.button("Access Dashboard", use_container_width=True):
                username_cleaned = username.strip() if username else ""
                
                if is_login_blocked(username_cleaned):
                    st.error("Too many login attempts. Please try again after 5 minutes.")
                else:
                    result = sign_in(username, password)
                    if result:
                        reset_attempts(username_cleaned)
                        
                        # Session Fixation Protection: Clear entire session state first
                        for key in list(st.session_state.keys()):
                            del st.session_state[key]
                            
                        # Set fresh user data and login timestamp
                        st.session_state.logged_in = True
                        st.session_state.user = result
                        st.session_state.role = result['role']
                        st.session_state.login_time = time.time()
                        
                        # Re-initialize other required state variables
                        st.session_state.theme = "dark"
                        st.session_state.analytics_data = {"visits": {}, "searches": []}
                        st.session_state.chat_history = [{"role": "assistant", "content": "Hello! I am your EduVerse AI Assistant. Kaise help kar sakta hoon?"}]
                        
                        log_action(result['id'], "Login")
                        st.rerun()
                    else:
                        record_attempt(username_cleaned)
                        st.error("Invalid credentials")
            
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
            if st.button("← Return to Home", key="back_home", use_container_width=True):
                st.session_state.show_login = False
                st.rerun()

if __name__ == "__main__":
    main()
