"""
Agent Tools Registry for PersonalAI.
Defines OpenAI-compatible function declarations, Pydantic validation schemas,
and actual Python execution handlers.
"""

import json
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ValidationError
from services.task_service import (
    create_task,
    list_tasks,
    update_task,
    mark_task_status,
    delete_task,
    recommend_next_task,
    get_dashboard_stats,
    get_overdue_tasks,
    get_upcoming_tasks,
)
from agent.memory import save_memory, search_memories, list_memories

# ---------------------------------------------------------------------------
# Pydantic Schemas for Tool Argument Validation
# ---------------------------------------------------------------------------

class CreateTaskArgs(BaseModel):
    title: str = Field(..., min_length=1, description="Title of the task to create")
    description: Optional[str] = Field("", description="Detailed explanation or notes for the task")
    category: Optional[str] = Field("General", description="Category: Study, Work, Personal, Assignment, Interview, General")
    priority: Optional[str] = Field("Medium", description="Priority level: Low, Medium, High, Urgent")
    deadline: Optional[str] = Field(None, description="Deadline in YYYY-MM-DD format (e.g. '2026-11-01')")

class ListTasksArgs(BaseModel):
    status: Optional[str] = Field(None, description="Filter by status: Pending, In Progress, Completed, Cancelled")
    priority: Optional[str] = Field(None, description="Filter by priority: Low, Medium, High, Urgent")
    category: Optional[str] = Field(None, description="Filter by category: Study, Work, Personal, Assignment, Interview, General")
    search: Optional[str] = Field(None, description="Keyword search in title and description")

class UpdateTaskArgs(BaseModel):
    task_id: int = Field(..., description="Unique integer ID of the task to update")
    title: Optional[str] = Field(None, description="New title for the task")
    description: Optional[str] = Field(None, description="New description")
    category: Optional[str] = Field(None, description="New category")
    priority: Optional[str] = Field(None, description="New priority: Low, Medium, High, Urgent")
    status: Optional[str] = Field(None, description="New status: Pending, In Progress, Completed, Cancelled")
    deadline: Optional[str] = Field(None, description="New deadline in YYYY-MM-DD format")

class MarkTaskCompletedArgs(BaseModel):
    task_id: int = Field(..., description="ID of the task to mark as completed")

class DeleteTaskArgs(BaseModel):
    task_id: int = Field(..., description="ID of the task to delete")
    confirm: bool = Field(False, description="Must be explicitly True to confirm deletion")

class RecommendNextTaskArgs(BaseModel):
    pass

class GetDashboardSummaryArgs(BaseModel):
    pass

class SaveMemoryArgs(BaseModel):
    category: str = Field(..., description="Memory category: preference, fact, context, profile, study_note")
    key: str = Field(..., min_length=1, description="Short identifier or topic (e.g., 'target_role', 'interview_date')")
    value: str = Field(..., min_length=1, description="Value or information to remember")

class RecallMemoryArgs(BaseModel):
    query: Optional[str] = Field(None, description="Keyword or phrase to search saved memories")
    category: Optional[str] = Field(None, description="Optional category filter")

class DailyTaskPlanItem(BaseModel):
    day_number: int = Field(..., description="Day number (e.g. 1, 2, ...)")
    title: str = Field(..., description="Task title")
    description: str = Field("", description="Detailed topic or learning milestone")
    priority: str = Field("High", description="Priority: Low, Medium, High, Urgent")
    estimated_hours: Optional[float] = Field(2.0, description="Estimated hours")

class SaveGoalPlanArgs(BaseModel):
    title: str = Field(..., description="Title of the goal/plan (e.g. '7-Day Java Interview Preparation')")
    category: Optional[str] = Field("Study", description="Goal category")
    target_date: Optional[str] = Field(None, description="Target completion date YYYY-MM-DD")
    tasks: List[DailyTaskPlanItem] = Field(..., min_length=1, description="List of structured daily tasks")
    confirm: bool = Field(False, description="Explicit confirmation to save into database")


# ---------------------------------------------------------------------------
# OpenAI Tools Specification Schema
# ---------------------------------------------------------------------------

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a new task and save it into the persistent SQLite database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the task"},
                    "description": {"type": "string", "description": "Detailed notes or steps for the task"},
                    "category": {"type": "string", "enum": ["Study", "Work", "Personal", "Assignment", "Interview", "General"], "description": "Category"},
                    "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Urgent"], "description": "Priority level"},
                    "deadline": {"type": "string", "description": "Deadline date in YYYY-MM-DD format"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "Retrieve tasks from SQLite with optional filtering by status, priority, category, or search term.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["Pending", "In Progress", "Completed", "Cancelled"], "description": "Filter by status"},
                    "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Urgent"], "description": "Filter by priority"},
                    "category": {"type": "string", "enum": ["Study", "Work", "Personal", "Assignment", "Interview", "General"], "description": "Filter by category"},
                    "search": {"type": "string", "description": "Search keyword matching title or description"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mark_task_completed",
            "description": "Mark an existing task as Completed by its task ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "ID of the task to complete"}
                },
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": "Update details, deadline, priority, or status of an existing task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "ID of task to update"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "category": {"type": "string"},
                    "priority": {"type": "string", "enum": ["Low", "Medium", "High", "Urgent"]},
                    "status": {"type": "string", "enum": ["Pending", "In Progress", "Completed", "Cancelled"]},
                    "deadline": {"type": "string", "description": "YYYY-MM-DD"}
                },
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_task",
            "description": "Delete a task from the database. Requires confirm=True.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "ID of the task to delete"},
                    "confirm": {"type": "boolean", "description": "Must be true to authorize deletion"}
                },
                "required": ["task_id", "confirm"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_next_task",
            "description": "Analyze pending tasks and recommend the single most urgent or important task to do next.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_dashboard_summary",
            "description": "Get current task statistics: total, pending, completed, overdue, upcoming, and completion rate.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Store a user preference, profile fact, study note, or context in persistent memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": ["preference", "fact", "context", "profile", "study_note"], "description": "Category"},
                    "key": {"type": "string", "description": "Identifier key (e.g. 'preferred_language', 'target_company')"},
                    "value": {"type": "string", "description": "Content to remember"}
                },
                "required": ["category", "key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "Search or retrieve stored user preferences, profile facts, or study notes from persistent memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword to search"},
                    "category": {"type": "string", "description": "Optional category filter"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_goal_plan",
            "description": "Save a structured goal plan and automatically populate SQLite with its individual daily tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the goal"},
                    "category": {"type": "string", "description": "Category (e.g. Study, Interview)"},
                    "target_date": {"type": "string", "description": "Target completion date (YYYY-MM-DD)"},
                    "confirm": {"type": "boolean", "description": "Confirmation to write to database"},
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "day_number": {"type": "integer"},
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "priority": {"type": "string"},
                                "estimated_hours": {"type": "number"}
                            },
                            "required": ["day_number", "title"]
                        }
                    }
                },
                "required": ["title", "tasks", "confirm"]
            }
        }
    }
]


# ---------------------------------------------------------------------------
# Python Tool Handlers Execution
# ---------------------------------------------------------------------------

def execute_tool(name: str, arguments: Dict[str, Any], db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Validates arguments with Pydantic and executes the real Python function.
    Returns a structured dictionary representing the tool output.
    """
    try:
        if name == "create_task":
            args = CreateTaskArgs(**arguments)
            task = create_task(
                title=args.title,
                description=args.description or "",
                category=args.category or "General",
                priority=args.priority or "Medium",
                deadline=args.deadline,
                db_path=db_path,
            )
            return {
                "success": True,
                "message": f"Task #{task['id']} '{task['title']}' created successfully.",
                "task": task,
            }

        elif name == "list_tasks":
            args = ListTasksArgs(**arguments)
            tasks = list_tasks(
                status=args.status,
                priority=args.priority,
                category=args.category,
                search=args.search,
                db_path=db_path,
            )
            return {
                "success": True,
                "count": len(tasks),
                "tasks": tasks,
            }

        elif name == "mark_task_completed":
            args = MarkTaskCompletedArgs(**arguments)
            updated = mark_task_status(task_id=args.task_id, status="Completed", db_path=db_path)
            if not updated:
                return {"success": False, "error": f"Task #{args.task_id} not found."}
            return {
                "success": True,
                "message": f"Task #{args.task_id} marked as Completed.",
                "task": updated,
            }

        elif name == "update_task":
            args = UpdateTaskArgs(**arguments)
            updated = update_task(
                task_id=args.task_id,
                title=args.title,
                description=args.description,
                category=args.category,
                priority=args.priority,
                status=args.status,
                deadline=args.deadline,
                db_path=db_path,
            )
            if not updated:
                return {"success": False, "error": f"Task #{args.task_id} not found."}
            return {
                "success": True,
                "message": f"Task #{args.task_id} updated successfully.",
                "task": updated,
            }

        elif name == "delete_task":
            args = DeleteTaskArgs(**arguments)
            if not args.confirm:
                return {
                    "success": False,
                    "error": "Deletion requires explicit confirmation (confirm=True). Please ask the user to confirm before proceeding.",
                }
            deleted = delete_task(task_id=args.task_id, db_path=db_path)
            if not deleted:
                return {"success": False, "error": f"Task #{args.task_id} not found."}
            return {"success": True, "message": f"Task #{args.task_id} deleted permanently."}

        elif name == "recommend_next_task":
            rec = recommend_next_task(db_path=db_path)
            if not rec:
                return {
                    "success": True,
                    "message": "No pending tasks found! You have cleared your task list or haven't created any tasks yet.",
                    "task": None,
                }
            return {
                "success": True,
                "recommendation": f"Next suggested task: #{rec['id']} - {rec['title']}",
                "task": rec,
            }

        elif name == "get_dashboard_summary":
            stats = get_dashboard_stats(db_path=db_path)
            overdue = get_overdue_tasks(db_path=db_path)
            upcoming = get_upcoming_tasks(days=3, db_path=db_path)
            return {
                "success": True,
                "statistics": stats,
                "overdue_count": len(overdue),
                "upcoming_count": len(upcoming),
            }

        elif name == "save_memory":
            args = SaveMemoryArgs(**arguments)
            mem = save_memory(
                category=args.category,
                key=args.key,
                value=args.value,
                db_path=db_path,
            )
            return {
                "success": True,
                "message": f"Saved preference in persistent memory: [{mem['category']}] {mem['key']} = {mem['value']}",
                "memory": mem,
            }

        elif name == "recall_memory":
            args = RecallMemoryArgs(**arguments)
            if args.query:
                results = search_memories(args.query, db_path=db_path)
            else:
                results = list_memories(category=args.category, db_path=db_path)
            return {
                "success": True,
                "count": len(results),
                "memories": results,
            }

        elif name == "save_goal_plan":
            args = SaveGoalPlanArgs(**arguments)
            # Import planner service to avoid circular dependency
            from services.planner_service import save_confirmed_plan
            dumped_tasks = [t.model_dump() if hasattr(t, "model_dump") else t.dict() for t in args.tasks]
            if not args.confirm:
                return {
                    "success": False,
                    "error": "Saving goal plan requires user confirmation. Present the structured plan to the user first.",
                    "preview_plan": {
                        "title": args.title,
                        "tasks_count": len(args.tasks),
                        "tasks": dumped_tasks,
                    },
                }

            goal_res = save_confirmed_plan(
                title=args.title,
                category=args.category or "Study",
                target_date=args.target_date,
                tasks=dumped_tasks,
                db_path=db_path,
            )
            return {
                "success": True,
                "message": f"Goal '{args.title}' and {len(args.tasks)} daily tasks were saved to the database.",
                "goal": goal_res,
            }

        else:
            return {"success": False, "error": f"Unknown tool '{name}'."}

    except ValidationError as ve:
        return {"success": False, "error": f"Tool argument validation failed: {ve.errors()}"}
    except Exception as e:
        return {"success": False, "error": f"Tool execution error: {str(e)}"}
