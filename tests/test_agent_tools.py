"""
Automated tests for Agent Tool Definitions, Pydantic Schema Validation,
and Tool Execution Handlers.
"""

import pytest
from agent.tools import execute_tool
from services.task_service import get_task_by_id
from agent.memory import get_memory


def test_tool_create_task(temp_db):
    """Tests executing create_task tool with valid and missing arguments."""
    res = execute_tool(
        "create_task",
        {
            "title": "Agent Created Task",
            "description": "Created via agent function call",
            "category": "Study",
            "priority": "High",
            "deadline": "2026-11-20",
        },
        db_path=temp_db,
    )
    assert res["success"] is True
    assert res["task"]["title"] == "Agent Created Task"

    # Missing required title should fail validation
    err_res = execute_tool("create_task", {}, db_path=temp_db)
    assert err_res["success"] is False
    assert "validation failed" in err_res["error"]


def test_tool_list_tasks(temp_db):
    """Tests executing list_tasks tool."""
    execute_tool("create_task", {"title": "Task A", "priority": "High"}, db_path=temp_db)
    execute_tool("create_task", {"title": "Task B", "priority": "Low"}, db_path=temp_db)

    res = execute_tool("list_tasks", {"priority": "High"}, db_path=temp_db)
    assert res["success"] is True
    assert res["count"] == 1
    assert res["tasks"][0]["title"] == "Task A"


def test_tool_mark_task_completed(temp_db):
    """Tests executing mark_task_completed tool."""
    create_res = execute_tool("create_task", {"title": "Finish Lab"}, db_path=temp_db)
    task_id = create_res["task"]["id"]

    comp_res = execute_tool("mark_task_completed", {"task_id": task_id}, db_path=temp_db)
    assert comp_res["success"] is True
    assert comp_res["task"]["status"] == "Completed"

    # Non-existent task ID
    err_res = execute_tool("mark_task_completed", {"task_id": 9999}, db_path=temp_db)
    assert err_res["success"] is False


def test_tool_delete_task_safety_confirmation(temp_db):
    """Verifies that delete_task strictly requires confirm=True."""
    create_res = execute_tool("create_task", {"title": "Dangerous Delete"}, db_path=temp_db)
    task_id = create_res["task"]["id"]

    # Without confirmation
    unconf_res = execute_tool("delete_task", {"task_id": task_id, "confirm": False}, db_path=temp_db)
    assert unconf_res["success"] is False
    assert "requires explicit confirmation" in unconf_res["error"]
    assert get_task_by_id(task_id, db_path=temp_db) is not None

    # With confirmation
    conf_res = execute_tool("delete_task", {"task_id": task_id, "confirm": True}, db_path=temp_db)
    assert conf_res["success"] is True
    assert get_task_by_id(task_id, db_path=temp_db) is None


def test_tool_memory_operations(temp_db):
    """Tests save_memory and recall_memory tools."""
    save_res = execute_tool(
        "save_memory",
        {"category": "preference", "key": "target_role", "value": "Backend Engineer"},
        db_path=temp_db,
    )
    assert save_res["success"] is True

    mem = get_memory("preference", "target_role", db_path=temp_db)
    assert mem is not None
    assert mem["value"] == "Backend Engineer"

    # Recall
    recall_res = execute_tool("recall_memory", {"query": "Backend"}, db_path=temp_db)
    assert recall_res["success"] is True
    assert recall_res["count"] >= 1


def test_tool_save_goal_plan(temp_db):
    """Tests save_goal_plan confirmation and persistence."""
    plan_args = {
        "title": "7-Day Sprint",
        "category": "Study",
        "target_date": "2026-11-01",
        "confirm": False,
        "tasks": [
            {"day_number": 1, "title": "Day 1 Setup", "priority": "High"},
            {"day_number": 2, "title": "Day 2 Implementation", "priority": "Urgent"},
        ],
    }

    # Without confirm, returns preview plan
    preview = execute_tool("save_goal_plan", plan_args, db_path=temp_db)
    assert preview["success"] is False
    assert "requires user confirmation" in preview["error"]

    # With confirm=True, saves atomically
    plan_args["confirm"] = True
    save_res = execute_tool("save_goal_plan", plan_args, db_path=temp_db)
    assert save_res["success"] is True
    assert save_res["goal"]["tasks_count"] == 2


def test_unknown_tool_rejection(temp_db):
    """Tests that unknown tool names fail cleanly."""
    res = execute_tool("drop_database_all", {}, db_path=temp_db)
    assert res["success"] is False
    assert "Unknown tool" in res["error"]
