import streamlit as st
import os
import requests
import time
from collections import defaultdict
from dotenv import load_dotenv
from pathlib import Path
from utils.auth import sign_in, sign_in_with_google, require_role
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
load_dotenv(dotenv_path=ROOT / ".env", override=True)

# Page configuration (MUST be first Streamlit UI command called)
st.set_page_config(
    page_title="EduVerse - Secure Access",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state early to prevent any key errors in checks
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

import secrets

def get_google_auth_url():
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    st.session_state["oauth_state"] = state
    
    # Build auth URL manually - NO PKCE, plain OAuth2
    params = {
        "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
        "redirect_uri": os.environ.get("GOOGLE_REDIRECT_URI"),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account"
    }
    
    from urllib.parse import urlencode
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    return f"{base_url}?{urlencode(params)}"

def exchange_code_for_user_info(code):
    # Exchange code for token
    token_response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
            "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
            "redirect_uri": os.environ.get("GOOGLE_REDIRECT_URI"),
            "grant_type": "authorization_code",
        },
        timeout=10
    )
    token_data = token_response.json()
    access_token = token_data.get("access_token")
    
    if not access_token:
        print(f"[OAuth] Token exchange failed. Response: {token_data}")
        st.error("Authentication failed. Please try again.")
        st.stop()
    
    # Get user info
    userinfo_response = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10
    )
    user_info = userinfo_response.json()
    
    if not user_info.get("email"):
        print(f"[OAuth] Failed to retrieve user profile. Response: {user_info}")
        st.error("Authentication failed. Please try again.")
        st.stop()
        
    return user_info

def clear_oauth_query_params():
    try:
        st.query_params.clear()
    except Exception:
        try:
            st.experimental_set_query_params()
        except Exception:
            pass

# 1. At very top of app.py, before anything else, check if Google auth callback params exist in URL
has_google_callback = False
try:
    if "code" in st.query_params:
        has_google_callback = True
except AttributeError:
    try:
        if "code" in st.experimental_get_query_params():
            has_google_callback = True
    except Exception:
        pass

if has_google_callback and not st.session_state.logged_in:
    code = ""
    state = ""
    try:
        code = st.query_params.get("code", "")
        state = st.query_params.get("state", "")
    except AttributeError:
        try:
            code = st.experimental_get_query_params().get("code", [""])[0]
            state = st.experimental_get_query_params().get("state", [""])[0]
        except Exception:
            pass

    # Validate OAuth state parameter to prevent CSRF attacks
    expected_state = st.session_state.get("oauth_state")
    if not state or state != expected_state:
        clear_oauth_query_params()
        st.error("Invalid authentication state. Please try logging in again.")
        st.session_state.show_login = True
        st.stop()

    if code:
        google_user_info = exchange_code_for_user_info(code)
        if google_user_info:
            result = sign_in_with_google(google_user_info)
            if result:
                # Clear query params to prevent callback loop on rerun
                clear_oauth_query_params()
                
                # Clear session to prevent session fixation
                for key in list(st.session_state.keys()):
                    if key not in ["oauth_state"]:
                        del st.session_state[key]
                        
                st.session_state.logged_in = True
                st.session_state.user = result
                st.session_state.role = result['role']
                st.session_state.login_time = time.time()
                st.session_state.auth_provider = "google"
                
                # Re-initialize other required state variables
                st.session_state.theme = "dark"
                st.session_state.analytics_data = {"visits": {}, "searches": []}
                st.session_state.chat_history = [{"role": "assistant", "content": "Hello! I am your EduVerse AI Assistant. Kaise help kar sakta hoon?"}]
                
                log_action(result['id'], "Google Login")
                st.rerun()
            else:
                # Google email not mapped in table! Access Denied and clean up
                clear_oauth_query_params()
                st.session_state.google_auth_error = "Access denied: Your Gmail account is not registered in EduVerse."
                st.session_state.show_login = True
                st.rerun()
        else:
            clear_oauth_query_params()
            st.session_state.google_auth_error = "Authentication failed: Could not retrieve user profile from Google."
            st.session_state.show_login = True
            st.rerun()

# 2. If st.session_state['logged_in'] is True: skip login page entirely, go straight to dashboard
if st.session_state.get("logged_in"):
    st.session_state.show_login = False

# Hide sidebar instantly on app load for unauthenticated users (prevents brief flash)
if not st.session_state.logged_in:
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

    MENU = {
        "Student": ["Dashboard", "My Grades", "Attendance", "AI Insights", "How It Works", "AI Chat"],
        "Teacher": ["Dashboard", "Student Management", "Upload Marks", "Analytics", "How It Works", "AI Chat"],
        "Admin": ["Dashboard", "User Management", "System Health", "Reports", "Audit Logs", "Smart Analytics", "How It Works", "AI Chat"]
    }
    
    available_pages = MENU.get(st.session_state.role, [])
    
    if "selection" not in st.session_state:
        st.session_state.selection = available_pages[0]

    st.sidebar.markdown('<p style="color: #475569; font-size: 0.75rem; font-weight: 800; margin-left: 20px; margin-top: 20px; margin-bottom: 15px; letter-spacing: 2px;">PLATFORM NAV</p>', unsafe_allow_html=True)
    
    for page in available_pages:
        label = f"• {page}" if st.session_state.selection == page else page
        if st.sidebar.button(label, key=f"nav_{page}", use_container_width=True):
            st.session_state.selection = page
            # Track Page Visit
            st.session_state.analytics_data["visits"][page] = st.session_state.analytics_data["visits"].get(page, 0) + 1
            st.rerun()

    st.sidebar.markdown('<hr style="border-color: rgba(255, 255, 255, 0.1);"/>', unsafe_allow_html=True)
    if st.sidebar.button("Logout", key="logout_btn", use_container_width=True):
        try:
            log_action(st.session_state.user['id'], "Logout")
        except Exception:
            pass
        # Completely clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        st.session_state.logged_in = False
        st.session_state.show_login = True
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
            require_role(['Admin', 'Teacher', 'Student'])
            import pages.how_it_works as how_it_works
            how_it_works.show()
        elif selection == "AI Chat":
            require_role(['Admin', 'Teacher', 'Student'])
            from pages import ai_insights
            ai_insights.show_chat()
        elif st.session_state.role == "Student":
            require_role(['Admin', 'Teacher', 'Student'])
            if selection == "AI Insights":
                import pages.ai_insights as ai_insights
                ai_insights.show()
            else:
                import pages.student_dashboard as student
                student.show(selection)
        elif st.session_state.role == "Teacher":
            require_role(['Admin', 'Teacher'])
            import pages.teacher_dashboard as teacher
            teacher.show(selection)
        elif st.session_state.role == "Admin":
            require_role(['Admin'])
            if selection == "Smart Analytics":
                import pages.analytics as analytics
                analytics.show()
            else:
                import pages.admin_dashboard as admin
                admin.show(selection)
        elif selection == "AI Insights":
            require_role(['Admin', 'Teacher', 'Student'])
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
                        <span style="font-size: 2.8rem; font-weight: 900; color: #00f2fe; display: block;">500+</span>
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
            if st.button("Launch Platform ->", use_container_width=True):
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
            
            # Using div with style instead of h1/h2 to avoid anchor links
            st.markdown("<div style='font-size: 2rem; font-weight: 800; color: #1e293b; margin-bottom: 5px; text-align: center; font-family: Inter, sans-serif;'>EduVerse Access</div>", unsafe_allow_html=True)
            st.markdown('<div style="text-align: center; color: #94a3b8; font-size: 0.9rem; margin-bottom: 0.8rem;">Secure entry to your EduVerse account</div>', unsafe_allow_html=True)
            
            if st.session_state.get("google_auth_error"):
                st.error(st.session_state.google_auth_error)
                del st.session_state["google_auth_error"]
                
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
            
            # --- OR Divider ---
            st.markdown("<div style='text-align: center; margin: 15px 0; color: #64748b; font-weight: bold;'>— OR —</div>", unsafe_allow_html=True)
            
            # Google OAuth Login Button
            try:
                auth_url = get_google_auth_url()
                st.markdown(f'''
                    <a href="{auth_url}" target="_self">
                        <button style="background:#1a73e8; color:white; border:none; 
                        padding:12px 24px; border-radius:8px; cursor:pointer; 
                        font-size:16px; width:100%;">
                            Sign in with Google
                        </button>
                    </a>
                ''', unsafe_allow_html=True)
            except Exception as e:
                st.error("Google login currently unavailable.")
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("← Return to Home", key="back_home", use_container_width=True):
                st.session_state.show_login = False
                st.rerun()


if __name__ == "__main__":
    main()
