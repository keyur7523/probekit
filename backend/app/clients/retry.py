"""Retry helper with exponential backoff for LLM API calls."""

import asyncio
import random
import logging
from typing import TypeVar, Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')

# HTTP status codes that should trigger a retry
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Exception types that should trigger a retry
RETRYABLE_EXCEPTIONS = (
    asyncio.TimeoutError,
    ConnectionError,
    OSError,
)


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 4,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Args:
            max_attempts: Maximum number of attempts (including initial)
            base_delay: Initial delay in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


DEFAULT_RETRY_CONFIG = RetryConfig()


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for a given attempt number."""
    # Exponential backoff: base_delay * (exponential_base ^ attempt)
    delay = config.base_delay * (config.exponential_base ** attempt)
    delay = min(delay, config.max_delay)

    if config.jitter:
        # Add random jitter (0.5 to 1.5 of calculated delay)
        delay = delay * (0.5 + random.random())

    return delay


def is_retryable_error(error: Exception) -> bool:
    """Check if an error should trigger a retry."""
    # Check for retryable exception types
    if isinstance(error, RETRYABLE_EXCEPTIONS):
        return True

    # Check for HTTP errors with retryable status codes
    # Handle httpx.HTTPStatusError
    if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
        return error.response.status_code in RETRYABLE_STATUS_CODES

    # Handle anthropic/openai specific errors
    if hasattr(error, 'status_code'):
        return error.status_code in RETRYABLE_STATUS_CODES

    # Check error message for rate limit indicators
    error_str = str(error).lower()
    if 'rate limit' in error_str or 'too many requests' in error_str:
        return True
    if 'overloaded' in error_str or 'capacity' in error_str:
        return True

    return False


def get_retry_after(error: Exception) -> float | None:
    """Extract retry-after header value if present."""
    if hasattr(error, 'response') and hasattr(error.response, 'headers'):
        retry_after = error.response.headers.get('retry-after')
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass
    return None


async def retry_with_backoff(
    func: Callable[..., T],
    *args,
    config: RetryConfig | None = None,
    **kwargs
) -> T:
    """
    Execute an async function with retry and exponential backoff.

    Args:
        func: Async function to execute
        *args: Positional arguments for func
        config: Retry configuration (uses default if not provided)
        **kwargs: Keyword arguments for func

    Returns:
        Result of the function call

    Raises:
        The last exception if all retries are exhausted
    """
    config = config or DEFAULT_RETRY_CONFIG
    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e

            # Check if we should retry
            if not is_retryable_error(e):
                logger.warning(f"Non-retryable error: {type(e).__name__}: {e}")
                raise

            # Check if we have more attempts
            if attempt + 1 >= config.max_attempts:
                logger.error(f"All {config.max_attempts} attempts failed: {type(e).__name__}: {e}")
                raise

            # Calculate delay
            delay = get_retry_after(e) or calculate_delay(attempt, config)

            logger.warning(
                f"Attempt {attempt + 1}/{config.max_attempts} failed: {type(e).__name__}: {e}. "
                f"Retrying in {delay:.2f}s..."
            )

            await asyncio.sleep(delay)

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Retry loop completed without result or exception")


def with_retry(config: RetryConfig | None = None):
    """
    Decorator to add retry logic to an async function.

    Usage:
        @with_retry(RetryConfig(max_attempts=3))
        async def my_api_call():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_with_backoff(func, *args, config=config, **kwargs)
        return wrapper
    return decorator
