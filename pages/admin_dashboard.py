import streamlit as st
import pandas as pd
import plotly.express as px
from utils.ui import glass_card, metric_row, section_header
from utils.db import fetch_table

def show(selection):
    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
    
    if selection == "Dashboard":
        show_admin_main()
    elif selection == "User Management":
        show_user_mgmt()
    elif selection == "System Health":
        show_system_health()
    elif selection == "Reports":
        show_reports()
    elif selection == "Audit Logs":
        show_audit_logs()
        
    st.markdown('</div>', unsafe_allow_html=True)

from utils.charts import apply_neon_theme

def show_admin_main():
    section_header("Institutional Analytics", "Global overview of EduVerse ecosystem")
    
    # Fetch real data from Supabase with fallback
    try:
        depts = fetch_table("departments")
        if not depts:
            raise Exception("empty")
        df_dept = pd.DataFrame(depts)
    except:
        # Mock data as fallback
        df_dept = pd.DataFrame([
            {"name": "CS", "avg_gpa": 3.4, "total_students": 120},
            {"name": "EE", "avg_gpa": 3.2, "total_students": 95},
            {"name": "ME", "avg_gpa": 3.1, "total_students": 80},
            {"name": "Civil", "avg_gpa": 3.0, "total_students": 70},
            {"name": "AI", "avg_gpa": 3.6, "total_students": 150},
            {"name": "DS", "avg_gpa": 3.5, "total_students": 130},
        ])

    metrics = [
        {"label": "Active Users", "value": "1,240", "trend": "+15%", "icon": "👥"},
        {"label": "Departments", "value": str(len(df_dept)), "trend": "Stable", "icon": "🏫"},
        {"label": "Server Uptime", "value": "99.9%", "trend": "Optimal", "icon": "⚡"},
        {"label": "DB Queries", "value": "450/m", "trend": "+12%", "icon": "🔥"}
    ]
    metric_row(metrics)
    
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    colors = ['#00f2fe', '#4facfe', '#43e97b', '#fa709a', '#f093fb', '#ffd700']
    
    with col1:
        fig = px.bar(df_dept, x='name', y='total_students', 
                     color='name',
                     color_discrete_sequence=colors,
                     labels={'name': 'Department', 'total_students': 'Students'})
        fig = apply_neon_theme(fig, "Students by Department")
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        fig = px.pie(df_dept, values='total_students', names='name',
                     color_discrete_sequence=colors)
        fig = apply_neon_theme(fig, "Departmental Distribution")
        st.plotly_chart(fig, use_container_width=True)

def show_user_mgmt():
    section_header("User Management", "Control access and manage roles")
    
    try:
        users = fetch_table("users")
        if not users:
            raise Exception("empty")
        df_users = pd.DataFrame(users)
    except:
        df_users = pd.DataFrame([
            {"id": 1, "username": "admin", "role": "Admin", "email": "admin@eduverse.ai"},
            {"id": 2, "username": "jsmith", "role": "Teacher", "email": "jsmith@eduverse.ai"},
            {"id": 3, "username": "ajohnson", "role": "Student", "email": "ajohnson@eduverse.ai"},
            {"id": 4, "username": "mlee", "role": "Teacher", "email": "mlee@eduverse.ai"},
            {"id": 5, "username": "swilliams", "role": "Student", "email": "swilliams@eduverse.ai"},
        ])
    
    st.dataframe(df_users[['id', 'username', 'role', 'email']], use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.button("Add New User")
    with col2:
        st.button("Export User List")

def show_audit_logs():
    section_header("System Audit Logs", "Track user actions across the platform")
    try:
        logs = fetch_table("analytics_logs")
        if not logs:
            raise Exception("empty")
        df_logs = pd.DataFrame(logs)
    except:
        from datetime import datetime, timedelta
        now = datetime.now()
        df_logs = pd.DataFrame([
            {"user_id": 1, "action": "Login", "timestamp": (now - timedelta(minutes=5)).isoformat()},
            {"user_id": 2, "action": "Update Marks", "timestamp": (now - timedelta(minutes=15)).isoformat()},
            {"user_id": 1, "action": "System Config Change", "timestamp": (now - timedelta(hours=1)).isoformat()},
            {"user_id": 3, "action": "Login", "timestamp": (now - timedelta(hours=2)).isoformat()},
            {"user_id": 4, "action": "Export CSV", "timestamp": (now - timedelta(hours=4)).isoformat()},
        ])
        
    st.dataframe(df_logs.sort_values('timestamp', ascending=False), use_container_width=True)

def show_system_health():
    section_header("System Infrastructure", "Real-time monitoring of services")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        glass_card("🔗 Database", "<span style='color: #00f2fe; font-weight: 700;'>CONNECTED</span><br/>Latencey: 12ms<br/>Load: 15%")
    with col2:
        glass_card("🌐 API Service", "<span style='color: #00f2fe; font-weight: 700;'>OPERATIONAL</span><br/>Uptime: 45 days<br/>Version: v2.4.0")
    with col3:
        glass_card("🤖 AI Engine", "<span style='color: #00f2fe; font-weight: 700;'>ONLINE</span><br/>Model: EduLLM-v1<br/>Avg Inference: 0.8s")
    
    st.markdown("<br>", unsafe_allow_html=True)
    # Simple CPU load chart
    time_points = pd.date_range(start='now', periods=20, freq='min')
    load = [10, 12, 15, 14, 20, 25, 22, 18, 15, 14, 13, 16, 18, 22, 30, 28, 25, 20, 18, 15]
    df_load = pd.DataFrame({'Time': time_points, 'CPU Load (%)': load})
    fig = px.area(df_load, x='Time', y='CPU Load (%)',
                  labels={'Time': 'Timestamp', 'CPU Load (%)': 'CPU Load'})
    fig = apply_neon_theme(fig, "Server CPU Load (Last 20 mins)")
    st.plotly_chart(fig, use_container_width=True)

def show_reports():
    section_header("Institutional Reports", "Generate and export comprehensive audits")
    
    report_type = st.selectbox("Select Report Type", ["Academic Audit", "Attendance Summary", "Financial Overview", "AI Efficiency Report"])
    date_range = st.date_input("Date Range")
    
    if st.button("Generate Report"):
        st.success(f"Generated {report_type} for selected period.")
        st.info("Preparing PDF for download...")
        st.download_button("Download Report (PDF)", data="Dummy PDF Content", file_name="report.pdf")
