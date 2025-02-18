#!/usr/bin/env python3
# this_file: src/twat_fs/upload_providers/core.py

"""
Core utilities and decorators for upload providers.
Provides common functionality for retrying uploads, handling errors, and managing async operations.
"""

import asyncio
import functools
import time
from enum import Enum
from pathlib import Path
from typing import TypeVar, ParamSpec, cast
from collections.abc import Callable, Awaitable
import aiohttp
from loguru import logger

from twat_fs.upload_providers.types import UploadResult

# Type variables for generic decorators
T = TypeVar("T")
P = ParamSpec("P")

# Constants for URL validation
URL_CHECK_TIMEOUT = 30.0  # seconds
MAX_REDIRECTS = 5
USER_AGENT = "twat-fs/1.0"


class RetryStrategy(str, Enum):
    """Retry strategies for upload attempts."""

    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"


def with_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for retrying upload operations with configurable backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        strategy: Retry strategy to use
        exceptions: Tuple of exceptions to catch and retry on

    Returns:
        Decorated function that implements retry logic
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None
            delay = initial_delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        raise

                    # Calculate next delay based on strategy
                    if strategy == RetryStrategy.EXPONENTIAL:
                        delay = min(initial_delay * (2**attempt), max_delay)
                    elif strategy == RetryStrategy.LINEAR:
                        delay = min(initial_delay * (attempt + 1), max_delay)
                    else:  # CONSTANT
                        delay = initial_delay

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)

            assert last_exception is not None  # for type checker
            raise last_exception

        return wrapper

    return decorator


def with_async_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator for retrying async upload operations with configurable backoff.
    Similar to with_retry but for async functions.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None
            delay = initial_delay

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        raise

                    if strategy == RetryStrategy.EXPONENTIAL:
                        delay = min(initial_delay * (2**attempt), max_delay)
                    elif strategy == RetryStrategy.LINEAR:
                        delay = min(initial_delay * (attempt + 1), max_delay)
                    else:  # CONSTANT
                        delay = initial_delay

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)

            assert last_exception is not None  # for type checker
            raise last_exception

        return cast(Callable[P, T], wrapper)

    return decorator


def validate_file(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator to validate file existence and permissions before upload.
    Common validation used by most providers.
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # Extract file path from args or kwargs
        file_path = next(
            (arg for arg in args if isinstance(arg, str | Path)),
            kwargs.get("local_path") or kwargs.get("file_path"),
        )

        if not file_path:
            msg = "No file path provided"
            raise ValueError(msg)

        path = Path(file_path)
        if not path.exists():
            msg = f"File not found: {path}"
            raise FileNotFoundError(msg)
        if not path.is_file():
            msg = f"Not a file: {path}"
            raise ValueError(msg)
        if not path.stat().st_size:
            msg = f"File is empty: {path}"
            raise ValueError(msg)
        if not path.stat().st_mode & 0o444:
            msg = f"File not readable: {path}"
            raise PermissionError(msg)

        return func(*args, **kwargs)

    return wrapper


def sync_to_async(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator to convert a synchronous upload function to async.
    Useful for providers that need to implement both sync and async interfaces.
    """

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return await asyncio.to_thread(func, *args, **kwargs)

    return cast(Callable[P, T], wrapper)


def async_to_sync(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator to convert an async upload function to sync.
    Useful for providers that implement async upload but need to provide sync interface.
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return asyncio.run(func(*args, **kwargs))

    return wrapper


class UploadError(Exception):
    """Base exception for upload errors."""

    def __init__(self, message: str, provider: str | None = None) -> None:
        super().__init__(message)
        self.provider = provider


class RetryableError(UploadError):
    """Exception indicating the upload should be retried."""

    pass


class NonRetryableError(UploadError):
    """Exception indicating the upload should not be retried."""

    pass


async def validate_url(url: str, timeout: float = URL_CHECK_TIMEOUT) -> bool:
    """
    Validate that a URL is accessible by making a GET request.

    Args:
        url: The URL to validate
        timeout: Timeout in seconds for the request

    Returns:
        bool: True if URL is valid and accessible

    Raises:
        RetryableError: If the validation should be retried (e.g., timeout)
        NonRetryableError: If the URL is invalid or inaccessible
    """
    async with aiohttp.ClientSession() as session:
        try:
            # Configure client session with appropriate headers and settings
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "*/*",
            }

            async with session.get(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
                max_redirects=MAX_REDIRECTS,
            ) as response:
                # Consider any 2xx or 3xx status as success
                if 200 <= response.status < 400:
                    return True
                if response.status in (401, 403, 404, 410):
                    msg = f"URL not accessible (status {response.status})"
                    raise NonRetryableError(msg)
                # Treat all other status codes as retryable
                msg = f"URL validation failed (status {response.status})"
                raise RetryableError(msg)

        except aiohttp.ClientError as e:
            if isinstance(e, aiohttp.ClientConnectorError):
                msg = f"Connection error: {e}"
                raise RetryableError(msg)
            if isinstance(e, aiohttp.ClientTimeout):
                msg = f"Timeout error: {e}"
                raise RetryableError(msg)
            msg = f"Client error: {e}"
            raise NonRetryableError(msg)
        except asyncio.TimeoutError as e:
            msg = f"Timeout error: {e}"
            raise RetryableError(msg)
        except Exception as e:
            msg = f"Unexpected error: {e}"
            raise NonRetryableError(msg)


@with_async_retry(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=10.0,
    strategy=RetryStrategy.EXPONENTIAL,
    exceptions=(RetryableError, aiohttp.ClientError),
)
async def ensure_url_accessible(url: str) -> str:
    """
    Ensure a URL is accessible with retries.
    Returns the URL if successful, raises an error if not.

    Args:
        url: The URL to validate

    Returns:
        str: The validated URL

    Raises:
        NonRetryableError: If the URL is invalid or inaccessible after retries
    """
    if await validate_url(url):
        return url
    msg = "URL validation failed after retries"
    raise NonRetryableError(msg)


def with_url_validation(
    func: Callable[P, Awaitable[str | UploadResult]],
) -> Callable[P, Awaitable[str | UploadResult]]:
    """
    Decorator to validate URLs after upload.
    Should be applied to async upload methods that return a URL or UploadResult.

    Args:
        func: Async function that returns a URL or UploadResult

    Returns:
        Decorated function that validates the URL after upload
    """

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> str | UploadResult:
        result = await func(*args, **kwargs)
        # Add a small delay before validation to allow for propagation
        await asyncio.sleep(1.0)

        # Extract URL from result
        url = result.url if isinstance(result, UploadResult) else result
        validated_url = await ensure_url_accessible(url)

        # Return same type as input
        if isinstance(result, UploadResult):
            result.url = validated_url
            return result
        return validated_url

    return wrapper
