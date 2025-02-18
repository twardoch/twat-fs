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
from typing import TypeVar, ParamSpec, cast, NamedTuple
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


class TimingMetrics(NamedTuple):
    """Timing metrics for upload operations."""

    start_time: float
    end_time: float
    total_duration: float
    read_duration: float
    upload_duration: float
    validation_duration: float
    provider: str

    @property
    def as_dict(self) -> dict[str, float | str]:
        """Convert timing metrics to a dictionary."""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration": self.total_duration,
            "read_duration": self.read_duration,
            "upload_duration": self.upload_duration,
            "validation_duration": self.validation_duration,
            "provider": self.provider,
        }


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


def with_timing(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    """
    Decorator to add timing metrics to upload operations.

    This decorator will track:
    - Total operation duration
    - File read duration
    - Upload duration
    - URL validation duration
    """

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        start_time = time.time()
        read_start = time.time()

        # Get file path from args or kwargs
        file_path = next(
            (arg for arg in args if isinstance(arg, str | Path)),
            kwargs.get("local_path") or kwargs.get("file_path"),
        )

        # Get provider name from instance or module
        provider_name = (
            getattr(args[0], "provider_name", None)
            if args
            else kwargs.get("provider", "unknown")
        )

        # Track file read time
        if file_path:
            path = Path(str(file_path))
            if path.exists():
                with open(path, "rb") as f:
                    _ = f.read()  # Read file to measure read time
        read_duration = time.time() - read_start

        # Track upload time
        upload_start = time.time()
        result = await func(*args, **kwargs)
        upload_duration = time.time() - upload_start

        # Track validation time if result has a URL
        validation_start = time.time()
        if isinstance(result, UploadResult):
            url = result.url
        elif isinstance(result, str):
            url = result
        else:
            url = None

        if url:
            try:
                await validate_url(url)
            except Exception:
                pass
        validation_duration = time.time() - validation_start

        end_time = time.time()
        total_duration = end_time - start_time

        # Create timing metrics
        metrics = TimingMetrics(
            start_time=start_time,
            end_time=end_time,
            total_duration=total_duration,
            read_duration=read_duration,
            upload_duration=upload_duration,
            validation_duration=validation_duration,
            provider=str(provider_name),
        )

        # Attach metrics to result if it's an UploadResult
        if isinstance(result, UploadResult):
            result.metadata["timing"] = metrics.as_dict

        # Log timing information
        logger.info(
            f"Upload timing for {provider_name}: "
            f"total={total_duration:.2f}s, "
            f"read={read_duration:.2f}s, "
            f"upload={upload_duration:.2f}s, "
            f"validation={validation_duration:.2f}s"
        )

        return result

    return cast(Callable[P, Awaitable[T]], wrapper)
