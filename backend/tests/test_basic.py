"""
Basic tests to verify setup
"""

import pytest


def test_basic_import():
    """Test that basic imports work"""
    try:
        from core.config import settings
        assert settings is not None
    except ImportError as e:
        pytest.fail(f"Failed to import core.config: {e}")


def test_environment():
    """Test that environment is set correctly"""
    import os
    assert os.getenv("ENVIRONMENT") == "test"


def test_database_url():
    """Test that database URL is set"""
    import os
    db_url = os.getenv("DATABASE_URL")
    assert db_url is not None
    assert "postgresql" in db_url or "sqlite" in db_url