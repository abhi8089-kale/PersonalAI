"""
Automated tests for Database Initialization and Logging.
"""

import sqlite3
import pytest
from database.db import (
    get_connection,
    get_db,
    init_db,
    log_activity,
    get_recent_activities,
    reset_database,
)


def test_database_initialization(temp_db):
    """Verifies that all tables are properly created on initialization."""
    with get_db(temp_db) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        )
        tables = [row["name"] for row in cursor.fetchall()]

    assert "tasks" in tables
    assert "goals" in tables
    assert "memories" in tables
    assert "activity_logs" in tables


def test_activity_logging(temp_db):
    """Verifies that events are correctly recorded in the activity_logs table."""
    log_activity("test_event", "Demonstration activity details", db_path=temp_db)
    activities = get_recent_activities(limit=5, db_path=temp_db)

    assert len(activities) >= 1
    assert activities[0]["action"] == "test_event"
    assert "Demonstration activity details" in activities[0]["details"]


def test_database_reset(temp_db):
    """Verifies that reset_database wipes tables and reinitializes empty schemas."""
    # Insert dummy task
    with get_db(temp_db) as conn:
        conn.execute(
            "INSERT INTO tasks (title, created_at, updated_at) VALUES ('Temp Task', '2026-01-01', '2026-01-01')"
        )

    reset_database(temp_db)

    with get_db(temp_db) as conn:
        cur = conn.execute("SELECT COUNT(*) as cnt FROM tasks")
        assert cur.fetchone()["cnt"] == 0
