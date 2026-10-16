"""Tests for settings parsing."""

import pytest

from app.config import Settings


@pytest.mark.parametrize('url,expected', [
    ('postgres://u:p@host:5432/db', 'postgresql+asyncpg://u:p@host:5432/db'),
    ('postgresql://u:p@host/db', 'postgresql+asyncpg://u:p@host/db'),
    ('postgresql+asyncpg://u:p@host/db', 'postgresql+asyncpg://u:p@host/db'),
    ('sqlite+aiosqlite:///:memory:', 'sqlite+aiosqlite:///:memory:'),
])
def test_database_url_uses_asyncpg(url, expected):
    assert Settings(database_url=url, _env_file=None).database_url == expected
