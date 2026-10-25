"""
Automated tests for Planner Service, Study Helper Service, and LLM Service.
"""

from unittest.mock import patch
import pytest
from services.planner_service import (
    generate_study_plan,
    save_confirmed_plan,
    get_goal_progress,
    list_goals,
)
from services.study_service import (
    explain_concept,
    generate_interview_questions,
    get_quiz_questions,
    evaluate_user_answer,
)
from services.llm_service import is_llm_available, get_llm_config, LLMServiceError


def test_planner_curriculum_generation():
    """Tests generating a 7-day structured study curriculum for Java."""
    plan = generate_study_plan("Prepare for Java Interview", duration_days=7)

    assert plan["title"] == "Prepare for Java Interview"
    assert plan["duration_days"] == 7
    assert len(plan["tasks"]) == 7
    assert "OOP Principles" in plan["tasks"][0]["title"]
    assert plan["tasks"][0]["priority"] == "High"
    assert plan["tasks"][0]["suggested_deadline"] is not None


def test_save_confirmed_plan_atomic_persistence(temp_db):
    """Verifies that confirming a plan creates both the goal and linked tasks."""
    plan = generate_study_plan("Prepare for Python Exam", duration_days=3)
    saved = save_confirmed_plan(
        title=plan["title"],
        category="Study",
        target_date=plan["target_date"],
        tasks=plan["tasks"],
        db_path=temp_db,
    )

    assert saved["goal_id"] is not None
    assert saved["tasks_count"] == 3

    prog = get_goal_progress(saved["goal_id"], db_path=temp_db)
    assert prog["total"] == 3
    assert prog["completed"] == 0
    assert prog["completion_rate"] == 0.0

    all_goals = list_goals(db_path=temp_db)
    assert len(all_goals) == 1
    assert all_goals[0]["title"] == "Prepare for Python Exam"


def test_study_service_concept_explainer():
    """Tests concept explanation fallback when offline."""
    with patch("services.llm_service.is_llm_available", return_value=False):
        res = explain_concept("HashMap")
    assert "HashMap" in res["concept"]
    assert "Core Intuition" in res["explanation"]


def test_study_service_quiz_and_interview_questions():
    """Tests fetching quiz and technical questions from offline knowledge bank."""
    java_q = generate_interview_questions("java", count=3)
    assert len(java_q) >= 1
    assert any("String" in q["question"] or "HashMap" in q["question"] for q in java_q)

    quizzes = get_quiz_questions("python")
    assert len(quizzes) >= 1
    assert "quiz_options" in quizzes[0]


def test_study_service_answer_evaluation():
    """Tests scoring and feedback for student interview answers."""
    with patch("services.llm_service.is_llm_available", return_value=False):
        eval_empty = evaluate_user_answer("What is GIL?", "")
        assert eval_empty["score"] == 0

        eval_good = evaluate_user_answer(
            "What is GIL?",
            "The Global Interpreter Lock is a mutex in CPython that prevents multiple native threads from executing Python bytecode simultaneously to protect memory management.",
            expected_points=["mutex protects access", "single thread bytecode"],
        )
        assert eval_good["score"] >= 6
        assert len(eval_good["strengths"]) > 0


def test_llm_service_configuration():
    """Verifies safe configuration handling and key masking."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
        assert is_llm_available() is False

    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test1234567890"}):
        assert is_llm_available() is True
        cfg = get_llm_config()
        assert cfg["api_key"] == "sk-test1234567890"
