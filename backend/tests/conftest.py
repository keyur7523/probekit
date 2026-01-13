import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from app.database import Base
from app.main import app
from app.database import get_db
from app.clients.base import LLMResponse
from app.evaluators.base import EvaluationContext


# Use SQLite for testing (in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        yield session


@pytest.fixture
async def client(test_engine):
    """Create a test HTTP client with test database."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def mock_llm_response():
    """Factory for creating mock LLM responses."""
    def _create(
        content: str = "Test response",
        input_tokens: int = 100,
        output_tokens: int = 50,
        latency_ms: int = 500,
        cost_usd: float = 0.001,
        model: str = "test-model",
    ) -> LLMResponse:
        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            model=model,
        )
    return _create


@pytest.fixture
def mock_claude_client(mock_llm_response):
    """Create a mock Claude client."""
    client = AsyncMock()
    client.generate = AsyncMock(return_value=mock_llm_response())
    client.calculate_cost = MagicMock(return_value=0.001)
    client.model_id = "claude-3-5-sonnet-20241022"
    return client


@pytest.fixture
def mock_openai_client(mock_llm_response):
    """Create a mock OpenAI client."""
    client = AsyncMock()
    client.generate = AsyncMock(return_value=mock_llm_response())
    client.calculate_cost = MagicMock(return_value=0.001)
    client.model_id = "gpt-4o"
    return client


@pytest.fixture
def evaluation_context_factory():
    """Factory for creating evaluation contexts."""
    def _create(
        output: str = "This is a test response.",
        prompt: str = "Test prompt",
        input_text: str = "Test input",
        context: str | None = None,
        expected_structure: dict | None = None,
        category: str | None = None,
    ) -> EvaluationContext:
        return EvaluationContext(
            output=output,
            prompt=prompt,
            input_text=input_text,
            context=context,
            expected_structure=expected_structure,
            category=category,
        )
    return _create


@pytest.fixture
def sample_test_case_data():
    """Sample test case data for API tests."""
    return {
        "prompt": "Summarize the following text in 2-3 sentences.",
        "input": "The quick brown fox jumps over the lazy dog.",
        "category": "summarization",
    }


@pytest.fixture
def sample_json_output():
    """Sample JSON output for format testing."""
    return '{"entities": ["fox", "dog"], "summary": "A fox jumps over a dog.", "confidence": 0.95}'


@pytest.fixture
def sample_hallucination_context():
    """Sample context for hallucination testing."""
    return {
        "context": "The company was founded in 2020. It has 50 employees. Revenue was $1M in 2023.",
        "grounded_response": "The company was founded in 2020 and has 50 employees.",
        "hallucinated_response": "The company was founded in 2015 and has 500 employees with $10M revenue.",
    }
