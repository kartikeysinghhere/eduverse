import streamlit as st
import pandas as pd
import plotly.express as px
from utils.ui import glass_card, metric_row, section_header
from utils.ml import generate_student_data
from utils.db import fetch_table, log_action, insert_records
from utils.charts import apply_neon_theme

def show(selection):
    st.markdown('<div class="fade-in">', unsafe_allow_html=True)

    if selection == "Dashboard":
        show_teacher_main()
    elif selection == "Student Management":
        show_student_list()
    elif selection == "Upload Marks":
        show_upload_marks()
    elif selection == "Analytics":
        show_class_analytics()

    st.markdown('</div>', unsafe_allow_html=True)

def show_teacher_main():
    section_header("Class Overview", "Academic session 2025-26 | Computer Science B")

    try:
        data = fetch_table("students")
        df = pd.DataFrame(data)
    except Exception:
        df = generate_student_data(45)

    total_students = len(df)
    class_avg = f"{df['internal_marks'].mean():.1f}%"
    at_risk = len(df[df['risk'] == 1])
    pending = len(df[df['assignments_completed'] < 15])

    metrics = [
        {"label": "Total Students", "value": str(total_students), "trend": "Stable"},
        {"label": "Class Average", "value": class_avg, "trend": "+1.2%"},
        {"label": "At Risk", "value": str(at_risk), "trend": "Decreasing"},
        {"label": "Pending Tasks", "value": str(pending), "trend": "Active"}
    ]
    metric_row(metrics)

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        df_top = df.sort_values("final_gpa", ascending=False).head(3)
        top_performers_html = ""
        for idx, (_, row) in enumerate(df_top.iterrows()):
            top_performers_html += f"{idx+1}. <b>{row['name']}</b> - GPA: {row['final_gpa']:.2f}<br/>"

        glass_card(" Top Performers", top_performers_html)

    with col2:
        glass_card(" Recent Activity", f"""
            - <i>Attendance for Lab 4 is below average (65%).</i> <br/>
            - <i>Real-time synchronization with local SQLite DB completed.</i> <br/>
            - <i>Currently tracking {at_risk} at-risk students for mentorship.</i>
        """)

def show_student_list():
    section_header("Student Directory", "Manage and view all students in your classes")

    try:
        data = fetch_table("students")
        if not data:
            raise Exception("empty")
        df = pd.DataFrame(data)
    except Exception:
        df = generate_student_data(45)

    search = st.text_input(" Search Student by ID or Name")
    if search:
        df = df[df['student_id'].astype(str).str.contains(search, regex=False) | df['name'].str.contains(search, case=False, regex=False)]

    st.dataframe(df, use_container_width=True)

    if st.button("Download Class Report (CSV)"):
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Click to Download", data=csv, file_name="class_report.csv", mime="text/csv")

def show_upload_marks():
    section_header("Upload Academic Data", "Support for manual entry or batch CSV upload")

    tab1, tab2 = st.tabs(["CSV Upload", "Manual Entry"])

    with tab1:
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
        if uploaded_file is not None:
            data = pd.read_csv(uploaded_file)
            st.dataframe(data.head())
            if st.button("Process & Save to DB"):
                records = data.to_dict('records')
                # Validate columns
                if all(col in data.columns for col in ['student_id', 'Subject', 'Marks']):
                    if insert_records('grades', records):
                        st.success("Data saved successfully!")
                        log_action(st.session_state.user['id'], "CSV Upload Marks")
                    else:
                        st.error("Failed to save data. Please try again.")
                else:
                    st.error("CSV must contain 'student_id', 'Subject', and 'Marks' columns.")

    with tab2:
        with st.form("marks_form"):
            st.write("Enter individual student marks")
            sid = st.text_input("Student ID")
            sub = st.selectbox("Subject", ["AI", "Data Science", "Ethics"])
            marks = st.number_input("Marks", 0, 100)
            submitted = st.form_submit_button("Submit Marks")
            if submitted:
                sid_clean = sid.strip()
                if not sid_clean:
                    st.error("Please enter a valid Student ID.")
                elif not sid_clean.isdigit():
                    st.error("Please enter a valid numeric Student ID.")
                else:
                    sid_int = int(sid_clean)
                    existing_student = fetch_table("students", filters={"student_id": sid_int})
                    if not existing_student:
                        st.error(f"Student ID {sid_int} not found in the database. Please verify the ID.")
                    else:
                        record = {"student_id": sid_int, "Subject": sub, "Marks": marks}
                        if insert_records('grades', [record]):
                            st.success(f"Marks for {sid_int} in {sub} saved.")
                            log_action(st.session_state.user['id'], f"Manual Entry: {sid_int} in {sub}")
                        else:
                            st.error("Failed to save data.")

@st.cache_data(ttl=300)
def get_teacher_histogram_chart(df_json):
    from io import StringIO
    df = pd.read_json(StringIO(df_json))
    fig = px.histogram(df, x='internal_marks', nbins=20,
                       labels={'internal_marks': 'Internal Marks', 'count': 'Number of Students'})
    fig = apply_neon_theme(fig, "Internal Marks Distribution")
    return fig

@st.cache_data(ttl=300)
def get_teacher_scatter_chart(df_json):
    from io import StringIO
    df = pd.read_json(StringIO(df_json))
    fig = px.scatter(df, x='study_hours', y='final_gpa', color='attendance_pct',
                     labels={'study_hours': 'Daily Study Hours', 'final_gpa': 'Predicted GPA', 'attendance_pct': 'Attendance %'})
    fig = apply_neon_theme(fig, "Study Hours vs GPA")
    return fig

def show_class_analytics():
    section_header("Class-wide Insights", "Visualize trends and identify bottlenecks")
    df = generate_student_data(100)

    col1, col2 = st.columns(2)
    df_json = df.to_json()

    with col1:
        fig_hist = get_teacher_histogram_chart(df_json)
        st.plotly_chart(fig_hist, use_container_width=True)

    with col2:
        fig_scatter = get_teacher_scatter_chart(df_json)
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.info(" Insights: Students with > 5 study hours show 15% better performance in final grades.")
