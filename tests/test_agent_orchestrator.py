"""
Automated tests for the Agent Orchestrator:
- Offline mode tool execution
- LLM tool calling loop and maximum iteration safety guards
- Missing API key graceful degradation
"""

from unittest.mock import patch
import pytest
from agent.orchestrator import run_agent_turn
from agent.memory import save_memory, get_memory_context_prompt
from services.task_service import list_tasks


def test_offline_agent_dispatch_create_task(temp_db):
    """Verifies that in offline mode, natural commands like 'create task ...' execute real tools."""
    with patch("services.llm_service.is_llm_available", return_value=False):
        result = run_agent_turn(
            user_input="Create task: Review Computer Networks chapter 3",
            db_path=temp_db,
        )

    assert result["tool_executed"] is True
    assert "Created task" in result["response"]
    tasks = list_tasks(db_path=temp_db)
    assert any("Computer Networks" in t["title"] for t in tasks)


def test_offline_agent_recommend_next_task(temp_db):
    """Tests offline intent dispatch for task recommendations."""
    from services.task_service import create_task
    create_task(title="Prepare OS presentation", priority="Urgent", db_path=temp_db)

    with patch("agent.orchestrator.is_llm_available", return_value=False):
        result = run_agent_turn(
            user_input="What should I do next?",
            db_path=temp_db,
        )

    assert result["tool_executed"] is True
    assert "Recommended Next Task" in result["response"]
    assert "Prepare OS presentation" in result["response"]


def test_offline_agent_goal_planning(temp_db):
    """Tests offline intent dispatch for 7-day interview goal planning."""
    with patch("services.llm_service.is_llm_available", return_value=False):
        result = run_agent_turn(
            user_input="Help me prepare for my Java interview in 7 days",
            db_path=temp_db,
        )

    assert "Structured Goal Plan" in result["response"]
    assert "Day 1" in result["response"]


def test_agent_iteration_limit_safety(temp_db):
    """
    Verifies that the agent loop strictly terminates at max_iterations
    if the LLM repeatedly calls tools without reaching a terminal response.
    """
    # Mock LLM constantly returning a tool call
    mock_llm_response = {
        "content": "",
        "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "list_tasks",
                    "arguments": "{}",
                },
            }
        ],
        "model": "gpt-4o-mini",
        "finish_reason": "tool_calls",
    }

    with patch("agent.orchestrator.is_llm_available", return_value=True), \
         patch("agent.orchestrator.chat_completion", return_value=mock_llm_response):
        
        result = run_agent_turn(
            user_input="Keep looping tasks",
            db_path=temp_db,
            max_iterations=3,
        )

    assert result["logs"]["iterations"] == 3
    assert "maximum allowed reasoning steps" in result["response"]


def test_memory_prompt_injection(temp_db):
    """Verifies that stored user memories are correctly injected into system prompts."""
    save_memory("preference", "preferred_language", "Java 17", db_path=temp_db)
    save_memory("profile", "target_company", "Google", db_path=temp_db)

    ctx = get_memory_context_prompt(db_path=temp_db)
    assert "[PREFERENCE] preferred_language: Java 17" in ctx
    assert "[PROFILE] target_company: Google" in ctx
