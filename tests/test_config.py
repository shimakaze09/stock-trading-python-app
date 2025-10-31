"""Test configuration and settings."""

import pytest
from config import get_settings


def test_settings_loaded():
    """Test that settings can be loaded."""
    settings = get_settings()
    assert settings is not None
    assert settings.POLYGON_API_KEY is not None
    assert settings.MAX_API_CALLS_PER_MINUTE == 5


def test_database_url():
    """Test database URL construction."""
    settings = get_settings()
    db_url = settings.DATABASE_URL
    assert 'postgresql://' in db_url
    assert str(settings.DB_PORT) in db_url
    assert settings.DB_NAME in db_url

