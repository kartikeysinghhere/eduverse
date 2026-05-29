import streamlit as st
import pandas as pd
import plotly.express as px
from utils.ui import section_header, glass_card, metric_row
from utils.charts import apply_neon_theme
from collections import Counter

def show():
    section_header("Smart Analytics", "System usage insights and automated recommendations")

    if "analytics_data" not in st.session_state:
        st.info("No analytics data collected yet. Navigate through the app to generate insights.")
        return

    data = st.session_state.analytics_data
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Page Visit Frequency")
        if data["visits"]:
            df_visits = pd.DataFrame(list(data["visits"].items()), columns=["Page", "Visits"])
            fig = px.bar(df_visits, x="Page", y="Visits", color="Page",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            fig = apply_neon_theme(fig, "Most Visited Sections")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("No page visits tracked yet.")

    with col2:
        st.subheader("🔍 Search Keyword Frequency")
        if data["searches"]:
            counts = Counter(data["searches"])
            df_searches = pd.DataFrame(list(counts.items()), columns=["Keyword", "Frequency"])
            fig = px.pie(df_searches, values="Frequency", names="Keyword",
                         color_discrete_sequence=px.colors.qualitative.Safe)
            fig = apply_neon_theme(fig, "Top Search Terms")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("No searches tracked yet.")

    st.divider()
    
    st.subheader("💡 System Improvement Recommendations")
    
    # Logic for recommendations
    recommendations = []
    
    visits = data["visits"]
    if visits.get("AI Insights", 0) > visits.get("Dashboard", 0):
        recommendations.append({
            "title": "Expand ML Features",
            "desc": "Users are spending more time on AI Insights than the main dashboard. Consider adding more predictive models and automated tutoring features.",
            "icon": "🤖"
        })
    
    if visits.get("Attendance", 0) > 5:
        recommendations.append({
            "title": "Add Attendance Alerts",
            "desc": "Frequent attendance checks detected. Implementing automated SMS/Email alerts for low attendance might improve student engagement.",
            "icon": "📅"
        })

    if not recommendations:
        recommendations.append({
            "title": "Gather More Data",
            "desc": "Keep using the platform to unlock personalized system recommendations.",
            "icon": "📈"
        })

    cols = st.columns(len(recommendations))
    for i, rec in enumerate(recommendations):
        with cols[i]:
            st.markdown(f"""
                <div class="glass-card fade-in" style="height: 250px; border-top: 4px solid #00f2fe;">
                    <div style="font-size: 2.5rem; margin-bottom: 10px;">{rec['icon']}</div>
                    <h3 style="color: #00f2fe; margin-top: 0;">{rec['title']}</h3>
                    <p style="color: #94a3b8; font-size: 0.9rem;">{rec['desc']}</p>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.expander("🛠️ Raw Analytics Data"):
        st.write(st.session_state.analytics_data)
