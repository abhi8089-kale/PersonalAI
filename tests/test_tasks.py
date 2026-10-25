"""
Automated tests for Task Service CRUD operations, validations, and recommendations.
"""

from datetime import date, timedelta
import pytest
from services.task_service import (
    create_task,
    get_task_by_id,
    list_tasks,
    update_task,
    mark_task_status,
    delete_task,
    get_dashboard_stats,
    get_overdue_tasks,
    get_upcoming_tasks,
    recommend_next_task,
)


def test_create_and_retrieve_task(temp_db):
    """Tests creating a task and retrieving it by ID."""
    task = create_task(
        title="Study Memory Architecture",
        description="Review cache hierarchy and virtual paging",
        category="Study",
        priority="High",
        deadline="2026-11-10",
        db_path=temp_db,
    )

    assert task["id"] is not None
    assert task["title"] == "Study Memory Architecture"
    assert task["priority"] == "High"
    assert task["status"] == "Pending"

    fetched = get_task_by_id(task["id"], db_path=temp_db)
    assert fetched is not None
    assert fetched["title"] == task["title"]


def test_invalid_task_inputs(temp_db):
    """Tests that invalid inputs trigger appropriate errors."""
    with pytest.raises(ValueError, match="cannot be empty"):
        create_task(title="", db_path=temp_db)

    with pytest.raises(ValueError, match="cannot be empty"):
        create_task(title="   ", db_path=temp_db)

    # Creating with unlisted priority defaults safely to 'Medium'
    t = create_task(title="Valid Title", priority="InvalidPriority", db_path=temp_db)
    assert t["priority"] == "Medium"


def test_update_and_completion_flow(temp_db):
    """Tests updating attributes and verifying completion timestamp."""
    task = create_task(title="Original Title", priority="Low", db_path=temp_db)
    t_id = task["id"]

    updated = update_task(
        task_id=t_id,
        title="Updated Title",
        priority="Urgent",
        status="In Progress",
        db_path=temp_db,
    )
    assert updated["title"] == "Updated Title"
    assert updated["priority"] == "Urgent"
    assert updated["status"] == "In Progress"
    assert updated["completed_at"] is None

    # Mark completed
    completed = mark_task_status(task_id=t_id, status="Completed", db_path=temp_db)
    assert completed["status"] == "Completed"
    assert completed["completed_at"] is not None


def test_task_deletion(temp_db):
    """Tests deleting an existing task and handling non-existent ID."""
    task = create_task(title="To be deleted", db_path=temp_db)
    t_id = task["id"]

    assert delete_task(t_id, db_path=temp_db) is True
    assert get_task_by_id(t_id, db_path=temp_db) is None
    # Deleting again returns False
    assert delete_task(t_id, db_path=temp_db) is False


def test_list_tasks_and_filters(temp_db):
    """Tests filtering by category, status, priority, and search."""
    create_task(title="Java Multithreading", category="Study", priority="High", db_path=temp_db)
    create_task(title="Python Decorators", category="Study", priority="Medium", db_path=temp_db)
    t3 = create_task(title="Submit Assignment", category="Assignment", priority="Urgent", db_path=temp_db)
    mark_task_status(t3["id"], "Completed", db_path=temp_db)

    study_tasks = list_tasks(category="Study", db_path=temp_db)
    assert len(study_tasks) == 2

    completed_tasks = list_tasks(status="Completed", db_path=temp_db)
    assert len(completed_tasks) == 1
    assert completed_tasks[0]["title"] == "Submit Assignment"

    search_res = list_tasks(search="Multithreading", db_path=temp_db)
    assert len(search_res) == 1
    assert search_res[0]["title"] == "Java Multithreading"


def test_dashboard_metrics_calculation(temp_db):
    """Tests dashboard metric counts and completion percentage."""
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    tomorrow = (today + timedelta(days=1)).isoformat()

    # 1 Overdue pending task
    create_task(title="Overdue Task", deadline=yesterday, priority="High", db_path=temp_db)
    # 1 Upcoming task
    create_task(title="Upcoming Task", deadline=tomorrow, priority="Medium", db_path=temp_db)
    # 1 Completed task
    t_comp = create_task(title="Done Task", priority="Low", db_path=temp_db)
    mark_task_status(t_comp["id"], "Completed", db_path=temp_db)

    stats = get_dashboard_stats(db_path=temp_db)
    assert stats["total"] == 3
    assert stats["pending"] == 2
    assert stats["completed"] == 1
    assert stats["overdue"] == 1
    assert stats["upcoming"] == 1
    assert stats["completion_rate"] == 33.3


def test_smart_task_recommendation(temp_db):
    """Verifies that overdue tasks are prioritized first, then highest priority."""
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    future = (today + timedelta(days=5)).isoformat()

    # Create low priority overdue
    create_task(title="Low Overdue", deadline=yesterday, priority="Low", db_path=temp_db)
    # Create urgent future
    create_task(title="Urgent Future", deadline=future, priority="Urgent", db_path=temp_db)

    # Overdue should be recommended first
    rec = recommend_next_task(db_path=temp_db)
    assert rec is not None
    assert rec["title"] == "Low Overdue"
