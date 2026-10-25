"""
Goal Planner UI for PersonalAI.
Allows users to generate structured milestone study/project plans,
review the breakdown, and confirm before atomically saving tasks into SQLite.
"""

from datetime import date, timedelta
import streamlit as st
from services.planner_service import (
    generate_study_plan,
    save_confirmed_plan,
    list_goals,
    get_goal,
    update_goal_status,
)


def render_goal_planner():
    st.title("🎯 AI Goal Planner")
    st.caption("Deconstruct complex college study or placement goals into actionable daily milestones.")

    tab_create, tab_active = st.tabs(["✨ Plan New Goal", "🏆 Existing Goals & Milestones"])

    with tab_create:
        st.subheader("1. Define Your Goal")
        st.markdown(
            "Enter what you want to achieve, and PersonalAI will generate a structured, "
            "step-by-step curriculum with milestones and daily deadlines."
        )

        # Example prompt buttons
        ex_col1, ex_col2, ex_col3 = st.columns(3)
        sample_title = ""
        if ex_col1.button("☕ 7-Day Java Interview Prep"):
            sample_title = "Help me prepare for my Java interview in 7 days"
        if ex_col2.button("🐍 2-Week Python Fundamentals"):
            sample_title = "Learn Python fundamentals in 14 days"
        if ex_col3.button("💻 7-Day DSA Placement Sprint"):
            sample_title = "Data Structures & Algorithms Placement Prep"

        with st.form("goal_planner_input_form"):
            g_title = st.text_input(
                "Goal Objective *",
                value=sample_title,
                placeholder="e.g., Prepare for my Java technical interview in 7 days",
            )
            c1, c2 = st.columns(2)
            with c1:
                g_days = st.slider("Target Duration (Days)", min_value=1, max_value=30, value=7)
            with c2:
                g_cat = st.selectbox("Category", ["Study", "Interview", "Assignment", "Work", "Personal"])

            g_notes = st.text_area(
                "Custom Focus Areas / Constraints (Optional)",
                placeholder="e.g. Emphasize multithreading, collections, and mock viva questions...",
                height=70,
            )

            generate_btn = st.form_submit_button("🧠 Generate Structured Plan", use_container_width=True)

        if generate_btn:
            if not g_title.strip():
                st.error("Please enter a goal title.")
            else:
                with st.spinner("Analyzing curriculum and constructing milestones..."):
                    plan = generate_study_plan(
                        goal_title=g_title.strip(),
                        duration_days=g_days,
                        category=g_cat,
                        custom_notes=g_notes.strip(),
                    )
                    st.session_state["current_generated_plan"] = plan

        # If a plan is in session state, display review & confirmation
        if "current_generated_plan" in st.session_state:
            plan = st.session_state["current_generated_plan"]
            st.divider()
            st.subheader(f"2. Review Proposed Plan: {plan['title']}")
            st.info(
                f"**Target Duration:** {plan['duration_days']} days | "
                f"**Estimated Completion:** `{plan['target_date']}` | "
                f"**Total Milestones:** {len(plan['tasks'])} daily tasks"
            )

            # Display plan table
            for item in plan["tasks"]:
                with st.container():
                    p_c1, p_c2, p_c3 = st.columns([1, 4, 1.5])
                    p_c1.markdown(f"**Day {item['day_number']}**")
                    p_c2.markdown(f"**{item['title']}**\n\n{item['description']}")
                    p_c3.markdown(f"`{item['suggested_deadline']}`\n\nPriority: `{item['priority']}`")
                    st.markdown("<hr style='margin: 0.3rem 0;'>", unsafe_allow_html=True)

            # Safety and Confirmation Guard
            st.warning("⚠️ **Confirmation Required:** Would you like to commit this plan and automatically create all tasks in SQLite?")
            col_save, col_discard = st.columns([1, 1])

            with col_save:
                if st.button("💾 Confirm & Save Plan to Database", type="primary", use_container_width=True):
                    with st.spinner("Saving goal and creating tasks in SQLite..."):
                        saved = save_confirmed_plan(
                            title=plan["title"],
                            category=plan["category"],
                            target_date=plan["target_date"],
                            tasks=plan["tasks"],
                        )
                    st.success(f"🎉 Goal #{saved['goal_id']} saved with {saved['tasks_count']} tasks created in your Task Manager!")
                    del st.session_state["current_generated_plan"]
                    st.rerun()

            with col_discard:
                if st.button("❌ Discard Plan", use_container_width=True):
                    del st.session_state["current_generated_plan"]
                    st.rerun()

    with tab_active:
        st.subheader("Your Active & Saved Goals")
        goals = list_goals()
        if not goals:
            st.info("No saved goals yet. Generate and save a plan in the 'Plan New Goal' tab!")
            return

        for g in goals:
            with st.container():
                prog = g.get("progress", {})
                rate = prog.get("completion_rate", 0.0)

                g_col1, g_col2, g_col3 = st.columns([3, 1.5, 1])
                with g_col1:
                    st.markdown(f"### #{g['id']} {g['title']}")
                    st.caption(f"Category: {g['category']} | Target: `{g['target_date'] or 'Open'}` | Status: `{g['status']}`")
                with g_col2:
                    st.write(f"**Progress: {rate}%**")
                    st.progress(rate / 100.0)
                    st.caption(f"{prog.get('completed', 0)} of {prog.get('total', 0)} tasks finished")
                with g_col3:
                    if g["status"] == "Active" and st.button("Mark Completed", key=f"goal_comp_{g['id']}"):
                        update_goal_status(g["id"], "Completed")
                        st.toast("Goal marked as Completed!")
                        st.rerun()

                # Expandable details of tasks under this goal
                with st.expander("🔍 View Linked Tasks for this Goal"):
                    full_goal = get_goal(g["id"])
                    if full_goal and full_goal.get("tasks"):
                        for t in full_goal["tasks"]:
                            st.write(f"- [#{t['id']}] **{t['title']}** - Status: `{t['status']}` (Due: `{t['deadline']}`)")
                    else:
                        st.caption("No individual tasks found.")

                st.divider()
