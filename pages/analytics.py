import streamlit as st
import pandas as pd
import plotly.express as px
from utils.ui import section_header, glass_card, metric_row
from utils.charts import apply_neon_theme
from utils.db import fetch_table

@st.cache_data(ttl=300)
def get_dept_attendance_chart(dept_att_json):
    from io import StringIO
    dept_att = pd.read_json(StringIO(dept_att_json))
    colors = ['#00f2fe', '#4facfe', '#43e97b', '#fa709a', '#f093fb', '#ffd700', '#c084fc', '#fb7185']
    fig = px.bar(dept_att, x='department', y='Attendance %',
                 color='department', color_discrete_sequence=colors,
                 labels={'department': 'Department', 'Attendance %': 'Avg Attendance %'})
    fig = apply_neon_theme(fig, "Average Attendance by Department")
    fig.update_yaxes(range=[50, 100])
    return fig

@st.cache_data(ttl=300)
def get_attendance_trend_chart(daily_att_json):
    from io import StringIO
    daily_att = pd.read_json(StringIO(daily_att_json))
    daily_att['date'] = pd.to_datetime(daily_att['date'])
    fig = px.area(daily_att, x='date', y='Attendance Rate %',
                  color_discrete_sequence=['#43e97b'])
    fig = apply_neon_theme(fig, "Daily Institutional Attendance Trend")
    fig.update_yaxes(range=[50, 100])
    return fig

@st.cache_data(ttl=300)
def get_dept_gpa_chart(dept_gpa_json):
    from io import StringIO
    dept_gpa = pd.read_json(StringIO(dept_gpa_json))
    colors = ['#00f2fe', '#4facfe', '#43e97b', '#fa709a', '#f093fb', '#ffd700', '#c084fc', '#fb7185']
    fig = px.bar(dept_gpa, x='department', y='Average GPA',
                 color='department', color_discrete_sequence=colors,
                 labels={'department': 'Department', 'Average GPA': 'Avg GPA'})
    fig = apply_neon_theme(fig, "Average GPA by Department")
    fig.update_yaxes(range=[0, 4.0])
    return fig

@st.cache_data(ttl=300)
def get_gpa_dist_chart(gpa_dist_json):
    from io import StringIO
    gpa_dist = pd.read_json(StringIO(gpa_dist_json))
    fig = px.histogram(gpa_dist, x='final_gpa', nbins=15,
                       color_discrete_sequence=['#fa709a'],
                       labels={'final_gpa': 'GPA', 'count': 'Number of Students'})
    fig = apply_neon_theme(fig, "Institutional GPA Distribution")
    return fig

def show():
    section_header("Smart Analytics", "Automated educational intelligence and predictive insights")

    # Fetch data from real SQLite database
    students_data = fetch_table("students")
    if not students_data:
        st.info("No student records found in the database. Please verify SQLite database seeding.")
        return

    df_students = pd.DataFrame(students_data)
    df_students.columns = [c.lower() for c in df_students.columns]

    # Calculate at-risk criteria dynamically (attendance below 75% or GPA below 2.5 or ML risk flag)
    df_students['is_at_risk'] = ((df_students['risk'] == 1) | (df_students['attendance_pct'] < 75.0) | (df_students['final_gpa'] < 2.5)).astype(int)
    at_risk_count = len(df_students[df_students['is_at_risk'] == 1])

    # Top Department (by GPA)
    dept_gpa = df_students.groupby('department')['final_gpa'].mean()
    top_dept = dept_gpa.idxmax()
    top_dept_gpa = dept_gpa.max()

    # Render Dashboard Summary Cards
    metrics = [
        {"label": "Total Students", "value": f"{len(df_students)}", "trend": "Stable"},
        {"label": "Average GPA", "value": f"{df_students['final_gpa'].mean():.2f}", "trend": "+0.02"},
        {"label": "Average Attendance", "value": f"{df_students['attendance_pct'].mean():.1f}%", "trend": "+0.8%"},
        {"label": "At-Risk Students", "value": f"{at_risk_count}", "trend": "Flagged"},
        {"label": "Top Department", "value": f"{top_dept}", "trend": f"{top_dept_gpa:.2f} Avg"}
    ]
    metric_row(metrics)

    st.markdown("<br>", unsafe_allow_html=True)

    # AI Insights Panel
    dept_att = df_students.groupby('department')['attendance_pct'].mean()
    max_att_dept = dept_att.idxmax()
    max_att_val = dept_att.max()
    min_att_dept = dept_att.idxmin()
    min_att_val = dept_att.min()
    low_att_count = len(df_students[df_students['attendance_pct'] < 75.0])

    insights_html = f"""
    <ul style="color: #cbd5e1; font-size: 1rem; line-height: 1.6; padding-left: 20px;">
        <li style="margin-bottom: 8px;"><b>Departmental GPA:</b> The <b>{top_dept}</b> department holds the highest academic rank with an average GPA of <b>{top_dept_gpa:.2f}</b>.</li>
        <li style="margin-bottom: 8px;"><b>Optimal Attendance:</b> The <b>{max_att_dept}</b> department leads attendance compliance at <b>{max_att_val:.1f}%</b>.</li>
        <li style="margin-bottom: 8px;"><b>Low Attendance Alert:</b> The <b>{min_att_dept}</b> department has the lowest average attendance at <b>{min_att_val:.1f}%</b>.</li>
        <li style="margin-bottom: 8px;"><b>Risk Profiling:</b> <b>{at_risk_count}</b> students are flagged as academically at-risk, and <b>{low_att_count}</b> students have attendance below the 75% threshold.</li>
    </ul>
    """
    glass_card("AI Automated Insights", insights_html)

    st.markdown("<br>", unsafe_allow_html=True)

    # 1. At-Risk Students & Top Performers Tables
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Flagged At-Risk Students (Top 10)")
        df_risk = df_students[df_students['is_at_risk'] == 1].sort_values(
            by=['final_gpa', 'attendance_pct'], ascending=[True, True]
        ).head(10)[['name', 'department', 'final_gpa', 'attendance_pct']]
        df_risk.columns = ['Name', 'Department', 'GPA', 'Attendance']
        st.dataframe(df_risk, use_container_width=True, hide_index=True)
        
    with col2:
        st.subheader("Institutional Top Performers")
        depts_list = ["All Departments"] + sorted(list(df_students['department'].unique()))
        selected_dept = st.selectbox("Department Filter", depts_list)
        
        if selected_dept == "All Departments":
            df_top = df_students.sort_values(by='final_gpa', ascending=False).head(10)
        else:
            df_top = df_students[df_students['department'] == selected_dept].sort_values(
                by='final_gpa', ascending=False
            ).head(10)
            
        df_top_display = df_top[['name', 'department', 'final_gpa', 'attendance_pct']].copy()
        df_top_display.columns = ['Name', 'Department', 'GPA', 'Attendance']
        st.dataframe(df_top_display, use_container_width=True, hide_index=True)

    st.markdown("<br><hr style='border-color: rgba(255,255,255,0.08);'><br>", unsafe_allow_html=True)

    # 2. Charts Sections
    tab_att, tab_acad = st.tabs(["Attendance Analytics", "Academic Performance Analytics"])

    with tab_att:
        col_att1, col_att2 = st.columns(2)
        with col_att1:
            # Average attendance by department
            dept_att_df = df_students.groupby('department')['attendance_pct'].mean().reset_index(name='Attendance %')
            fig_dept_att = get_dept_attendance_chart(dept_att_df.to_json())
            st.plotly_chart(fig_dept_att, use_container_width=True)
            
        with col_att2:
            # Attendance Trend Chart
            df_att = pd.DataFrame(fetch_table("attendance"))
            if not df_att.empty:
                df_att.columns = [c.lower() for c in df_att.columns]
                df_att['date'] = pd.to_datetime(df_att['date'])
                
                # Group by Date and calculate rate (optimised to avoid groupby.apply warning)
                df_att['is_present'] = (df_att['status'].str.strip().str.capitalize() == 'Present').astype(int)
                daily_att = df_att.groupby('date')['is_present'].mean().reset_index(name='Attendance Rate %')
                daily_att['Attendance Rate %'] = daily_att['Attendance Rate %'] * 100
                
                fig_trend = get_attendance_trend_chart(daily_att.to_json())
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.write("No attendance logs available for trend.")

    with tab_acad:
        col_ac1, col_ac2 = st.columns(2)
        with col_ac1:
            # Average GPA by department
            dept_gpa_df = df_students.groupby('department')['final_gpa'].mean().reset_index(name='Average GPA')
            fig_dept_gpa = get_dept_gpa_chart(dept_gpa_df.to_json())
            st.plotly_chart(fig_dept_gpa, use_container_width=True)
            
        with col_ac2:
            # Grade distribution
            gpa_dist_df = df_students[['final_gpa']].copy()
            fig_dist = get_gpa_dist_chart(gpa_dist_df.to_json())
            st.plotly_chart(fig_dist, use_container_width=True)

    st.markdown("<br><hr style='border-color: rgba(255,255,255,0.08);'><br>", unsafe_allow_html=True)

    # 3. Smart Recommendations
    st.markdown("### AI Smart Recommendations")
    rec1 = f"<b>Mentorship Drive:</b> Schedule targeted counseling sessions for the <b>{at_risk_count}</b> flagged at-risk students immediately."
    rec2 = f"<b>Attendance Intervention:</b> Issue automated compliance warnings to the <b>{low_att_count}</b> students with attendance below 75%."
    
    top_performer = df_students.sort_values(by='final_gpa', ascending=False).iloc[0]
    if not df_students.empty:
        rec3 = f"<b>Academic Recognition:</b> Recognize top-performing students on the Dean's List (led by <b>{top_performer['name']}</b> with a GPA of <b>{top_performer['final_gpa']:.2f}</b>)."
    
    col_rec1, col_rec2, col_rec3 = st.columns(3)
    with col_rec1:
        glass_card("Mentorship", rec1)
    with col_rec2:
        glass_card("Attendance Warning", rec2)
    with col_rec3:
        glass_card("Excellence Recognition", rec3)
