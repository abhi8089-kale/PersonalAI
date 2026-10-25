"""
Pytest configuration and fixtures.
Provides isolated temporary SQLite database for test execution.
"""

import os
import pytest
from database.db import init_db


@pytest.fixture
def temp_db(tmp_path):
    """
    Creates an isolated temporary SQLite database for each test,
    ensuring real user data is never touched.
    """
    db_file = str(tmp_path / "test_personal_ai.db")
    init_db(db_file)
    return db_file
