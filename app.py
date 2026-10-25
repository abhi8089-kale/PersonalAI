"""
PersonalAI — Intelligent Personal Assistant Agent
Main Streamlit Application Entrypoint.
"""

import streamlit as st
from database.db import init_db
from services.llm_service import is_llm_available, get_llm_config
from services.task_service import get_dashboard_stats
from ui.dashboard import render_dashboard
from ui.assistant import render_assistant_chat
from ui.tasks import render_tasks_view
from ui.planner import render_goal_planner
from ui.study_helper import render_study_helper
from ui.settings import render_settings

# Configure page metadata
st.set_page_config(
    page_title="PersonalAI — Intelligent Personal Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    /* Metric styling */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
    }
    /* Sidebar headers */
    .sidebar-brand {
        font-size: 1.35rem;
        font-weight: 800;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sidebar-subtitle {
        font-size: 0.85rem;
        color: #6B7280;
        margin-bottom: 1.2rem;
    }
    .badge-pill {
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-online { background-color: #DEF7EC; color: #03543F; }
    .badge-offline { background-color: #FEF08A; color: #713F12; }
    .badge-configured { background-color: #FEF3C7; color: #92400E; }
    .badge-error { background-color: #FEE2E2; color: #991B1B; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Ensure database tables exist
init_db()

# Fetch quick sidebar stats
stats = get_dashboard_stats()
from services.llm_service import get_connection_status
conn_info = get_connection_status()

# --- Sidebar Navigation ---
with st.sidebar:
    st.markdown('<div class="sidebar-brand">🤖 PersonalAI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-subtitle">Agentic AI Personal Assistant</div>', unsafe_allow_html=True)

    # Dynamic Honest Status Pill
    if conn_info["verified"]:
        st.markdown(f'<span class="badge-pill badge-online">{conn_info["badge_label"]}</span>', unsafe_allow_html=True)
    elif conn_info["mode"] == "Online AI Error":
        st.markdown('<span class="badge-pill badge-error">🔴 AI Connection Error</span>', unsafe_allow_html=True)
    elif conn_info["configured"]:
        st.markdown(f'<span class="badge-pill badge-configured">{conn_info["badge_label"]}</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge-pill badge-offline">🟠 Offline Mode Active</span>', unsafe_allow_html=True)

    st.write("")
    nav_selection = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "🤖 AI Assistant Chat",
            "📋 My Tasks",
            "🎯 Goal Planner",
            "🎓 Study & Interview Helper",
            "⚙️ Memory & Settings",
        ],
        index=0,
    )

    st.divider()

    # Quick Glance Sidebar Counters
    st.markdown("### 📌 Quick Glance")
    st.write(f"- Pending Tasks: **{stats['pending']}**")
    if stats["overdue"] > 0:
        st.error(f"⚠️ Overdue: **{stats['overdue']} tasks**")
    else:
        st.write("- Overdue: **0** (All clear!)")
    st.write(f"- Completion Rate: **{stats['completion_rate']}%**")

    st.divider()
    st.caption("College Final Year Project | CSE\nSubject: Agentic AI Development")

# --- Page Router ---
if nav_selection == "📊 Dashboard":
    render_dashboard()
elif nav_selection == "🤖 AI Assistant Chat":
    render_assistant_chat()
elif nav_selection == "📋 My Tasks":
    render_tasks_view()
elif nav_selection == "🎯 Goal Planner":
    render_goal_planner()
elif nav_selection == "🎓 Study & Interview Helper":
    render_study_helper()
elif nav_selection == "⚙️ Memory & Settings":
    render_settings()
