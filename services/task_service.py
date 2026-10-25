"""
Task Service for PersonalAI.
Manages CRUD operations, filtering, status transitions, statistics, and recommendations.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from database.db import get_db, log_activity

VALID_PRIORITIES = {"Low", "Medium", "High", "Urgent"}
VALID_STATUSES = {"Pending", "In Progress", "Completed", "Cancelled"}
VALID_CATEGORIES = {"Study", "Work", "Personal", "Assignment", "Interview", "General"}

PRIORITY_WEIGHTS = {
    "Urgent": 4,
    "High": 3,
    "Medium": 2,
    "Low": 1,
}


def create_task(
    title: str,
    description: str = "",
    category: str = "General",
    priority: str = "Medium",
    deadline: Optional[str] = None,
    goal_id: Optional[int] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates a new task with validated attributes and persists it in SQLite.
    """
    cleaned_title = (title or "").strip()
    if not cleaned_title:
        raise ValueError("Task title cannot be empty.")

    cleaned_priority = priority.capitalize() if priority else "Medium"
    if cleaned_priority not in VALID_PRIORITIES:
        cleaned_priority = "Medium"

    cleaned_category = category.capitalize() if category else "General"
    if cleaned_category not in VALID_CATEGORIES:
        cleaned_category = "General"

    cleaned_deadline = deadline.strip() if deadline else None

    now = datetime.now().isoformat()

    with get_db(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (title, description, category, priority, status, deadline, created_at, updated_at, goal_id)
            VALUES (?, ?, ?, ?, 'Pending', ?, ?, ?, ?)
            """,
            (
                cleaned_title,
                description or "",
                cleaned_category,
                cleaned_priority,
                cleaned_deadline,
                now,
                now,
                goal_id,
            ),
        )
        task_id = cursor.lastrowid

    log_activity("task_created", f"Created task #{task_id}: {cleaned_title}", db_path=db_path)
    created = get_task_by_id(task_id, db_path=db_path)
    if not created:
        raise RuntimeError(f"Failed to retrieve newly created task #{task_id}")
    return created


def get_task_by_id(task_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a single task by its ID."""
    with get_db(db_path) as conn:
        cur = conn.execute(
            """
            SELECT id, title, description, category, priority, status, deadline, created_at, updated_at, completed_at, goal_id
            FROM tasks WHERE id = ?
            """,
            (task_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "deadline",
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Lists tasks filtered by status, priority, category, or search term.
    """
    query = """
        SELECT id, title, description, category, priority, status, deadline, created_at, updated_at, completed_at, goal_id
        FROM tasks
        WHERE 1=1
    """
    params: List[Any] = []

    if status:
        query += " AND status = ?"
        params.append(status)

    if priority:
        query += " AND priority = ?"
        params.append(priority)

    if category:
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (title LIKE ? OR description LIKE ?)"
        like_term = f"%{search}%"
        params.extend([like_term, like_term])

    if sort_by == "deadline":
        # Order by NULL deadline last, then deadline ascending, then priority
        query += """
            ORDER BY 
                CASE WHEN deadline IS NULL OR deadline = '' THEN 1 ELSE 0 END,
                deadline ASC,
                CASE priority 
                    WHEN 'Urgent' THEN 1 
                    WHEN 'High' THEN 2 
                    WHEN 'Medium' THEN 3 
                    WHEN 'Low' THEN 4 
                    ELSE 5 
                END
        """
    elif sort_by == "priority":
        query += """
            ORDER BY 
                CASE priority 
                    WHEN 'Urgent' THEN 1 
                    WHEN 'High' THEN 2 
                    WHEN 'Medium' THEN 3 
                    WHEN 'Low' THEN 4 
                    ELSE 5 
                END,
                created_at DESC
        """
    elif sort_by == "created_at":
        query += " ORDER BY created_at DESC"
    else:
        query += " ORDER BY id DESC"

    with get_db(db_path) as conn:
        cur = conn.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def update_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    deadline: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Updates an existing task's attributes.
    """
    existing = get_task_by_id(task_id, db_path=db_path)
    if not existing:
        return None

    updates: List[str] = []
    params: List[Any] = []

    if title is not None:
        c_title = title.strip()
        if not c_title:
            raise ValueError("Task title cannot be empty.")
        updates.append("title = ?")
        params.append(c_title)

    if description is not None:
        updates.append("description = ?")
        params.append(description)

    if category is not None:
        updates.append("category = ?")
        params.append(category)

    if priority is not None:
        c_priority = priority.capitalize()
        if c_priority not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority '{priority}'. Must be one of {sorted(VALID_PRIORITIES)}.")
        updates.append("priority = ?")
        params.append(c_priority)

    if deadline is not None:
        updates.append("deadline = ?")
        params.append(deadline.strip() if deadline else None)

    now = datetime.now().isoformat()

    if status is not None:
        c_status = status.capitalize() if status != "In Progress" else "In Progress"
        if c_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {sorted(VALID_STATUSES)}.")
        updates.append("status = ?")
        params.append(c_status)
        if c_status == "Completed":
            updates.append("completed_at = ?")
            params.append(now)
        else:
            updates.append("completed_at = NULL")

    if not updates:
        return existing

    updates.append("updated_at = ?")
    params.append(now)

    params.append(task_id)

    sql = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
    with get_db(db_path) as conn:
        conn.execute(sql, params)

    log_activity("task_updated", f"Updated task #{task_id}", db_path=db_path)
    return get_task_by_id(task_id, db_path=db_path)


def mark_task_status(
    task_id: int,
    status: str = "Completed",
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Convenience helper to set a task's status (default Completed)."""
    return update_task(task_id=task_id, status=status, db_path=db_path)


def delete_task(task_id: int, db_path: Optional[str] = None) -> bool:
    """Deletes a task by ID."""
    existing = get_task_by_id(task_id, db_path=db_path)
    if not existing:
        return False

    with get_db(db_path) as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    log_activity("task_deleted", f"Deleted task #{task_id}: {existing['title']}", db_path=db_path)
    return True


def get_dashboard_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Computes summary metrics for the dashboard:
    total, pending, in_progress, completed, overdue, upcoming, completion rate.
    """
    all_tasks = list_tasks(db_path=db_path)
    today_str = date.today().isoformat()
    three_days_str = (date.today() + timedelta(days=3)).isoformat()

    total = len(all_tasks)
    pending = 0
    in_progress = 0
    completed = 0
    cancelled = 0
    overdue = 0
    upcoming = 0

    for t in all_tasks:
        st = t["status"]
        dl = t["deadline"]

        if st == "Pending":
            pending += 1
        elif st == "In Progress":
            in_progress += 1
        elif st == "Completed":
            completed += 1
        elif st == "Cancelled":
            cancelled += 1

        if st in ("Pending", "In Progress") and dl:
            # check overdue
            if dl < today_str:
                overdue += 1
            elif today_str <= dl <= three_days_str:
                upcoming += 1

    completion_rate = round((completed / total * 100), 1) if total > 0 else 0.0

    # Count active goals
    with get_db(db_path) as conn:
        cur = conn.execute("SELECT COUNT(*) as count FROM goals WHERE status = 'Active'")
        active_goals = cur.fetchone()["count"]

    return {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "completed": completed,
        "cancelled": cancelled,
        "overdue": overdue,
        "upcoming": upcoming,
        "completion_rate": completion_rate,
        "active_goals": active_goals,
    }


def get_overdue_tasks(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns pending or in-progress tasks whose deadline is before today."""
    today_str = date.today().isoformat()
    with get_db(db_path) as conn:
        cur = conn.execute(
            """
            SELECT * FROM tasks
            WHERE status IN ('Pending', 'In Progress')
              AND deadline IS NOT NULL
              AND deadline != ''
              AND deadline < ?
            ORDER BY deadline ASC,
                CASE priority 
                    WHEN 'Urgent' THEN 1 
                    WHEN 'High' THEN 2 
                    WHEN 'Medium' THEN 3 
                    WHEN 'Low' THEN 4 
                    ELSE 5 
                END
            """,
            (today_str,),
        )
        return [dict(row) for row in cur.fetchall()]


def get_upcoming_tasks(days: int = 7, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns pending/in-progress tasks due within the specified number of days."""
    today_str = date.today().isoformat()
    future_str = (date.today() + timedelta(days=days)).isoformat()
    with get_db(db_path) as conn:
        cur = conn.execute(
            """
            SELECT * FROM tasks
            WHERE status IN ('Pending', 'In Progress')
              AND deadline IS NOT NULL
              AND deadline != ''
              AND deadline >= ?
              AND deadline <= ?
            ORDER BY deadline ASC
            """,
            (today_str, future_str),
        )
        return [dict(row) for row in cur.fetchall()]


def recommend_next_task(db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Intelligently recommends the single next task the user should focus on:
    1. Overdue task with the highest priority and earliest deadline.
    2. Task due today.
    3. Next pending/in-progress task prioritized by Priority (Urgent > High > Medium > Low) and nearest deadline.
    """
    # Check overdue first
    overdues = get_overdue_tasks(db_path=db_path)
    if overdues:
        return overdues[0]

    # Check today's tasks
    today_str = date.today().isoformat()
    with get_db(db_path) as conn:
        cur = conn.execute(
            """
            SELECT * FROM tasks
            WHERE status IN ('Pending', 'In Progress')
              AND deadline = ?
            ORDER BY 
                CASE priority 
                    WHEN 'Urgent' THEN 1 
                    WHEN 'High' THEN 2 
                    WHEN 'Medium' THEN 3 
                    WHEN 'Low' THEN 4 
                    ELSE 5 
                END
            LIMIT 1
            """,
            (today_str,),
        )
        row = cur.fetchone()
        if row:
            return dict(row)

    # Next general highest priority pending task
    with get_db(db_path) as conn:
        cur = conn.execute(
            """
            SELECT * FROM tasks
            WHERE status IN ('Pending', 'In Progress')
            ORDER BY 
                CASE priority 
                    WHEN 'Urgent' THEN 1 
                    WHEN 'High' THEN 2 
                    WHEN 'Medium' THEN 3 
                    WHEN 'Low' THEN 4 
                    ELSE 5 
                END,
                CASE WHEN deadline IS NULL OR deadline = '' THEN 1 ELSE 0 END,
                deadline ASC,
                id ASC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        return dict(row) if row else None
