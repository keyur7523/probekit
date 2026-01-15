from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import get_settings

settings = get_settings()

# Import all models so Base.metadata.create_all() creates them
# This is used for environments without Alembic shell access (e.g., Render free tier)
def _import_models():
    from app.models import (  # noqa: F401
        TestCase,
        EvaluationRun,
        EvaluationOutput,
        EvaluatorResult,
        HumanAnnotation,
        ConversationRun,
        ConversationTurn,
        TurnEvaluatorResult,
        ConversationEvaluatorResult,
    )

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables. Use Alembic for migrations in production."""
    _import_models()  # Ensure all models are registered with Base.metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Minimal schema sync for hosted environments without migration access.
        await conn.execute(text(
            "ALTER TABLE IF EXISTS test_cases "
            "ADD COLUMN IF NOT EXISTS instruction_spec JSON"
        ))
        await conn.execute(text(
            "ALTER TABLE IF EXISTS test_cases "
            "ADD COLUMN IF NOT EXISTS format_spec JSON"
        ))
        await conn.execute(text(
            "ALTER TABLE IF EXISTS test_cases "
            "ADD COLUMN IF NOT EXISTS stability_params JSON"
        ))
        await conn.execute(text(
            "ALTER TABLE IF EXISTS test_cases "
            "ADD COLUMN IF NOT EXISTS should_refuse BOOLEAN"
        ))
        await conn.execute(text(
            "ALTER TABLE IF EXISTS test_cases "
            "ADD COLUMN IF NOT EXISTS title VARCHAR(200)"
        ))
        await conn.execute(text(
            "ALTER TABLE IF EXISTS conversation_turns "
            "ADD COLUMN IF NOT EXISTS condition VARCHAR(50)"
        ))
        await conn.execute(text(
            "ALTER TABLE IF EXISTS conversation_turns "
            "ADD COLUMN IF NOT EXISTS model_id VARCHAR(100)"
        ))
