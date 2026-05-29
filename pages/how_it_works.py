import streamlit as st
import plotly.graph_objects as go
from utils.ui import section_header

def show():
    section_header("Kaise Chalta Hai? 🤔", "Step-by-step visual explanation in Hinglish")

    st.markdown("""
        <div class="glass-card fade-in" style="margin-bottom: 2rem;">
            <p style="font-size: 1.2rem; color: #cbd5e1;">
                EduVerse koi jaadu nahi, balki <b>Data Science</b> aur <b>AI</b> ka kamaal hai. 
                Aaiye dekhte hain aapka data kaise travel karta hai! 🚀
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Plotly Flowchart / Sankey
    labels = ["User Login 👤", "Database (SQL) 🗄️", "AI Model (ML) 🤖", "Dashboard 📊"]
    
    # Source -> Target
    # 0 (Login) -> 1 (DB)
    # 1 (DB) -> 2 (AI)
    # 2 (AI) -> 3 (Dashboard)
    
    fig = go.Figure(data=[go.Sankey(
        node = dict(
          pad = 15,
          thickness = 20,
          line = dict(color = "black", width = 0.5),
          label = labels,
          color = ["#00f2fe", "#4facfe", "#43e97b", "#fa709a"]
        ),
        link = dict(
          source = [0, 1, 2],
          target = [1, 2, 3],
          value = [10, 10, 10],
          color = "rgba(148, 163, 184, 0.2)"
        ))])

    fig.update_layout(title_text="Data Flow Visualizer", font_size=12, 
                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      font_color="#94a3b8")
    
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Step by Step breakdown
    steps = [
        {
            "title": "Pehle aap login karte ho 🔑",
            "text": "Jab aap apna username aur password daalte ho, system check karta hai ki aap kaun ho (Student, Teacher, ya Admin).",
            "img": "🔓"
        },
        {
            "title": "Phir aapka data fetch hota hai 📥",
            "text": "Database se aapke purane grades, attendance aur activity records uthaye jaate hain.",
            "img": "💾"
        },
        {
            "title": "ML model predict karta hai 🧠",
            "text": "Humara smart AI model data ko analyze karke batata hai ki aapka future performance kaisa ho sakta hai.",
            "img": "✨"
        },
        {
            "title": "Dashboard pe result dikhta hai 📈",
            "text": "Saara complex data simple charts aur metrics mein badal kar aapke screen pe aa jata hai.",
            "img": "📱"
        }
    ]

    for step in steps:
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown(f"<div style='font-size: 4rem; text-align: center;'>{step['img']}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"### {step['title']}")
            st.write(step['text'])
        st.markdown("<div style='margin-bottom: 2rem;'></div>", unsafe_allow_html=True)

    st.success("Ab aap samajh gaye na? EduVerse is simple but powerful! 💪")
