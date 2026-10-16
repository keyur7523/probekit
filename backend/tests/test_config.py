"""Tests for settings parsing."""

import pytest
from sqlalchemy.dialects.postgresql.asyncpg import dialect
from sqlalchemy.engine import make_url

from app.config import Settings


@pytest.mark.parametrize('url,expected', [
    ('postgres://u:p@host:5432/db', 'postgresql+asyncpg://u:p@host:5432/db'),
    ('postgresql://u:p@host/db', 'postgresql+asyncpg://u:p@host/db'),
    ('postgresql+asyncpg://u:p@host/db', 'postgresql+asyncpg://u:p@host/db'),
    ('sqlite+aiosqlite:///:memory:', 'sqlite+aiosqlite:///:memory:'),
    # Neon connection string
    (
        'postgresql://u:p@ep-x-123.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require',
        'postgresql+asyncpg://u:p@ep-x-123.us-east-2.aws.neon.tech/neondb?ssl=require',
    ),
    ('postgresql+asyncpg://u:p@host/db?sslmode=require', 'postgresql+asyncpg://u:p@host/db?ssl=require'),
])
def test_database_url_uses_asyncpg(url, expected):
    assert Settings(database_url=url, _env_file=None).database_url == expected


def test_neon_url_reaches_asyncpg_with_supported_args():
    url = Settings(
        database_url='postgresql://u:p@ep-x.neon.tech/neondb?sslmode=require&channel_binding=require',
        _env_file=None,
    ).database_url
    _, kwargs = dialect().create_connect_args(make_url(url))
    assert kwargs['ssl'] == 'require'
    assert 'sslmode' not in kwargs and 'channel_binding' not in kwargs
