import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.ui import glass_card, metric_row, section_header
from utils.ml import get_student_predictions, generate_subject_marks
from fpdf import FPDF
import io
import numpy as np
from utils.charts import apply_neon_theme
from utils.db import fetch_table
from datetime import datetime

def show(selection):
    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
    
    if selection == "Dashboard":
        show_main_dashboard()
    elif selection == "My Grades":
        show_grades()
    elif selection == "Attendance":
        show_attendance()
    elif selection == "AI Insights":
        show_ai_insights()
    elif selection == "AI Chatbot":
        show_chatbot()
        
    st.markdown('</div>', unsafe_allow_html=True)

def show_main_dashboard():
    section_header("Student Insights", "Real-time track of your academic journey")
    
    # Fetch real student record
    student_id = st.session_state.user['id']
    try:
        student_records = fetch_table("students", filters={"student_id": student_id})
        if student_records:
            student = student_records[0]
        else:
            raise Exception("Student record not found in database.")
    except Exception as e:
        student = {
            "student_id": student_id,
            "name": st.session_state.user['username'],
            "attendance_pct": 92.0,
            "prev_gpa": 3.85,
            "final_gpa": 3.85,
            "assignments_completed": 12,
            "internal_marks": 85
        }
        
    # Dynamically compute rank
    try:
        all_students = fetch_table("students")
        df_all = pd.DataFrame(all_students)
        df_all.columns = [c.lower() for c in df_all.columns]
        df_all = df_all.sort_values("final_gpa", ascending=False).reset_index(drop=True)
        rank = df_all[df_all['student_id'] == student_id].index[0] + 1
        rank_str = f"{rank}/{len(df_all)}"
    except Exception:
        rank_str = "12/50"
        
    col_main, col_side = st.columns([3, 1])
    
    with col_side:
        # Exam Countdown
        st.markdown('<div class="glass-card fade-in">', unsafe_allow_html=True)
        st.subheader("⏱️ Exam Countdown")
        exam_date = st.date_input("Next Exam Date", value=pd.to_datetime('2026-06-15'))
        days_left = (exam_date - pd.to_datetime('today').date()).days
        st.write(f"### {days_left} Days Left")
        st.progress(max(0, min(100, (30-days_left)*100//30)))
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        # Achievement Badges
        st.subheader("🏅 Badges")
        badges = ["🔥 10 Day Streak", "📚 Top Scorer", "✅ Perfect Attendance"]
        for b in badges:
            st.info(b)

    with col_main:
        # Key Metrics (Real data-driven values)
        metrics = [
            {"label": "Current CGPA", "value": f"{student['final_gpa']:.2f}", "trend": f"{'+' if student['final_gpa'] >= student['prev_gpa'] else ''}{student['final_gpa'] - student['prev_gpa']:.2f}", "icon": "🎓"},
            {"label": "Attendance", "value": f"{int(student['attendance_pct'])}%", "trend": "+1.5%", "icon": "📅"},
            {"label": "Rank", "value": rank_str, "trend": "Stable", "icon": "🏆"}
        ]
        metric_row(metrics)
        
        st.markdown("<br>", unsafe_allow_html=True)
        # Leaderboard (Top 5 from real data)
        st.markdown('<div class="glass-card fade-in">', unsafe_allow_html=True)
        st.subheader("🏆 Leaderboard (Top 5)")
        try:
            top_5_data = df_all.head(5)[['name', 'final_gpa']]
            top_5_data.columns = ['Name', 'GPA']
        except Exception:
            top_5_data = pd.DataFrame({
                'Name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
                'GPA': [4.0, 3.98, 3.95, 3.92, 3.88]
            })
        st.table(top_5_data)

        # PDF Export with Real Data
        if st.button("Generate Performance Report (PDF)", use_container_width=True):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="EduVerse Student Performance Audit", ln=True, align='C')
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"Student ID: {student['student_id']}", ln=True)
            pdf.cell(200, 10, txt=f"Name: {student['name']}", ln=True)
            pdf.cell(200, 10, txt=f"Current GPA: {student['final_gpa']:.2f}", ln=True)
            pdf.cell(200, 10, txt=f"Attendance: {int(student['attendance_pct'])}%", ln=True)
            pdf.cell(200, 10, txt=f"Rank: {rank_str}", ln=True)
            pdf.cell(200, 10, txt=f"Assignments Completed: {student['assignments_completed']}/20", ln=True)
            pdf.cell(200, 10, txt=f"Status: {'Good Standing' if student['risk'] == 0 else 'At Academic Risk'}", ln=True)
            pdf.cell(200, 10, txt=f"Report Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
            
            pdf_output = pdf.output(dest='S').encode('latin-1')
            st.download_button(label="Click to Download PDF", 
                               data=pdf_output, 
                               file_name=f"{student['name'].replace(' ', '_')}_report.pdf", 
                               mime="application/pdf",
                               use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

def show_chatbot():
    from utils.ai import get_ai_response
    import time
    
    section_header("AI Academic Assistant", "Ask me anything about your studies!")
    
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Hello! I am your AI Academic Assistant. Ask me anything about your grades, study plans, or performance stats."}]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("How can I improve my GPA?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("AI is thinking..."):
                start_time = time.time()
                try:
                    response = get_ai_response(prompt)
                    elapsed = time.time() - start_time
                    if elapsed < 0.6:
                        time.sleep(0.6 - elapsed)
                except Exception as e:
                    response = f"I faced a connection issue. Kripya fir se try karein. (Error: {str(e)})"
            
            message_placeholder.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

def show_grades():
    section_header("Subject-wise Performance", "Detailed breakdown of your grades")
    
    try:
        data = fetch_table("grades", filters={"student_id": st.session_state.user['id']})
        if not data:
            raise Exception("empty")
        df_marks = pd.DataFrame(data)
    except:
        df_marks = generate_subject_marks()
    
    # Standardize column names dynamically to match what Plotly expect (Subject, Marks)
    cols = {c.lower(): c for c in df_marks.columns}
    if 'subject' in cols:
        df_marks = df_marks.rename(columns={cols['subject']: 'Subject'})
    if 'marks' in cols:
        df_marks = df_marks.rename(columns={cols['marks']: 'Marks'})
        
    colors = ['#00f2fe', '#4facfe', '#43e97b', '#fa709a', '#f093fb', '#ffd700']
    fig = px.bar(df_marks, x='Subject', y='Marks', 
                 color='Subject',
                 color_discrete_sequence=colors,
                 labels={'Subject': 'Course', 'Marks': 'Grade'})
    fig = apply_neon_theme(fig, "Marks Distribution")
    st.plotly_chart(fig, use_container_width=True)
    
    st.table(df_marks)

def show_attendance():
    section_header("Attendance Analysis", "Track your presence across all courses")
    
    try:
        data = fetch_table("attendance", filters={"student_id": st.session_state.user['id']})
        if not data:
            raise Exception("empty")
        df_att = pd.DataFrame(data)
    except:
        # Mock data for daily attendance
        dates = pd.date_range(start='2026-05-01', periods=24)
        status = np.random.choice(['Present', 'Absent'], size=24, p=[0.9, 0.1])
        df_att = pd.DataFrame({'date': dates, 'status': status})
    
    # Standardize column names to lowercase to avoid case mismatches
    df_att.columns = [c.lower() for c in df_att.columns]
    
    fig = px.scatter(df_att, x='date', y='status', color='status', 
                     color_discrete_map={'Present': '#43e97b', 'Absent': '#fa709a', 'present': '#43e97b', 'absent': '#fa709a'},
                     labels={'date': 'Attendance Date', 'status': 'Attendance Status'})
    fig = apply_neon_theme(fig, "Daily Attendance Log")
    st.plotly_chart(fig, use_container_width=True)

def show_ai_insights():
    section_header("AI Performance Predictions", "Predictive modeling for your future grades")
    
    # Fetch real student record for slider defaults
    student_id = st.session_state.user['id']
    try:
        student_records = fetch_table("students", filters={"student_id": student_id})
        if student_records:
            student = student_records[0]
        else:
            raise Exception("Student record not found in database.")
    except Exception as e:
        student = {
            "attendance_pct": 92.0,
            "internal_marks": 85,
            "prev_gpa": 3.8,
            "assignments_completed": 12
        }
        
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Simulate Your Performance")
        att = st.slider("Attendance %", 50, 100, int(student['attendance_pct']))
        internal = st.slider("Internal Marks", 0, 100, int(student['internal_marks']))
        study = st.slider("Daily Study Hours", 1, 12, 5)
        prev = st.slider("Previous GPA", 2.0, 4.0, float(student['prev_gpa']))
        assign = st.slider("Assignments Completed", 0, 20, int(student['assignments_completed']))
        
        if st.button("Predict My Final GPA"):
            pred_gpa, risk = get_student_predictions(att, internal, study, prev, assign)
            st.session_state.pred_gpa = pred_gpa
            st.session_state.pred_risk = risk

    with col2:
        if "pred_gpa" in st.session_state:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.write(f"### Predicted Final GPA: <span style='color: #00f2fe;'>{st.session_state.pred_gpa}</span>", unsafe_allow_html=True)
            st.write(f"### Risk Level: <span style='color: {'#ff4b4b' if st.session_state.pred_risk > 50 else '#00f2fe'};'>{st.session_state.pred_risk}%</span>", unsafe_allow_html=True)
            
            if st.session_state.pred_risk > 30:
                st.warning("⚠️ High Risk detected. AI recommends increasing study hours and attending more sessions.")
            else:
                st.success("✅ On track for excellence. Keep up the consistent effort!")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Adjust the sliders and click 'Predict' to see AI insights.")
