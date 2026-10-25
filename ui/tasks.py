"""
Task Management UI for PersonalAI.
Provides full CRUD capabilities, multi-criteria filtering, sorting, status updates,
and safe deletion with confirmation.
"""

from datetime import date, datetime
import streamlit as st
from services.task_service import (
    list_tasks,
    create_task,
    update_task,
    mark_task_status,
    delete_task,
    VALID_CATEGORIES,
    VALID_PRIORITIES,
    VALID_STATUSES,
)


def render_tasks_view():
    st.title("📋 Task Manager")
    st.caption("Organize, track, and update all your tasks stored in persistent SQLite.")

    # --- Top Bar: Add Task Expander ---
    with st.expander("➕ Create New Task", expanded=False):
        with st.form("new_task_full_form", clear_on_submit=True):
            f_title = st.text_input("Task Title *", placeholder="e.g., Practice LeetCode Tree Problems")
            f_desc = st.text_area("Detailed Description", placeholder="Specific questions, constraints, or goals...")
            c1, c2, c3 = st.columns(3)
            with c1:
                f_cat = st.selectbox("Category", sorted(list(VALID_CATEGORIES)), index=0)
            with c2:
                f_prio = st.selectbox("Priority", ["Urgent", "High", "Medium", "Low"], index=2)
            with c3:
                f_dead = st.date_input("Deadline", value=date.today())

            submitted = st.form_submit_button("Save Task to SQLite", use_container_width=True)
            if submitted:
                if f_title.strip():
                    new_t = create_task(
                        title=f_title.strip(),
                        description=f_desc.strip(),
                        category=f_cat,
                        priority=f_prio,
                        deadline=f_dead.isoformat(),
                    )
                    st.success(f"Task #{new_t['id']} '{new_t['title']}' created successfully!")
                    st.rerun()
                else:
                    st.error("Title is required.")

    st.divider()

    # --- Filters and Sorting ---
    f_col1, f_col2, f_col3, f_col4 = st.columns([1, 1, 1, 1])

    with f_col1:
        status_filter = st.selectbox("Status Filter", ["All", "Pending", "In Progress", "Completed", "Cancelled"])
    with f_col2:
        priority_filter = st.selectbox("Priority Filter", ["All", "Urgent", "High", "Medium", "Low"])
    with f_col3:
        category_filter = st.selectbox("Category Filter", ["All"] + sorted(list(VALID_CATEGORIES)))
    with f_col4:
        sort_by = st.selectbox("Sort By", ["deadline", "priority", "created_at"])

    search_query = st.text_input("🔍 Search tasks by keyword", placeholder="Search in title or description...")

    # Fetch filtered tasks
    tasks = list_tasks(
        status=status_filter if status_filter != "All" else None,
        priority=priority_filter if priority_filter != "All" else None,
        category=category_filter if category_filter != "All" else None,
        search=search_query if search_query.strip() else None,
        sort_by=sort_by,
    )

    st.write(f"**Found {len(tasks)} tasks** matching criteria:")

    if not tasks:
        st.info("No tasks found. Create a new task above or adjust your search filters.")
        return

    # Render Task Cards
    for task in tasks:
        t_id = task["id"]
        is_completed = task["status"] == "Completed"

        with st.container():
            t_col1, t_col2, t_col3, t_col4 = st.columns([0.5, 3.5, 1.5, 1.5])

            # Column 1: Checkbox to toggle completed
            with t_col1:
                checked = st.checkbox(
                    " ",
                    value=is_completed,
                    key=f"check_{t_id}",
                    label_visibility="collapsed",
                )
                if checked != is_completed:
                    new_st = "Completed" if checked else "Pending"
                    mark_task_status(t_id, new_st)
                    st.rerun()

            # Column 2: Title & Details
            with t_col2:
                title_markdown = f"~~#{t_id} {task['title']}~~" if is_completed else f"**#{t_id} {task['title']}**"
                st.markdown(title_markdown)
                if task["description"]:
                    st.caption(task["description"])

            # Column 3: Metadata Badges
            with t_col3:
                prio_color = "red" if task["priority"] == "Urgent" else "orange" if task["priority"] == "High" else "blue"
                status_color = "green" if task["status"] == "Completed" else "orange" if task["status"] == "In Progress" else "gray"
                st.markdown(
                    f":{prio_color}[{task['priority']}] | :{status_color}[{task['status']}]\n\n"
                    f"📁 `{task['category']}` | 📅 `{task['deadline'] or 'No date'}`"
                )

            # Column 4: Edit & Delete Actions
            with t_col4:
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    edit_expanded = st.session_state.get(f"editing_{t_id}", False)
                    if st.button("✏️", key=f"edit_btn_{t_id}", help="Edit task"):
                        st.session_state[f"editing_{t_id}"] = not edit_expanded
                        st.rerun()

                with btn_col2:
                    if st.button("🗑️", key=f"del_btn_{t_id}", help="Delete task"):
                        st.session_state[f"confirm_del_{t_id}"] = True
                        st.rerun()

            # Delete confirmation modal/prompt
            if st.session_state.get(f"confirm_del_{t_id}", False):
                st.warning(f"Are you sure you want to permanently delete task **#{t_id}: {task['title']}**?")
                cd_col1, cd_col2 = st.columns([1, 4])
                with cd_col1:
                    if st.button("Yes, Delete", key=f"conf_yes_{t_id}", type="primary"):
                        delete_task(t_id)
                        st.session_state[f"confirm_del_{t_id}"] = False
                        st.toast(f"Task #{t_id} deleted.")
                        st.rerun()
                with cd_col2:
                    if st.button("Cancel", key=f"conf_no_{t_id}"):
                        st.session_state[f"confirm_del_{t_id}"] = False
                        st.rerun()

            # In-line Edit form
            if st.session_state.get(f"editing_{t_id}", False):
                with st.form(f"edit_form_{t_id}"):
                    st.markdown(f"**Editing Task #{t_id}**")
                    e_title = st.text_input("Title", value=task["title"])
                    e_desc = st.text_area("Description", value=task["description"] or "")
                    ec1, ec2, ec3 = st.columns(3)
                    with ec1:
                        e_cat = st.selectbox("Category", sorted(list(VALID_CATEGORIES)), index=sorted(list(VALID_CATEGORIES)).index(task["category"]) if task["category"] in VALID_CATEGORIES else 0)
                    with ec2:
                        e_prio = st.selectbox("Priority", ["Urgent", "High", "Medium", "Low"], index=["Urgent", "High", "Medium", "Low"].index(task["priority"]))
                    with ec3:
                        e_stat = st.selectbox("Status", ["Pending", "In Progress", "Completed", "Cancelled"], index=["Pending", "In Progress", "Completed", "Cancelled"].index(task["status"]))

                    sub_edit = st.form_submit_button("Update Task")
                    if sub_edit:
                        update_task(
                            task_id=t_id,
                            title=e_title,
                            description=e_desc,
                            category=e_cat,
                            priority=e_prio,
                            status=e_stat,
                        )
                        st.session_state[f"editing_{t_id}"] = False
                        st.success("Task updated.")
                        st.rerun()

            st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)
