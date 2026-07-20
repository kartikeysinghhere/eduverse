import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import html
from utils.ui import glass_card, metric_row, section_header
from utils.ml import get_student_predictions, train_predictive_models
from utils.charts import apply_neon_theme

@st.cache_data(ttl=300)
def load_sample_data(csv_path):
    return pd.read_csv(csv_path)

@st.cache_data(ttl=300)
def get_insights_scatter_chart(df_json):
    from io import StringIO
    df = pd.read_json(StringIO(df_json))
    colors = ['#00f2fe', '#4facfe', '#43e97b', '#fa709a', '#f093fb', '#ffd700']
    fig = px.scatter(df, x='attendance_pct', y='prev_gpa', color='department',
                     color_discrete_sequence=colors,
                     labels={'attendance_pct': 'Attendance %', 'prev_gpa': 'GPA', 'department': 'Department'})
    fig = apply_neon_theme(fig, "Attendance vs CGPA")
    return fig

@st.cache_data(ttl=300)
def get_insights_pie_chart(df_json):
    from io import StringIO
    df = pd.read_json(StringIO(df_json))
    risk_counts = df['risk'].value_counts().reset_index()
    risk_counts.columns = ['Status', 'Count']
    risk_counts['Status'] = risk_counts['Status'].map({0: 'Good Standing', 1: 'At Academic Risk'})
    fig = px.pie(risk_counts, values='Count', names='Status',
                 color_discrete_sequence=['#43e97b', '#fa709a'])
    fig = apply_neon_theme(fig, "Academic Risk Distribution")
    return fig

def show():
    section_header("AI Insights Engine", "Advanced predictive analytics for your academic success")

    selected_tab = st.radio(
        "Select Analytics Section",
        ["Performance Predictor", "Weak Subject Detector", "Study Plan", "Class Analytics"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if selected_tab == "Performance Predictor":
        show_performance_predictor()
    elif selected_tab == "Weak Subject Detector":
        show_weak_subject_detector()
    elif selected_tab == "Study Plan":
        show_study_plan_generator()
    elif selected_tab == "Class Analytics":
        try:
            from pathlib import Path
            ROOT = Path(__file__).resolve().parent.parent
            df_sample = load_sample_data(str(ROOT / "data" / "sample_data.csv"))
        except Exception:
            df_sample = pd.DataFrame()
        show_class_analytics(df_sample)

def show_performance_predictor():
    st.markdown("""
        <div class="glass-card fade-in" style="margin-bottom: 2rem; padding: 2rem;">
            <h3 class="gradient-text" style="margin-top: 0; font-size: 1.8rem; font-weight: 800; letter-spacing: -1px;">Performance Predictor</h3>
            <p style="color: #94a3b8; font-size: 1rem; margin-bottom: 0;">Adjust the parameters below to run AI-powered GPA projections and academic risk profiling.</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        att = st.slider("Attendance %", 0, 100, 85)
        study = st.slider("Daily Study Hours", 1, 15, 5)
    with col2:
        internal = st.slider("Internal Marks (Avg)", 0, 100, 75)
        assignments = st.slider("Assignments Completed", 0, 20, 12)
        prev_gpa = st.number_input("Previous GPA", 0.0, 4.0, 3.5)

    if st.button("Predict My Performance", use_container_width=True):
        pred_gpa, risk_prob = get_student_predictions(att, internal, study, prev_gpa, assignments)

        st.divider()

        risk_level = "Low"
        color = "#43e97b"
        if risk_prob > 60:
            risk_level = "High"
            color = "#fa709a"
        elif risk_prob > 30:
            risk_level = "Medium"
            color = "#f6d365"

        st.markdown(f"""
            <div style="background: {color}22; border: 1px solid {color}; border-radius: 20px; padding: 2rem; text-align: center;">
                <h2 style="color: {color}; margin-bottom: 0;">{risk_level} Risk Detected</h2>
                <div style="font-size: 4rem; font-weight: 900; margin: 1rem 0;">{pred_gpa} <span style="font-size: 1.5rem; color: #94a3b8;">GPA</span></div>
                <p style="font-size: 1.2rem; color: #cbd5e1;">Probability of academic risk: <b>{risk_prob}%</b></p>
            </div>
        """, unsafe_allow_html=True)

def show_weak_subject_detector():
    st.markdown("""
        <div class="glass-card fade-in" style="margin-bottom: 2rem; padding: 2rem;">
            <h3 class="gradient-text" style="margin-top: 0; font-size: 1.8rem; font-weight: 800; letter-spacing: -1px;">Weak Subject Detector</h3>
            <p style="color: #94a3b8; font-size: 1rem; margin-bottom: 0;">Enter your grades across different subjects to let AI analyze and recommend personalized study plans.</p>
        </div>
    """, unsafe_allow_html=True)

    subjects = ["Mathematics", "Physics", "Computer Science", "English", "Data Science", "AI"]
    marks = {}

    cols = st.columns(3)
    for i, sub in enumerate(subjects):
        with cols[i % 3]:
            marks[sub] = st.number_input(f"{sub} Marks", 0, 100, 75)

    weak_subjects = [s for s, m in marks.items() if m < 60]

    if weak_subjects:
        st.warning(f"Detected {len(weak_subjects)} weak subjects. See recommendations below.")
        for sub in weak_subjects:
            with st.expander(f"Recommendations for {sub}"):
                st.write(f"- Focus on core concepts of {sub} for 2 extra hours daily.")
                st.write("- Review previous year question papers.")
                st.write(f"- Schedule a doubt clearing session with your {sub} mentor.")
                st.progress(marks[sub]/100)
    else:
        st.success("All subjects are currently above the 60% threshold. Keep it up!")

def show_study_plan_generator():
    st.markdown("""
        <div class="glass-card fade-in" style="margin-bottom: 2rem; padding: 2rem;">
            <h3 class="gradient-text" style="margin-top: 0; font-size: 1.8rem; font-weight: 800; letter-spacing: -1px;">Automated 7-Day Study Plan</h3>
            <p style="color: #94a3b8; font-size: 1rem; margin-bottom: 0;">Your AI-generated personalized calendar schedule for balanced curriculum learning.</p>
        </div>
    """, unsafe_allow_html=True)

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    plan = {
        "Monday": "Math & Physics Review (Deep Dive)",
        "Tuesday": "CS Lab Practice & Assignment Prep",
        "Wednesday": "AI Concepts & Data Science Project",
        "Thursday": "English Reading & Communication Skills",
        "Friday": "Subject Mock Test & Weekly Quiz",
        "Saturday": "Weak Areas Revision & Group Study",
        "Sunday": "Rest & Strategy Planning for Next Week"
    }

    df_plan = pd.DataFrame(list(plan.items()), columns=["Day", "Focus Area"])
    st.table(df_plan)

def show_chat():
    from utils.ai import get_ai_response
    import time

    section_header("EduVerse AI Assistant", "Your dedicated companion for academic intelligence")

    col_hdr, col_clear = st.columns([4, 2])
    with col_hdr:
        st.markdown("### Chat Room")
    with col_clear:
        if st.button("Clear Chat History", use_container_width=True):
            st.session_state.chat_history = [{"role": "assistant", "content": "Hello! I am your EduVerse AI Assistant. Kaise help kar sakta hoon?"}]
            st.session_state.pop("last_error", None)
            st.rerun()

    st.markdown("##### Quick Action Chips")
    actions = ["Platform Stats", "How to use?", "At-risk Students", "Top Performers", "How does AI work?"]

    cols = st.columns(len(actions))
    clicked_action = None
    for i, action in enumerate(actions):
        if cols[i].button(action, key=f"chat_action_{i}", use_container_width=True):
            clicked_action = action

    st.divider()

    chat_container = st.container()

    with chat_container:
        for msg in st.session_state.chat_history[-20:]:
            if msg["role"] == "user":
                st.markdown(f"""
                    <div style="display: flex; justify-content: flex-end; margin-bottom: 20px;">
                        <div style="background: linear-gradient(135deg, #00f2fe, #4facfe); color: #0f172a; padding: 15px 20px; border-radius: 20px 20px 4px 20px; max-width: 75%; font-weight: 600; box-shadow: 0 4px 15px rgba(0, 242, 254, 0.25);">
                            {html.escape(msg["content"])}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div style="display: flex; justify-content: flex-start; margin-bottom: 20px;">
                        <div style="background: rgba(255, 255, 255, 0.04); color: #cbd5e1; padding: 15px 20px; border-radius: 20px 20px 20px 4px; max-width: 75%; border: 1px solid rgba(255, 255, 255, 0.08); box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);">
                            {msg["content"]}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    if st.session_state.get("last_error"):
        col_err, col_retry = st.columns([4, 2])
        with col_err:
            st.error(f"Connection Issue: {st.session_state.last_error}")
        with col_retry:
            if st.button("Retry Last Prompt", use_container_width=True):
                user_msgs = [m for m in st.session_state.chat_history if m["role"] == "user"]
                if user_msgs:
                    clicked_action = user_msgs[-1]["content"]
                    st.session_state.pop("last_error", None)

    user_input = st.chat_input("Ask EduVerse AI Assistant...")

    active_prompt = None
    if clicked_action:
        active_prompt = clicked_action
    elif user_input:
        active_prompt = user_input

    if active_prompt:
        if not clicked_action:
            st.session_state.chat_history.append({"role": "user", "content": active_prompt})
        elif clicked_action and (not st.session_state.chat_history or st.session_state.chat_history[-1]["content"] != active_prompt):
            st.session_state.chat_history.append({"role": "user", "content": active_prompt})

        st.rerun()

    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        with chat_container:
            st.markdown(f"""
                <div style="display: flex; justify-content: flex-start; margin-bottom: 20px;">
                    <div style="background: rgba(255, 255, 255, 0.04); padding: 18px 25px; border-radius: 20px 20px 20px 4px; max-width: 75%; border: 1px solid rgba(255, 255, 255, 0.08); box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);">
                        <div class="typing-container">
                            <div class="typing-loader"></div>
                            <div class="typing-loader"></div>
                            <div class="typing-loader"></div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        query = st.session_state.chat_history[-1]["content"]

        start_time = time.time()
        try:
            with st.spinner("EduVerse AI is thinking..."):
                response = get_ai_response(query)
                elapsed = time.time() - start_time
                if elapsed < 0.8:
                    time.sleep(0.8 - elapsed)

            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.session_state.pop("last_error", None)
        except Exception as e:
            st.session_state.last_error = str(e)
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": "Main temporary network connectivity issue face kar raha hoon. Kripya upar diye gaye retry button se phir se koshish karein ya local stats options use karein."
            })

        st.rerun()

def show_class_analytics(df):
    if df.empty:
        st.info("Class analytics data not available.")
        return

    df.columns = [c.lower() for c in df.columns]

    st.markdown("""
        <div class="glass-card fade-in" style="margin-bottom: 2rem; padding: 2rem;">
            <h3 class="gradient-text" style="margin-top: 0; font-size: 1.8rem; font-weight: 800; letter-spacing: -1px;">Class-wide Analytics</h3>
            <p style="color: #94a3b8; font-size: 1rem; margin-bottom: 0;">Demographic trends, risk distributions, and cumulative metrics across the academic department.</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    df_json = df.to_json()

    with col1:
        fig_scatter = get_insights_scatter_chart(df_json)
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col2:
        fig_pie = get_insights_pie_chart(df_json)
        st.plotly_chart(fig_pie, use_container_width=True)
