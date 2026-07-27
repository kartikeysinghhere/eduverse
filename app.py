import streamlit as st
import os
import requests
import time
from collections import defaultdict
from dotenv import load_dotenv
from pathlib import Path
from utils.auth import sign_in, sign_in_with_google, require_role, is_login_blocked, record_attempt, reset_attempts
from utils.db import log_action
from utils.notifications import show_notifications





def handle_login():
    username = st.session_state.get("login_username", "")
    password = st.session_state.get("login_password", "")
    username_cleaned = username.strip()

    if is_login_blocked(username_cleaned):
        st.session_state.login_error = "Too many login attempts. Please try again after 5 minutes."
    else:
        result = sign_in(username, password)
        if result:
            reset_attempts(username_cleaned)

            for key in list(st.session_state.keys()):
                if key not in ["login_username", "login_password", "oauth_state", "show_login"]:
                    del st.session_state[key]

            from typing import cast, Any
            result_dict = cast(dict[str, Any], result)
            st.session_state.logged_in = True
            st.session_state.user = result_dict
            st.session_state.role = result_dict['role']
            st.session_state.login_time = time.time()
            st.session_state.theme = "dark"
            st.session_state.analytics_data = {"visits": {}, "searches": []}
            st.session_state.chat_history = [{"role": "assistant", "content": "Hello! I am your EduVerse AI Assistant. Kaise help kar sakta hoon?"}]

            log_action(result_dict['id'], "Login")
        else:
            record_attempt(username_cleaned)
            st.session_state.login_error = "Invalid credentials"

ROOT = Path(__file__).resolve().parent
load_dotenv(dotenv_path=ROOT / ".env", override=True)

st.set_page_config(
    page_title="EduVerse - Secure Access",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    state = secrets.token_urlsafe(32)
    st.session_state["oauth_state"] = state

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
    st.query_params.clear()

has_google_callback = False
if "code" in st.query_params:
    has_google_callback = True

if has_google_callback and not st.session_state.logged_in:
    code = st.query_params.get("code", "")

    if code:
        google_user_info = exchange_code_for_user_info(code)
        if google_user_info:
            result = sign_in_with_google(google_user_info)
            if result:
                from typing import cast, Any
                result_dict = cast(dict[str, Any], result)
                clear_oauth_query_params()

                for key in list(st.session_state.keys()):
                    if key not in ["oauth_state"]:
                        del st.session_state[key]

                st.session_state.logged_in = True
                st.session_state.user = result_dict
                st.session_state.role = result_dict['role']
                st.session_state.login_time = time.time()
                st.session_state.auth_provider = "google"

                st.session_state.theme = "dark"
                st.session_state.analytics_data = {"visits": {}, "searches": []}
                st.session_state.chat_history = [{"role": "assistant", "content": "Hello! I am your EduVerse AI Assistant. Kaise help kar sakta hoon?"}]

                log_action(result_dict['id'], "Google Login")
                st.rerun()
            else:
                clear_oauth_query_params()
                st.session_state.google_auth_error = "Sign-in failed: Could not create your account. Please try again later."
                st.session_state.show_login = True
                st.rerun()
        else:
            clear_oauth_query_params()
            st.session_state.google_auth_error = "Authentication failed: Could not retrieve user profile from Google."
            st.session_state.show_login = True
            st.rerun()

if st.session_state.get("logged_in"):
    st.session_state.show_login = False

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

if st.session_state.get("logged_in") and "login_time" in st.session_state:
    if time.time() - st.session_state.login_time > 86400:
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.role = None
        st.warning("Session expired. Please log in again.")
        st.rerun()





def load_css():
    with open(ROOT / "assets" / "style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()


def sidebar_nav():

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
        return "Landing Page"

    st.sidebar.markdown('<div class="sidebar-logo">EduVerse</div>', unsafe_allow_html=True)

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




    st.sidebar.markdown('<p style="color: #475569; font-size: 0.75rem; font-weight: 800; margin-left: 20px; margin-bottom: 5px; letter-spacing: 2px;">SEARCH</p>', unsafe_allow_html=True)
    search_query = st.sidebar.text_input("", placeholder="Find insights...", key="global_search_input", label_visibility="collapsed")
    if search_query:
        if "last_search" not in st.session_state or st.session_state.last_search != search_query:
            st.session_state.analytics_data["searches"].append(search_query)
            st.session_state.last_search = search_query

    MENU = {
        "Student": ["Dashboard", "My Grades", "Attendance", "AI Insights", "AI Chat"],
        "Teacher": ["Dashboard", "Student Management", "Upload Marks", "Analytics", "AI Chat"],
        "Admin": ["Dashboard", "User Management", "System Health", "Reports", "Audit Logs", "Smart Analytics", "AI Chat"]
    }

    available_pages = MENU.get(st.session_state.role, [])

    if "selection" not in st.session_state:
        st.session_state.selection = available_pages[0]

    st.sidebar.markdown('<p style="color: #475569; font-size: 0.75rem; font-weight: 800; margin-left: 20px; margin-top: 20px; margin-bottom: 15px; letter-spacing: 2px;">PLATFORM NAV</p>', unsafe_allow_html=True)

    for page in available_pages:
        label = f"• {page}" if st.session_state.selection == page else page
        if st.sidebar.button(label, key=f"nav_{page}", use_container_width=True):
            st.session_state.selection = page
            st.session_state.analytics_data["visits"][page] = st.session_state.analytics_data["visits"].get(page, 0) + 1
            st.rerun()

    st.sidebar.markdown('<hr style="border-color: rgba(255, 255, 255, 0.1);"/>', unsafe_allow_html=True)
    if st.sidebar.button("Logout", key="logout_btn", use_container_width=True):
        try:
            from typing import cast, Any
            user_dict = cast(dict[str, Any], st.session_state.user)
            log_action(user_dict['id'], "Logout")
        except Exception:
            pass
        for key in list(st.session_state.keys()):
            del st.session_state[key]

        st.session_state.logged_in = False
        st.session_state.show_login = True
        st.rerun()


    return st.session_state.selection

def main():
    selection = sidebar_nav()
    show_notifications()

    if not st.session_state.logged_in:
        show_landing_page()
    else:
        if selection == "AI Chat":
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
    st.markdown('<div class="unauthenticated-root"></div>', unsafe_allow_html=True)
    st.markdown("""
        <style>
        .main .block-container {
            padding-top: 0.3rem !important;
            padding-bottom: 0rem !important;
        }
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
            gap: 0.2rem !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if not st.session_state.get("show_login", False):
        st.markdown("""
            <div class="hero-container fade-in">
                <div class="sidebar-logo" style="font-size: 4.5rem; margin-bottom: 1.5rem; line-height: 1;">EduVerse</div>
                <p style="font-size: 1.4rem; color: #94a3b8; max-width: 800px; margin: 0 auto 3rem; font-weight: 400; line-height: 1.6;">
                    The <span class="gradient-text" style="font-weight: 800;">World-Class</span> Intelligence layer for modern education.<br/>
                    AI-powered analytics that feel like the future.
                </p>
                <div style="display: flex; justify-content: center; gap: 3rem; margin-bottom: 4rem; margin-top: 2rem;">
                    <div class="glass-card floating-card" style="padding: 2.5rem 3.5rem;">
                        <span style="font-size: 3.5rem; font-weight: 900; color: #00f2fe; display: block; margin-bottom: 0.5rem;">500+</span>
                        <span style="color: #64748b; font-weight: 700; letter-spacing: 2px; font-size: 1.1rem;">STUDENTS</span>
                    </div>
                    <div class="glass-card floating-card" style="padding: 2.5rem 3.5rem; animation-delay: 1s;">
                        <span style="font-size: 3.5rem; font-weight: 900; color: #43e97b; display: block; margin-bottom: 0.5rem;">95%</span>
                        <span style="color: #64748b; font-weight: 700; letter-spacing: 2px; font-size: 1.1rem;">PASS RATE</span>
                    </div>
                    <div class="glass-card floating-card" style="padding: 2.5rem 3.5rem; animation-delay: 2s;">
                        <span style="font-size: 3.5rem; font-weight: 900; color: #fa709a; display: block; margin-bottom: 0.5rem;">AI</span>
                        <span style="color: #64748b; font-weight: 700; letter-spacing: 2px; font-size: 1.1rem;">INSIGHTS</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("""
            <style>
            div[data-testid="stColumn"] button {
                min-width: 400px !important;
                margin-top: 1.5rem !important;
                font-size: 1.4rem !important;
                padding: 1rem 3rem !important;
                height: auto !important;
                border-radius: 16px !important;
            }
            </style>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            if st.button("Launch Platform ->", use_container_width=True):
                st.session_state.show_login = True
                st.rerun()
    else:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
                <style>
                [data-testid="column"]:nth-of-type(2) {
                    background: rgba(255, 255, 255, 0.03) !important;
                    backdrop-filter: blur(20px) !important;
                    border: 1px solid rgba(255, 255, 255, 0.08) !important;
                    border-radius: 20px !important;
                    padding: 3rem 4rem !important;
                    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3) !important;
                }
                </style>
            """, unsafe_allow_html=True)

            st.markdown("""
                <div style="text-align: center; margin-bottom: 2rem;">
                    <div style="font-size: 1.8rem; font-weight: 800; color: #e2e8f0; line-height: 1.2; font-family: Inter, sans-serif;">EduVerse Access</div>
                    <div style="color: #94a3b8; font-size: 1.1rem; margin-top: 0.5rem;">Secure entry to your EduVerse account</div>
                </div>
            """, unsafe_allow_html=True)

            if st.session_state.get("google_auth_error"):
                st.error(st.session_state.google_auth_error)
                del st.session_state["google_auth_error"]

            if st.session_state.get("login_error"):
                st.error(st.session_state.login_error)
                del st.session_state["login_error"]

            st.text_input("Username", placeholder="e.g. admin", key="login_username")
            st.text_input("Password", type="password", placeholder="••••••••", key="login_password")

            st.markdown("""
                <style>
                /* Primary CTA — cyan fill for Access Dashboard */
                .st-key-access_dashboard_btn button {
                    background: linear-gradient(135deg, #00d4ff, #00b4d8) !important;
                    color: #0a0f1e !important;
                    border: none !important;
                    font-weight: 700 !important;
                    font-size: 1.3rem !important;
                    padding: 1rem 2rem !important;
                    border-radius: 12px !important;
                    box-shadow: 0 4px 18px rgba(0, 212, 255, 0.25) !important;
                    transition: all 0.3s ease !important;
                    margin-top: 1.5rem !important;
                }
                .st-key-access_dashboard_btn button:hover {
                    background: linear-gradient(135deg, #00f2fe, #00c4e0) !important;
                    box-shadow: 0 6px 24px rgba(0, 242, 254, 0.4) !important;
                    transform: translateY(-1px) !important;
                }
                /* Return to Home — subtle secondary style */
                .st-key-back_home button {
                    background: transparent !important;
                    color: #94a3b8 !important;
                    border: 1px solid rgba(255, 255, 255, 0.12) !important;
                    box-shadow: none !important;
                    font-weight: 500 !important;
                    font-size: 1.2rem !important;
                    padding: 0.8rem 2rem !important;
                    margin-top: 1rem !important;
                }
                .st-key-back_home button:hover {
                    background: rgba(255, 255, 255, 0.05) !important;
                    color: #e2e8f0 !important;
                    box-shadow: none !important;
                    transform: none !important;
                }
                </style>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            if st.button("Access Dashboard", key="access_dashboard_btn", use_container_width=True, on_click=handle_login):
                pass

            st.markdown("<div style='text-align: center; padding: 24px 0 16px; margin: 0; color: #64748b; font-weight: bold; font-size: 1.1rem; letter-spacing: 1.5px;'>— OR —</div>", unsafe_allow_html=True)

            try:
                auth_url = get_google_auth_url()
                st.markdown(f'''
                    <div class="google-signin-wrapper">
                        <a href="{auth_url}" target="_self">
                            <button>Sign in with Google</button>
                        </a>
                    </div>
                ''', unsafe_allow_html=True)
            except Exception as e:
                st.error("Google login currently unavailable.")

            st.markdown("<div class='login-footer-spacer'></div>", unsafe_allow_html=True)
            if st.button("← Return to Home", key="back_home", use_container_width=True):
                st.session_state.show_login = False
                st.rerun()


if __name__ == "__main__":
    main()
