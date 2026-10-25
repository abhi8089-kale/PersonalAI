"""
Agent Orchestrator for PersonalAI.
Implements the core ReAct agent loop:
User Input -> Intent/Planning -> Tool Selection -> Python Tool Execution -> Tool Result -> Model Observation -> Final Response.
Includes an explicit deterministic fallback when no LLM API key is present or when offline mode is selected.
"""

import json
import re
from typing import List, Dict, Any, Optional
from agent.prompts import PERSONAL_AI_SYSTEM_PROMPT
from agent.tools import AGENT_TOOLS, execute_tool
from agent.memory import get_memory_context_prompt, save_memory
import services.llm_service as llm_service
from services.llm_service import LLMServiceError
from services.planner_service import generate_study_plan, save_confirmed_plan
from services.task_service import create_task, list_tasks, recommend_next_task, get_dashboard_stats


def is_llm_available() -> bool:
    """Checks whether the LLM is available, delegating directly to llm_service."""
    return llm_service.is_llm_available()


def chat_completion(*args, **kwargs):
    """Executes chat completion, delegating directly to llm_service."""
    return llm_service.chat_completion(*args, **kwargs)


class AgentExecutionLog:
    """Tracks tool calls and execution metrics for a single turn."""
    def __init__(self):
        self.tool_calls: List[Dict[str, Any]] = []
        self.iterations: int = 0
        self.execution_mode: str = "LLM"  # "LLM" or "OfflineRuleDispatcher"

    def add_call(self, tool_name: str, arguments: Dict[str, Any], result: Dict[str, Any]):
        self.tool_calls.append({
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.execution_mode,
            "iterations": self.iterations,
            "tool_calls_count": len(self.tool_calls),
            "tool_calls": self.tool_calls,
        }


def run_agent_turn(
    user_input: str,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    db_path: Optional[str] = None,
    max_iterations: int = 5,
    offline: bool = False,
) -> Dict[str, Any]:
    """
    Executes a single conversational agent turn with autonomous tool calling.
    
    Returns:
    {
        "response": str,
        "logs": Dict[str, Any],
        "tool_executed": bool
    }
    """
    logs = AgentExecutionLog()
    history = list(chat_history or [])

    # If offline mode is explicitly requested or no LLM is available, route to offline dispatcher
    if offline or not is_llm_available():
        logs.execution_mode = "OfflineRuleDispatcher"
        return _handle_offline_agent(user_input, logs, db_path)

    # 1. Build system prompt with current memory context
    memory_ctx = get_memory_context_prompt(db_path=db_path)
    system_prompt = PERSONAL_AI_SYSTEM_PROMPT.format(memory_context=memory_ctx)

    # 2. Construct messages list
    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    for msg in history[-8:]:  # keep last 8 messages for context window efficiency
        messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", ""),
        })
    messages.append({"role": "user", "content": user_input})

    # 3. Agent Execution Loop
    for iteration in range(1, max_iterations + 1):
        logs.iterations = iteration
        try:
            ai_turn = chat_completion(messages=messages, tools=AGENT_TOOLS, temperature=0.2)
        except LLMServiceError as e:
            err_details = str(e)
            # Check if this user request can be handled by the offline dispatcher as a fallback
            offline_fallback = _handle_offline_agent(user_input, logs, db_path, is_fallback=True)
            if offline_fallback.get("tool_executed") or "Structured Goal Plan" in offline_fallback.get("response", ""):
                return {
                    "response": (
                        f"⚠️ **Online AI Connection Error:** {err_details}\n\n"
                        f"*Fell back to local tool execution to complete your request:*\n\n"
                        f"{offline_fallback['response']}"
                    ),
                    "logs": logs.to_dict(),
                    "tool_executed": offline_fallback.get("tool_executed", False),
                }

            return {
                "response": (
                    f"❌ **Online AI Connection Error:** {err_details}\n\n"
                    "**Troubleshooting & Next Steps:**\n"
                    "1. Open **⚙️ Memory & Settings** in the sidebar to verify your API key and model.\n"
                    "2. Click **🔌 Test AI Connection** to diagnose provider endpoint status.\n"
                    "3. Check your provider quota/billing (e.g., OpenAI or Groq console).\n"
                    "4. Alternatively, use standard offline commands like *'List tasks'* or *'Recommend next task'*."
                ),
                "logs": logs.to_dict(),
                "tool_executed": len(logs.tool_calls) > 0,
            }

        content = ai_turn.get("content", "")
        tool_calls = ai_turn.get("tool_calls", [])

        # If model did not request tool calls, we have the final answer
        if not tool_calls:
            return {
                "response": content or "Task finished.",
                "logs": logs.to_dict(),
                "tool_executed": len(logs.tool_calls) > 0,
            }

        # Otherwise, append assistant message with tool calls
        assistant_msg = {
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls,
        }
        messages.append(assistant_msg)

        # Execute each requested tool in Python
        for tc in tool_calls:
            func = tc["function"]
            fn_name = func["name"]
            raw_args = func["arguments"]

            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except Exception:
                args = {}

            # Execute tool safely
            result = execute_tool(fn_name, args, db_path=db_path)
            logs.add_call(fn_name, args, result)

            # Append tool observation message
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "name": fn_name,
                "content": json.dumps(result),
            })

    # If loop exited because of max_iterations
    return {
        "response": (
            "I completed the maximum allowed reasoning steps for this request. "
            f"Here is a summary of actions executed: {len(logs.tool_calls)} tool calls made."
        ),
        "logs": logs.to_dict(),
        "tool_executed": len(logs.tool_calls) > 0,
    }


def _handle_offline_agent(
    user_input: str,
    logs: AgentExecutionLog,
    db_path: Optional[str] = None,
    is_fallback: bool = False,
) -> Dict[str, Any]:
    """
    Honest offline dispatcher when no LLM API key is configured or when offline fallback occurs.
    Directly dispatches user requests to real tools so the application remains
    100% interactive and testable without a paid LLM API key.
    """
    text = user_input.strip()
    lower = text.lower()

    if is_fallback:
        notice_prefix = ""
    else:
        notice_prefix = "⚙️ *[Offline Mode — No API Key Configured. Executed real tool via local agent dispatcher]*\n\n"

    # Intent 1: Recommend next task
    if any(k in lower for k in ["recommend", "what next", "next task", "what should i do"]):
        res = execute_tool("recommend_next_task", {}, db_path=db_path)
        logs.add_call("recommend_next_task", {}, res)
        task = res.get("task")
        if task:
            msg = (
                f"{notice_prefix}"
                f"### 🎯 Recommended Next Task:\n"
                f"- **Title:** {task['title']}\n"
                f"- **Priority:** `{task['priority']}`\n"
                f"- **Deadline:** {task['deadline'] or 'No set deadline'}\n"
                f"- **Status:** {task['status']}\n\n"
                f"*Description:* {task['description'] or 'No description provided.'}"
            )
        else:
            msg = f"{notice_prefix}🎉 You have no pending tasks! Great job, or create a new task to get started."
        return {"response": msg, "logs": logs.to_dict(), "tool_executed": True}

    # Intent 2: List tasks / Show pending
    if any(k in lower for k in ["list task", "show task", "pending task", "view task", "my tasks"]):
        status_filter = "Pending" if "pending" in lower else None
        res = execute_tool("list_tasks", {"status": status_filter}, db_path=db_path)
        logs.add_call("list_tasks", {"status": status_filter}, res)
        tasks = res.get("tasks", [])
        if not tasks:
            msg = f"{notice_prefix}No tasks found matching your criteria."
        else:
            task_lines = [f"- **#{t['id']}** {t['title']} (`{t['priority']}`) - Due: {t['deadline'] or 'N/A'} [{t['status']}]" for t in tasks[:10]]
            msg = f"{notice_prefix}### 📋 Current Tasks ({len(tasks)} found):\n" + "\n".join(task_lines)
        return {"response": msg, "logs": logs.to_dict(), "tool_executed": True}

    # Intent 3: Dashboard summary
    if any(k in lower for k in ["dashboard", "summary", "stats", "overview"]):
        res = execute_tool("get_dashboard_summary", {}, db_path=db_path)
        logs.add_call("get_dashboard_summary", {}, res)
        stats = res.get("statistics", {})
        msg = (
            f"{notice_prefix}"
            f"### 📊 Dashboard Summary:\n"
            f"- **Total Tasks:** {stats.get('total', 0)}\n"
            f"- **Pending:** {stats.get('pending', 0)}\n"
            f"- **Completed:** {stats.get('completed', 0)} ({stats.get('completion_rate', 0)}%)\n"
            f"- **Overdue:** {stats.get('overdue', 0)}\n"
            f"- **Upcoming (3 days):** {stats.get('upcoming', 0)}"
        )
        return {"response": msg, "logs": logs.to_dict(), "tool_executed": True}

    # Intent 4: Create task
    if lower.startswith("add task") or lower.startswith("create task") or "add a task" in lower or "create a task" in lower:
        # Extract title cleanly
        title = re.sub(r"^(add task|create task|add a task to|add a task|create a task)[:\s]*", "", text, flags=re.IGNORECASE).strip()
        if not title:
            title = "New Task"
        res = execute_tool("create_task", {"title": title, "category": "General", "priority": "Medium"}, db_path=db_path)
        logs.add_call("create_task", {"title": title}, res)
        t = res.get("task", {})
        msg = f"{notice_prefix}✅ Created task **#{t.get('id')}**: *{t.get('title')}* in SQLite database."
        return {"response": msg, "logs": logs.to_dict(), "tool_executed": True}

    # Intent 5: Plan goal (e.g. 7-day Java interview preparation)
    if "prepare for" in lower or "plan" in lower or "interview" in lower or "days" in lower:
        # Extract day count if specified
        days_match = re.search(r"(\d+)\s*day", lower)
        days = int(days_match.group(1)) if days_match else 7

        plan = generate_study_plan(goal_title=text, duration_days=days)
        task_preview = "\n".join([f"- **Day {t['day_number']}**: {t['title']} ({t['priority']} priority)" for t in plan["tasks"]])
        msg = (
            f"{notice_prefix}"
            f"### 🎯 Structured Goal Plan: {plan['title']}\n"
            f"Target Duration: **{plan['duration_days']} days** (Target: {plan['target_date']})\n\n"
            f"{task_preview}\n\n"
            f"💡 *Would you like me to save these {len(plan['tasks'])} tasks into your SQLite database?* "
            f"You can also review and confirm this plan directly in the **Goal Planner** page."
        )
        return {"response": msg, "logs": logs.to_dict(), "tool_executed": False}

    # Default offline message
    msg = (
        f"{notice_prefix}"
        f"I received your request: *\"{text}\"*\n\n"
        f"**Offline Agent Capabilities Available:**\n"
        f"- *'Create task: Study Operating Systems'* → Adds task to SQLite\n"
        f"- *'List pending tasks'* → Queries SQLite database\n"
        f"- *'Recommend next task'* → Analyzes priority & deadlines\n"
        f"- *'Show dashboard stats'* → Computes completion metrics\n"
        f"- *'Help me prepare for Java interview in 7 days'* → Generates structured plan\n\n"
        f"To enable real-time LLM generative multi-step reasoning, add an OpenAI-compatible API key in **Memory & Settings**."
    )
    return {"response": msg, "logs": logs.to_dict(), "tool_executed": False}
