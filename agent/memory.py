"""
Persistent Memory Module for PersonalAI.
Stores and retrieves non-sensitive user preferences, profile details, study notes, and facts.
Provides structured recall for system prompt augmentation.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from database.db import get_db, log_activity

VALID_MEMORY_CATEGORIES = {"preference", "fact", "context", "profile", "study_note"}


def save_memory(
    category: str,
    key: str,
    value: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Saves or updates a persistent memory item (upsert).
    """
    cleaned_category = (category or "fact").strip().lower()
    if cleaned_category not in VALID_MEMORY_CATEGORIES:
        cleaned_category = "fact"

    cleaned_key = (key or "").strip()
    if not cleaned_key:
        raise ValueError("Memory key cannot be empty.")

    cleaned_value = (value or "").strip()
    if not cleaned_value:
        raise ValueError("Memory value cannot be empty.")

    now = datetime.now().isoformat()

    with get_db(db_path) as conn:
        conn.execute(
            """
            INSERT INTO memories (category, key, value, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(category, key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (cleaned_category, cleaned_key, cleaned_value, now, now),
        )

    log_activity("memory_saved", f"Saved memory [{cleaned_category}] {cleaned_key} = {cleaned_value}", db_path=db_path)
    mem = get_memory(cleaned_category, cleaned_key, db_path=db_path)
    if not mem:
        raise RuntimeError("Failed to retrieve saved memory")
    return mem


def get_memory(
    category: str,
    key: str,
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Retrieves a single memory item by category and key."""
    with get_db(db_path) as conn:
        cur = conn.execute(
            "SELECT id, category, key, value, created_at, updated_at FROM memories WHERE category = ? AND key = ?",
            (category.strip().lower(), key.strip()),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_memories(
    category: Optional[str] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lists memories, optionally filtered by category."""
    query = "SELECT id, category, key, value, created_at, updated_at FROM memories"
    params: List[Any] = []
    if category:
        query += " WHERE category = ?"
        params.append(category.strip().lower())
    query += " ORDER BY category ASC, key ASC"

    with get_db(db_path) as conn:
        cur = conn.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def search_memories(
    query_text: str,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Searches memory keys and values for a query string."""
    q = f"%{(query_text or '').strip()}%"
    with get_db(db_path) as conn:
        cur = conn.execute(
            """
            SELECT id, category, key, value, created_at, updated_at 
            FROM memories
            WHERE key LIKE ? OR value LIKE ?
            ORDER BY updated_at DESC
            """,
            (q, q),
        )
        return [dict(row) for row in cur.fetchall()]


def delete_memory(
    memory_id: int,
    db_path: Optional[str] = None,
) -> bool:
    """Deletes a memory by its primary key ID."""
    with get_db(db_path) as conn:
        cur = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        deleted = cur.rowcount > 0

    if deleted:
        log_activity("memory_deleted", f"Deleted memory #{memory_id}", db_path=db_path)
    return deleted


def delete_memory_by_key(
    category: str,
    key: str,
    db_path: Optional[str] = None,
) -> bool:
    """Deletes a memory by its category and key."""
    with get_db(db_path) as conn:
        cur = conn.execute(
            "DELETE FROM memories WHERE category = ? AND key = ?",
            (category.strip().lower(), key.strip()),
        )
        deleted = cur.rowcount > 0

    if deleted:
        log_activity("memory_deleted", f"Deleted memory [{category}] {key}", db_path=db_path)
    return deleted


def clear_all_memories(db_path: Optional[str] = None) -> int:
    """Clears all stored memories."""
    with get_db(db_path) as conn:
        cur = conn.execute("DELETE FROM memories")
        count = cur.rowcount
    log_activity("memories_cleared", f"Cleared {count} memory items", db_path=db_path)
    return count


def get_memory_context_prompt(db_path: Optional[str] = None) -> str:
    """
    Builds a markdown string of explicitly saved user memories to inject into the system prompt.
    Clearly distinguishes saved facts from speculative assumptions.
    """
    mems = list_memories(db_path=db_path)
    if not mems:
        return "No explicitly saved user preferences or memory records found."

    lines = ["Saved User Preferences & Context (from Persistent Database):"]
    for m in mems:
        lines.append(f"- [{m['category'].upper()}] {m['key']}: {m['value']}")
    return "\n".join(lines)
