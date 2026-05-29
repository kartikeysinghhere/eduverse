import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from utils.ui import glass_card, metric_row, section_header
from utils.ml import get_student_predictions, train_predictive_models
from utils.charts import apply_neon_theme

def show():
    section_header("AI Insights Engine", "Advanced predictive analytics for your academic success")

    # Load Data for Class Analytics (dynamically resolved relative to ROOT)
    try:
        from pathlib import Path
        ROOT = Path(__file__).resolve().parent.parent
        df_sample = pd.read_csv(ROOT / "data" / "sample_data.csv")
    except:
        df_sample = pd.DataFrame()

    tabs = st.tabs(["🎯 Performance Predictor", "🔍 Weak Subject Detector", "📅 Study Plan", "📊 Class Analytics"])

    with tabs[0]:
        show_performance_predictor()

    with tabs[1]:
        show_weak_subject_detector()

    with tabs[2]:
        show_study_plan_generator()

    with tabs[3]:
        show_class_analytics(df_sample)

def show_performance_predictor():
    st.markdown('<div class="glass-card fade-in">', unsafe_allow_html=True)
    st.subheader("Predict My Performance")
    
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
        
        # Result Card
        risk_level = "Low"
        color = "#43e97b" # Green
        if risk_prob > 60:
            risk_level = "High"
            color = "#fa709a" # Red
        elif risk_prob > 30:
            risk_level = "Medium"
            color = "#f6d365" # Yellow
            
        st.markdown(f"""
            <div style="background: {color}22; border: 1px solid {color}; border-radius: 20px; padding: 2rem; text-align: center;">
                <h2 style="color: {color}; margin-bottom: 0;">{risk_level} Risk Detected</h2>
                <div style="font-size: 4rem; font-weight: 900; margin: 1rem 0;">{pred_gpa} <span style="font-size: 1.5rem; color: #94a3b8;">GPA</span></div>
                <p style="font-size: 1.2rem; color: #cbd5e1;">Probability of academic risk: <b>{risk_prob}%</b></p>
            </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def show_weak_subject_detector():
    st.markdown('<div class="glass-card fade-in">', unsafe_allow_html=True)
    st.subheader("Subject-wise Analysis")
    
    subjects = ["Mathematics", "Physics", "Computer Science", "English", "Data Science", "AI"]
    marks = {}
    
    cols = st.columns(3)
    for i, sub in enumerate(subjects):
        with cols[i % 3]:
            marks[sub] = st.number_input(f"{sub} Marks", 0, 100, 75)
    
    weak_subjects = [s for s, m in marks.items() if m < 60]
    
    if weak_subjects:
        st.warning(f"⚠️ Detected {len(weak_subjects)} weak subjects. See recommendations below.")
        for sub in weak_subjects:
            with st.expander(f"📚 Recommendations for {sub}"):
                st.write(f"- Focus on core concepts of {sub} for 2 extra hours daily.")
                st.write("- Review previous year question papers.")
                st.write(f"- Schedule a doubt clearing session with your {sub} mentor.")
                st.progress(marks[sub]/100)
    else:
        st.success("✅ All subjects are currently above the 60% threshold. Keep it up!")
    st.markdown('</div>', unsafe_allow_html=True)

def show_study_plan_generator():
    st.markdown('<div class="glass-card fade-in">', unsafe_allow_html=True)
    st.subheader("Automated 7-Day Study Plan")
    
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
    st.markdown('</div>', unsafe_allow_html=True)

def show_chat():
    from utils.ai import get_ai_response
    import time
    
    section_header("🤖 EduVerse AI Assistant", "Your dedicated companion for academic intelligence")

    # Clear chat utility and layout header
    col_hdr, col_clear = st.columns([4, 2])
    with col_hdr:
        st.markdown("### 💬 Chat Room")
    with col_clear:
        if st.button("🧹 Clear Chat History", use_container_width=True):
            st.session_state.chat_history = [{"role": "assistant", "content": "Hello! I am your EduVerse AI Assistant. Kaise help kar sakta hoon?"}]
            st.session_state.pop("last_error", None)
            st.rerun()

    # Quick Actions / Chips
    st.markdown("##### ⚡ Quick Action Chips")
    actions = ["📊 Platform Stats", "🎓 How to use?", "⚠️ At-risk Students", "🏆 Top Performers", "🤖 How does AI work?"]
    
    cols = st.columns(len(actions))
    clicked_action = None
    for i, action in enumerate(actions):
        if cols[i].button(action, key=f"chat_action_{i}", use_container_width=True):
            clicked_action = action

    st.divider()

    # Chat Interface Container
    chat_container = st.container()

    with chat_container:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f"""
                    <div style="display: flex; justify-content: flex-end; margin-bottom: 20px;">
                        <div style="background: linear-gradient(135deg, #00f2fe, #4facfe); color: #0f172a; padding: 15px 20px; border-radius: 20px 20px 4px 20px; max-width: 75%; font-weight: 600; box-shadow: 0 4px 15px rgba(0, 242, 254, 0.25);">
                            {msg["content"]}
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

    # Check if there is an error in session state to display a retry option
    if st.session_state.get("last_error"):
        col_err, col_retry = st.columns([4, 2])
        with col_err:
            st.error(f"⚠️ Connection Issue: {st.session_state.last_error}")
        with col_retry:
            if st.button("🔄 Retry Last Prompt", use_container_width=True):
                user_msgs = [m for m in st.session_state.chat_history if m["role"] == "user"]
                if user_msgs:
                    clicked_action = user_msgs[-1]["content"]
                    st.session_state.pop("last_error", None)

    # Read native chat input
    user_input = st.chat_input("Ask EduVerse AI Assistant...")

    # Process prompt from either input or quick chips
    active_prompt = None
    if clicked_action:
        active_prompt = clicked_action
    elif user_input:
        active_prompt = user_input

    if active_prompt:
        # Avoid duplicate appending if triggered by chip / retry and already there
        if not clicked_action:
            st.session_state.chat_history.append({"role": "user", "content": active_prompt})
        elif clicked_action and (not st.session_state.chat_history or st.session_state.chat_history[-1]["content"] != active_prompt):
            st.session_state.chat_history.append({"role": "user", "content": active_prompt})
            
        st.rerun()

    # If last message is from user, generate assistant response
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
        
        # Call API & track latency
        start_time = time.time()
        try:
            response = get_ai_response(query)
            # Ensure the beautiful loading animation is visible for at least 0.8 seconds for premium feel
            elapsed = time.time() - start_time
            if elapsed < 0.8:
                time.sleep(0.8 - elapsed)
                
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.session_state.pop("last_error", None)
        except Exception as e:
            # Save error state for retry option
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
        
    st.markdown('<div class="glass-card fade-in">', unsafe_allow_html=True)
    st.subheader("Class-wide Analytics")
    
    col1, col2 = st.columns(2)
    colors = ['#00f2fe', '#4facfe', '#43e97b', '#fa709a', '#f093fb', '#ffd700']
    
    with col1:
        # Attendance vs GPA
        fig = px.scatter(df, x='attendance_pct', y='prev_gpa', color='department',
                         color_discrete_sequence=colors,
                         labels={'attendance_pct': 'Attendance %', 'prev_gpa': 'GPA', 'department': 'Department'})
        fig = apply_neon_theme(fig, "Attendance vs CGPA")
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        # Risk distribution
        risk_counts = df['risk'].value_counts().reset_index()
        risk_counts.columns = ['Status', 'Count']
        risk_counts['Status'] = risk_counts['Status'].map({0: 'Good Standing', 1: 'At Academic Risk'})
        fig = px.pie(risk_counts, values='Count', names='Status',
                     color_discrete_sequence=['#43e97b', '#fa709a'])
        fig = apply_neon_theme(fig, "Academic Risk Distribution")
        st.plotly_chart(fig, use_container_width=True)
        
    st.markdown('</div>', unsafe_allow_html=True)
