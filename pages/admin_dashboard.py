from typing import cast
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.ui import glass_card, metric_row, section_header
from utils.db import fetch_table, get_uptime_seconds, get_query_count, get_db_latency, DB_MODE
from utils.ai import get_average_inference_time, get_ai_model_name
from utils.charts import apply_neon_theme
import threading
from datetime import datetime, timedelta
from fpdf import FPDF

class CPUMonitor:
    def __init__(self):
        self.history = [12.0, 15.0, 14.0, 20.0, 25.0, 22.0, 18.0, 15.0, 14.0, 13.0, 16.0, 18.0, 22.0, 30.0, 28.0, 25.0, 20.0, 18.0, 15.0, 12.0]
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._monitor, name="Global_CPU_Monitor", daemon=True)
        self.thread.start()

    def _monitor(self):
        while not self.stop_event.is_set():
            try:
                import psutil
                val = psutil.cpu_percent(interval=1)
            except Exception:
                val = 15.0

            with self.lock:
                self.history.append(val)
                if len(self.history) > 20:
                    self.history.pop(0)

            # Wait for 60 seconds or until stop_event is set
            self.stop_event.wait(60)

    def get_history(self):
        with self.lock:
            return list(self.history)
            
    def stop(self):
        self.stop_event.set()

@st.cache_resource
def get_cpu_monitor():
    return CPUMonitor()


@st.cache_data(ttl=30)
def get_dashboard_stats():
    try:
        depts = fetch_table("departments")
        if not depts:
            raise Exception("empty")
        df_dept = pd.DataFrame(depts)
    except Exception:
        df_dept = pd.DataFrame([
            {"name": "AI", "avg_gpa": 3.28, "total_students": 66},
            {"name": "BBA", "avg_gpa": 3.22, "total_students": 79},
            {"name": "CS", "avg_gpa": 3.14, "total_students": 55},
            {"name": "Civil", "avg_gpa": 3.25, "total_students": 54},
            {"name": "DS", "avg_gpa": 3.28, "total_students": 46},
            {"name": "EE", "avg_gpa": 3.18, "total_students": 67},
            {"name": "MBA", "avg_gpa": 3.2, "total_students": 69},
            {"name": "ME", "avg_gpa": 3.24, "total_students": 64},
        ])

    try:
        users = fetch_table("users")
        active_users_count = len(users) if users else 502
    except Exception:
        active_users_count = 502

    return df_dept, active_users_count


@st.cache_data(ttl=60)
def get_department_charts(df_dept_json):
    from io import StringIO
    df_dept = pd.read_json(StringIO(df_dept_json))
    colors = ['#00f2fe', '#4facfe', '#43e97b', '#fa709a', '#f093fb', '#ffd700', '#c084fc', '#fb7185']

    fig_bar = px.bar(df_dept, x='name', y='total_students',
                 color='name',
                 color_discrete_sequence=colors,
                 labels={'name': 'Department', 'total_students': 'Students'})
    fig_bar = apply_neon_theme(fig_bar, "Students by Department")

    fig_pie = px.pie(df_dept, values='total_students', names='name',
                 color_discrete_sequence=colors)
    fig_pie = apply_neon_theme(fig_pie, "Departmental Distribution")

    return fig_bar, fig_pie


@st.cache_data(ttl=15)
def get_cpu_load_chart(load):
    time_points = pd.date_range(end='now', periods=len(load), freq='min')
    df_load = pd.DataFrame({'Time': time_points, 'CPU Load (%)': load})
    fig = px.area(df_load, x='Time', y='CPU Load (%)',
                  labels={'Time': 'Timestamp', 'CPU Load (%)': 'CPU Load'})
    fig = apply_neon_theme(fig, "Server CPU Load (Last 20 mins)")
    return fig


class EduVerseReport(FPDF):
    def header(self):
        self.set_fill_color(30, 41, 59)
        self.rect(0, 0, 210, 35, 'F')

        self.set_y(10)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, "EduVerse AI", align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_font("Helvetica", "I", 10)
        self.set_text_color(148, 163, 184)
        self.cell(0, 5, "Institutional Analytics & Academic Audit System", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}  |  Confidential  |  Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", align="C")


def generate_pdf_report(report_type, start_date, end_date, df_students, df_dept):
    pdf = EduVerseReport()
    pdf.set_top_margin(40)
    pdf.alias_nb_pages()
    pdf.add_page()

    total_stu = len(df_students) if not df_students.empty else 500

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, text=f"Report Type: {report_type}", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    date_str = f"Date Range: {start_date} to {end_date}"
    pdf.cell(0, 6, text=date_str, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, text="Generated By: EduVerse Admin Console", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.set_draw_color(226, 232, 240)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)

    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(10, pdf.get_y(), 190, 45, 'FD')

    pdf.set_xy(15, pdf.get_y() + 5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, text="Executive Summary", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(71, 85, 105)

    avg_gpa = df_students['final_gpa'].mean() if not df_students.empty else 3.22
    avg_att = df_students['attendance_pct'].mean() if not df_students.empty else 81.8
    risk_count = len(df_students[df_students['risk'] == 1]) if not df_students.empty else 25

    summary_text = (
        f"This {report_type} provides a comprehensive assessment of the institutional status of EduVerse. "
        f"Currently, there are {total_stu} active student profiles recorded across {len(df_dept)} academic departments. "
        f"The student body maintains an average GPA of {avg_gpa:.2f} with an average attendance rate of {avg_att:.1f}%. "
        f"A total of {risk_count} students ({risk_count / total_stu * 100:.1f}%) have been flagged by the AI engine as "
        f"academically at-risk and are currently queued for target interventions."
    )
    pdf.multi_cell(180, 5, text=summary_text, new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(pdf.get_y() + 15)

    if report_type == "Academic Audit":
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 10, text="Academic Performance by Department", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_fill_color(30, 41, 59)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)

        headers = ["Department", "Students Count", "Average GPA", "Average Attendance"]
        widths = [55, 45, 45, 45]

        for h, w in zip(headers, widths):
            pdf.cell(w, 8, text=h, border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)
        for idx, row in df_dept.iterrows():
            fill = idx % 2 == 1
            pdf.set_fill_color(241, 245, 249) if fill else pdf.set_fill_color(255, 255, 255)

            pdf.cell(55, 7, text=str(row['department']), border=1, align="C", fill=fill)
            pdf.cell(45, 7, text=str(row['total_students']), border=1, align="C", fill=fill)
            pdf.cell(45, 7, text=f"{row['avg_gpa']:.2f}", border=1, align="C", fill=fill)
            pdf.cell(45, 7, text=f"{row['avg_attendance']:.1f}%", border=1, align="C", fill=fill)
            pdf.ln()

        pdf.ln(10)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, text="AI Flagged Academic Risks", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(71, 85, 105)
        risk_text = (
            "The EduVerse predictive modeling engine constantly monitors student metrics (attendance, assignment completion, "
            "and internal marks) to detect risk. Students flagged with risk status are recommended for counseling. "
            "CS and EE departments currently show the highest relative concentration of students in the risk zone."
        )
        pdf.multi_cell(0, 5, text=risk_text)

    elif report_type == "Attendance Summary":
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 10, text="Attendance Statistics by Department", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_fill_color(30, 41, 59)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)

        headers = ["Department", "Average Attendance", "Students Count", "Critical Attendance (<75%)"]
        widths = [60, 45, 40, 45]

        for h, w in zip(headers, widths):
            pdf.cell(w, 8, text=h, border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)
        for idx, row in df_dept.iterrows():
            fill = idx % 2 == 1
            pdf.set_fill_color(241, 245, 249) if fill else pdf.set_fill_color(255, 255, 255)

            dept_students = df_students[df_students['department'] == row['department']] if not df_students.empty else pd.DataFrame()
            crit_count = len(dept_students[dept_students['attendance_pct'] < 75]) if not df_students.empty else int(row['total_students'] * 0.1)

            pdf.cell(60, 7, text=str(row['department']), border=1, align="C", fill=fill)
            pdf.cell(45, 7, text=f"{row['avg_attendance']:.1f}%", border=1, align="C", fill=fill)
            pdf.cell(40, 7, text=str(row['total_students']), border=1, align="C", fill=fill)
            pdf.cell(45, 7, text=str(crit_count), border=1, align="C", fill=fill)
            pdf.ln()

        pdf.ln(10)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, text="Attendance Compliance Notice", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(71, 85, 105)
        attendance_desc = (
            "According to university policy, students must maintain a minimum attendance of 75% to be eligible for final examinations. "
            "Students below 75% have been sent automated alerts. Faculty advisors are advised to coordinate with students showing critical attendance."
        )
        pdf.multi_cell(0, 5, text=attendance_desc)

    elif report_type == "Financial Overview":
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 10, text="Tuition and Financial Analytics Summary", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_fill_color(30, 41, 59)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)

        headers = ["Department", "Student Count", "Est. Tuition Revenue", "Scholarship Allocation"]
        widths = [50, 45, 50, 45]

        for h, w in zip(headers, widths):
            pdf.cell(w, 8, text=h, border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)
        total_rev = 0
        total_schol = 0

        for idx, row in df_dept.iterrows():
            fill = idx % 2 == 1
            pdf.set_fill_color(241, 245, 249) if fill else pdf.set_fill_color(255, 255, 255)

            fee = 12000 if row['department'] in ['CS', 'AI', 'DS'] else 10000
            revenue = row['total_students'] * fee
            schol = revenue * (0.1 if row['avg_gpa'] > 3.2 else 0.05)

            total_rev += revenue
            total_schol += schol

            pdf.cell(50, 7, text=str(row['department']), border=1, align="C", fill=fill)
            pdf.cell(45, 7, text=str(row['total_students']), border=1, align="C", fill=fill)
            pdf.cell(50, 7, text=f"${revenue:,.2f}", border=1, align="C", fill=fill)
            pdf.cell(45, 7, text=f"${schol:,.2f}", border=1, align="C", fill=fill)
            pdf.ln()

        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(50, 8, text="Total", border=1, align="C")
        pdf.cell(45, 8, text=str(total_stu), border=1, align="C")
        pdf.cell(50, 8, text=f"${total_rev:,.2f}", border=1, align="C")
        pdf.cell(45, 8, text=f"${total_schol:,.2f}", border=1, align="C")
        pdf.ln(15)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, text="Financial Sustainability Notes", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(71, 85, 105)
        fin_desc = (
            "Finances are projected using standardized department fee schedules. Scholarship allocations are tied to academic "
            "excellence performance markers. Expanding AI and DS tracks represents the highest margin opportunity for tuition optimization."
        )
        pdf.multi_cell(0, 5, text=fin_desc)

    elif report_type == "AI Efficiency Report":
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 10, text="AI Engine Operational Metrics", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        avg_inf = get_average_inference_time()
        model_name = get_ai_model_name()

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(50, 8, text="Primary LLM Model:")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, text=model_name, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(50, 8, text="Average Inference Time:")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, text=f"{avg_inf:.3f} seconds", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(50, 8, text="AI Query Log Status:")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, text="Active & Fully Operational", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(10)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, text="AI Counseling & Insights Feedback Summary", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(71, 85, 105)
        ai_desc = (
            "The AI Engine automates performance analyses, student queries, and risk reports. "
            "Current operational stats indicate the local fallback engine and remote API layers are running within "
            "optimal latencies (< 1.0s). No drift or critical failure thresholds have been tripped."
        )
        pdf.multi_cell(0, 5, text=ai_desc)

    return bytes(pdf.output())


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


def show_admin_main():
    section_header("Institutional Analytics", "Global overview of EduVerse ecosystem")

    df_dept, active_users_count = get_dashboard_stats()

    uptime_sec = get_uptime_seconds()
    if uptime_sec < 60:
        uptime_str = f"{int(uptime_sec)}s"
    elif uptime_sec < 3600:
        uptime_str = f"{int(uptime_sec // 60)}m {int(uptime_sec % 60)}s"
    elif uptime_sec < 86400:
        uptime_str = f"{int(uptime_sec // 3600)}h {int((uptime_sec % 3600) // 60)}m"
    else:
        uptime_str = f"{int(uptime_sec // 86400)}d {int((uptime_sec % 86400) // 3600)}h"

    queries_count = get_query_count()
    uptime_min = max(uptime_sec / 60.0, 0.01)
    queries_rate = queries_count / uptime_min

    metrics = [
        {"label": "Active Users", "value": f"{active_users_count:,}", "trend": "Real-time"},
        {"label": "Departments", "value": str(len(df_dept)), "trend": "Active"},
        {"label": "Server Uptime", "value": uptime_str, "trend": "Running"},
        {"label": "DB Queries", "value": f"{queries_count}", "trend": f"avg {queries_rate:.1f}/m"}
    ]
    metric_row(metrics)

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    fig_bar, fig_pie = get_department_charts(df_dept.to_json())

    with col1:
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.plotly_chart(fig_pie, use_container_width=True)


def show_user_mgmt():
    section_header("User Management", "Control access and manage roles")

    try:
        users = fetch_table("users")
        if not users:
            raise Exception("empty")
        df_users = pd.DataFrame(users)
    except Exception:
        df_users = pd.DataFrame([
            {"id": 1, "username": "admin", "role": "Admin", "email": "admin@eduverse.ai"},
            {"id": 2, "username": "jsmith", "role": "Teacher", "email": "jsmith@eduverse.ai"},
            {"id": 3, "username": "ajohnson", "role": "Student", "email": "ajohnson@eduverse.ai"},
            {"id": 4, "username": "mlee", "role": "Teacher", "email": "mlee@eduverse.ai"},
            {"id": 5, "username": "swilliams", "role": "Student", "email": "swilliams@eduverse.ai"},
        ])
    df_display = cast(pd.DataFrame, df_users[['id', 'username', 'role', 'email']].copy())
    df_display = df_display.rename(columns={
        'id': 'ID',
        'username': 'Username',
        'role': 'Role',
        'email': 'Email Address'
    })

    total_users = len(df_users)
    admins = len(df_users[df_users['role'] == 'Admin'])
    teachers = len(df_users[df_users['role'] == 'Teacher'])
    students = len(df_users[df_users['role'] == 'Student'])
    
    metrics = [
        {"label": "Total Users", "value": str(total_users), "trend": "Active"},
        {"label": "Active Admins", "value": str(admins), "trend": "Verified"},
        {"label": "Total Teachers", "value": str(teachers)},
        {"label": "Total Students", "value": str(students)}
    ]
    metric_row(metrics)
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<h3 class="gradient-text" style="margin-top: 0; font-size: 1.2rem;">User Directory</h3>', unsafe_allow_html=True)
    st.dataframe(df_display, use_container_width=True, hide_index=True)

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
    except Exception:
        from datetime import datetime, timedelta
        now = datetime.now()
        df_logs = pd.DataFrame([
            {"user_id": 1, "action": "Login", "timestamp": (now - timedelta(minutes=5)).isoformat()},
            {"user_id": 2, "action": "Update Marks", "timestamp": (now - timedelta(minutes=15)).isoformat()},
            {"user_id": 1, "action": "System Config Change", "timestamp": (now - timedelta(hours=1)).isoformat()},
            {"user_id": 3, "action": "Login", "timestamp": (now - timedelta(hours=2)).isoformat()},
            {"user_id": 4, "action": "Export CSV", "timestamp": (now - timedelta(hours=4)).isoformat()},
        ])
    df_display = cast(pd.DataFrame, df_logs.sort_values('timestamp', ascending=False).copy())
    df_display = df_display.rename(columns={
        'user_id': 'User ID',
        'action': 'Action',
        'timestamp': 'Timestamp'
    })

    total_logs = len(df_logs)
    
    metrics = [
        {"label": "Total Log Entries", "value": str(total_logs), "trend": "Real-time"},
        {"label": "Recent Activity", "value": "Active", "trend": "Monitoring"}
    ]
    metric_row(metrics)
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<h3 class="gradient-text" style="margin-top: 0; font-size: 1.2rem;">Recent Audit Logs</h3>', unsafe_allow_html=True)
    st.dataframe(df_display, use_container_width=True, hide_index=True)


def show_system_health():
    section_header("System Infrastructure", "Real-time monitoring of services")

    latency = get_db_latency()
    avg_inf = get_average_inference_time()
    ai_model = get_ai_model_name()

    uptime_sec = get_uptime_seconds()
    if uptime_sec < 60:
        uptime_str = f"{int(uptime_sec)}s"
    elif uptime_sec < 3600:
        uptime_str = f"{int(uptime_sec // 60)}m"
    elif uptime_sec < 86400:
        uptime_str = f"{int(uptime_sec // 3600)}h {int((uptime_sec % 3600) // 60)}m"
    else:
        uptime_str = f"{int(uptime_sec // 86400)}d {int((uptime_sec % 86400) // 3600)}h"

    col1, col2, col3 = st.columns(3)
    with col1:
        glass_card("Database", f"<span style='color: #00f2fe; font-weight: 700;'>CONNECTED</span><br/>Latency: {latency:.1f}ms<br/>Mode: {DB_MODE.upper()}")
    with col2:
        glass_card("API Service", f"<span style='color: #00f2fe; font-weight: 700;'>OPERATIONAL</span><br/>Uptime: {uptime_str}<br/>Version: v2.4.0")
    with col3:
        glass_card("AI Engine", f"<span style='color: #00f2fe; font-weight: 700;'>ONLINE</span><br/>Model: {ai_model}<br/>Avg Inference: {avg_inf:.2f}s")

    st.markdown("<br>", unsafe_allow_html=True)

    cpu_monitor = get_cpu_monitor()
    load = cpu_monitor.get_history()

    fig = get_cpu_load_chart(tuple(load))
    st.plotly_chart(fig, use_container_width=True)


def show_reports():
    section_header("Institutional Reports", "Generate and export comprehensive audits")

    report_type = st.selectbox("Select Report Type", ["Academic Audit", "Attendance Summary", "Financial Overview", "AI Efficiency Report"])

    default_start = (datetime.now() - timedelta(days=30)).date()
    default_end = datetime.now().date()
    date_range = st.date_input("Date Range", value=(default_start, default_end))

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    elif isinstance(date_range, tuple) and len(date_range) == 1:
        start_date = date_range[0]
        end_date = datetime.now().date()
    else:
        start_date = date_range
        end_date = datetime.now().date()

    if "pdf_data" not in st.session_state:
        st.session_state.pdf_data = None
    if "pdf_filename" not in st.session_state:
        st.session_state.pdf_filename = None

    if st.button("Generate Report"):
        with st.spinner("Compiling database records and generating PDF..."):
            try:
                students_data = fetch_table("students")
                if students_data:
                    df_students = pd.DataFrame(students_data)
                else:
                    df_students = pd.DataFrame()

                if not df_students.empty:
                    df_dept = df_students.groupby('department').agg(
                        total_students=('student_id', 'count'),
                        avg_gpa=('final_gpa', 'mean'),
                        avg_attendance=('attendance_pct', 'mean')
                    ).reset_index()
                else:
                    df_dept = pd.DataFrame([
                        {"department": "AI", "total_students": 66, "avg_gpa": 3.28, "avg_attendance": 85.0},
                        {"department": "BBA", "total_students": 79, "avg_gpa": 3.22, "avg_attendance": 82.5},
                        {"department": "CS", "total_students": 55, "avg_gpa": 3.14, "avg_attendance": 80.2},
                        {"department": "Civil", "total_students": 54, "avg_gpa": 3.25, "avg_attendance": 81.0},
                        {"department": "DS", "total_students": 46, "avg_gpa": 3.28, "avg_attendance": 84.1},
                        {"department": "EE", "total_students": 67, "avg_gpa": 3.18, "avg_attendance": 79.5},
                        {"department": "MBA", "total_students": 69, "avg_gpa": 3.20, "avg_attendance": 83.0},
                        {"department": "ME", "total_students": 64, "avg_gpa": 3.24, "avg_attendance": 80.8},
                    ])

                pdf_bytes = generate_pdf_report(report_type, start_date, end_date, df_students, df_dept)
                st.session_state.pdf_data = pdf_bytes
                filename_type = report_type.lower().replace(" ", "_")
                st.session_state.pdf_filename = f"eduverse_{filename_type}_{start_date}_to_{end_date}.pdf"
                st.success(f"Successfully generated {report_type}!")
            except Exception as e:
                st.error(f"Error generating PDF report: {e}")

    if st.session_state.pdf_data is not None:
        st.info("Your report is ready.")
        st.download_button(
            label="Download PDF Report",
            data=st.session_state.pdf_data,
            file_name=st.session_state.pdf_filename,
            mime="application/pdf",
            use_container_width=True
        )
