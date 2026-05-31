import streamlit as st

def glass_card(title, content, height=None):
    """Renders a world-class glassmorphic card without markdown code block parsing issues."""
    style_attr = f"style='height: {height}px;'" if height else ""
    st.markdown(f'<div class="glass-card fade-in" {style_attr}><h3 class="gradient-text" style="margin-top: 0; font-size: 1.5rem; letter-spacing: -0.5px;">{title}</h3><div style="color: #94a3b8; font-size: 1rem; line-height: 1.6; margin-top: 10px;">{content}</div></div>', unsafe_allow_html=True)

def metric_row(metrics):
    """
    Renders a row of premium metric cards with icons and trends.
    metrics: list of dicts with {'label': '...', 'value': '...', 'trend': '...', 'icon': '...'}
    """
    cols = st.columns(len(metrics))
    for i, m in enumerate(metrics):
        trend_html = ""
        if 'trend' in m:
            is_positive = "+" in m['trend'] or "↑" in m['trend']
            color = "#43e97b" if is_positive else "#fa709a"
            trend_html = f'<span style="color: {color}; font-size: 0.85rem; font-weight: 700; margin-left: 8px;">{m["trend"]}</span>'
            
        icon = m.get('icon', '⚡')
        with cols[i]:
            st.markdown(f'<div class="metric-card fade-in"><span class="metric-icon">{icon}</span><div style="color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 700; margin-bottom: 8px;">{m["label"]}</div><div style="display: flex; align-items: baseline;"><span class="metric-value">{m["value"]}</span>{trend_html}</div></div>', unsafe_allow_html=True)

def section_header(title, subtitle=None):
    """Renders a premium section header with large gradient text (no anchor icons)."""
    subtitle_html = f'<p style="color: #94a3b8; font-size: 1.2rem; margin-top: 12px; font-weight: 400; max-width: 600px;">{subtitle}</p>' if subtitle else ''
    st.markdown(f'<div style="margin-top: 3rem; margin-bottom: 2.5rem;" class="fade-in"><div class="gradient-text" style="margin-bottom: 0; font-size: 3.5rem; font-weight: 900; letter-spacing: -2px; line-height: 1.1;">{title}</div>{subtitle_html}</div>', unsafe_allow_html=True)
