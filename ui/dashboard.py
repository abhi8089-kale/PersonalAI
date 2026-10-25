"""
Dashboard View for PersonalAI.
Displays productivity metrics, reminders, smart task recommendation,
quick task creation, active goal progress, and recent activity log.
"""

from datetime import date, datetime
import streamlit as st
from services.task_service import (
    get_dashboard_stats,
    get_overdue_tasks,
    get_upcoming_tasks,
    recommend_next_task,
    create_task,
    mark_task_status,
)
from services.planner_service import list_goals
from database.db import get_recent_activities


def render_dashboard():
    st.title("📊 PersonalAI Executive Dashboard")
    today_str = date.today().strftime("%A, %B %d, %Y")
    st.caption(f"📅 Current Date: **{today_str}** | CSE Agentic AI Project Demo")

    # Fetch stats
    stats = get_dashboard_stats()
    overdue_tasks = get_overdue_tasks()
    upcoming_tasks = get_upcoming_tasks(days=7)
    recommended = recommend_next_task()

    # --- Top Metric Cards ---
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(label="Total Tasks", value=stats["total"])
    with col2:
        st.metric(label="Pending", value=stats["pending"])
    with col3:
        st.metric(label="Completed", value=stats["completed"], delta=f"{stats['completion_rate']}% Done")
    with col4:
        st.metric(
            label="Overdue",
            value=stats["overdue"],
            delta=f"-{stats['overdue']}" if stats["overdue"] > 0 else "0",
            delta_color="inverse"
        )
    with col5:
        st.metric(label="Active Goals", value=stats["active_goals"])

    st.divider()

    # --- In-App Reminders & Overdue Alerts ---
    if overdue_tasks:
        st.error(f"🚨 **Attention Required:** You have **{len(overdue_tasks)} overdue tasks**!")
        with st.expander("⚠️ View Overdue Tasks", expanded=True):
            for ot in overdue_tasks[:5]:
                c_a, c_b, c_c = st.columns([3, 1, 1])
                c_a.write(f"**{ot['title']}** (Due: `{ot['deadline']}` | Priority: `{ot['priority']}`)")
                c_b.caption(ot.get("category", "General"))
                if c_c.button("Complete", key=f"dash_ov_comp_{ot['id']}"):
                    mark_task_status(ot["id"], "Completed")
                    st.toast(f"Marked #{ot['id']} as Completed!")
                    st.rerun()

    # --- Recommended Next Task Section ---
    st.subheader("🎯 Smart Agent Recommendation")
    if recommended:
        rec_col1, rec_col2 = st.columns([4, 1])
        with rec_col1:
            badge_color = "red" if recommended["priority"] == "Urgent" else "orange" if recommended["priority"] == "High" else "blue"
            st.info(
                f"**Focus on this next:** [#{recommended['id']}] **{recommended['title']}**\n\n"
                f"- **Priority:** :{badge_color}[{recommended['priority']}] | **Category:** {recommended['category']} | **Due:** `{recommended['deadline'] or 'No deadline'}`\n"
                f"- *{recommended['description'] or 'No description'}*"
            )
        with rec_col2:
            st.write("")
            st.write("")
            if st.button("✅ Mark Done", key="dash_rec_done", use_container_width=True):
                mark_task_status(recommended["id"], "Completed")
                st.toast("Recommended task completed!")
                st.rerun()
    else:
        st.success("🎉 All caught up! No pending tasks in your queue.")

    st.divider()

    # --- Two Columns: Quick Add Task + Upcoming Deadlines ---
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.subheader("⚡ Quick Create Task")
        with st.form("quick_task_form", clear_on_submit=True):
            q_title = st.text_input("Task Title", placeholder="e.g. Finish Operating Systems Assignment")
            q_desc = st.text_area("Description (Optional)", placeholder="Notes, reference links or requirements...", height=70)
            c1, c2, c3 = st.columns(3)
            with c1:
                q_cat = st.selectbox("Category", ["Study", "Interview", "Assignment", "Work", "Personal", "General"])
            with c2:
                q_prio = st.selectbox("Priority", ["Medium", "High", "Urgent", "Low"])
            with c3:
                q_dead = st.date_input("Deadline", value=date.today())

            submitted = st.form_submit_button("➕ Add Task", use_container_width=True)
            if submitted:
                if q_title.strip():
                    created = create_task(
                        title=q_title.strip(),
                        description=q_desc.strip(),
                        category=q_cat,
                        priority=q_prio,
                        deadline=q_dead.isoformat(),
                    )
                    st.success(f"Created task #{created['id']}: {created['title']}")
                    st.rerun()
                else:
                    st.error("Task title cannot be empty.")

    with right_col:
        st.subheader("⏰ Upcoming Deadlines (Next 7 Days)")
        if upcoming_tasks:
            for up in upcoming_tasks[:6]:
                u1, u2 = st.columns([3, 1])
                u1.markdown(f"**{up['title']}**\n\n*{up['category']}* | Due: `{up['deadline']}`")
                if u2.button("Done", key=f"dash_up_done_{up['id']}"):
                    mark_task_status(up["id"], "Completed")
                    st.rerun()
        else:
            st.info("No upcoming deadlines in the next 7 days.")

    st.divider()

    # --- Goal Progress & Recent Activities ---
    col_goals, col_act = st.columns([1, 1])

    with col_goals:
        st.subheader("🏆 Active Goals Progress")
        goals = list_goals()
        active_goals = [g for g in goals if g["status"] == "Active"]
        if active_goals:
            for g in active_goals[:4]:
                prog = g.get("progress", {})
                rate = prog.get("completion_rate", 0.0)
                st.write(f"**{g['title']}** ({g['category']})")
                st.caption(f"{prog.get('completed', 0)} of {prog.get('total', 0)} tasks completed")
                st.progress(rate / 100.0)
        else:
            st.info("No active goals found. Use the **Goal Planner** tab to generate a structured curriculum or schedule!")

    with col_act:
        st.subheader("📜 Recent Activity Log")
        activities = get_recent_activities(limit=6)
        if activities:
            for act in activities:
                ts = act["timestamp"][:16].replace("T", " ")
                st.markdown(f"- `{ts}` **[{act['action']}]** {act['details']}")
        else:
            st.caption("No recent activities recorded yet.")
