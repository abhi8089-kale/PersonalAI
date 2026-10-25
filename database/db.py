"""
Database module for PersonalAI.
Provides thread-safe SQLite connection management, initialization, and logging.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, List, Dict, Any, Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "personal_ai.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def get_db_path() -> str:
    """Returns the database path, allowing override via DB_PATH environment variable."""
    return os.getenv("PERSONAL_AI_DB_PATH", DEFAULT_DB_PATH)


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Creates and returns a SQLite connection with Row factory enabled.
    Enables foreign keys and WAL mode for reliability.
    """
    path = db_path or get_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


@contextmanager
def get_db(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for safe database transactions with auto-commit and rollback."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes the SQLite database with the tables from schema.sql."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    with get_db(db_path) as conn:
        conn.executescript(schema_sql)


def log_activity(action: str, details: str, db_path: Optional[str] = None) -> None:
    """Logs an activity event in the database."""
    now = datetime.now().isoformat()
    with get_db(db_path) as conn:
        conn.execute(
            "INSERT INTO activity_logs (action, details, timestamp) VALUES (?, ?, ?)",
            (action, details, now),
        )


def get_recent_activities(limit: int = 10, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches recent activity logs."""
    with get_db(db_path) as conn:
        cur = conn.execute(
            "SELECT id, action, details, timestamp FROM activity_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


def reset_database(db_path: Optional[str] = None) -> None:
    """Safely wipes all tables and re-initializes schema. Used for tests or user data reset."""
    with get_db(db_path) as conn:
        conn.execute("DROP TABLE IF EXISTS tasks;")
        conn.execute("DROP TABLE IF EXISTS goals;")
        conn.execute("DROP TABLE IF EXISTS memories;")
        conn.execute("DROP TABLE IF EXISTS activity_logs;")
    init_db(db_path)
