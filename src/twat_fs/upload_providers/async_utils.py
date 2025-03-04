# this_file: src/twat_fs/upload_providers/async_utils.py

"""
Utility functions for handling async/sync conversions in upload providers.
Standardizes patterns for working with async code across providers.
"""

from __future__ import annotations

import asyncio
import functools
from typing import Any, Callable, TypeVar, ParamSpec, cast, Awaitable, overload
from collections.abc import Coroutine

from loguru import logger

# Type variables for generic functions
T = TypeVar("T")
P = ParamSpec("P")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    Run an async coroutine in a synchronous context.

    This is a standardized way to run async code from sync functions.

    Args:
        coro: Coroutine to run

    Returns:
        The result of the coroutine

    Raises:
        Any exception raised by the coroutine
    """
    try:
        return asyncio.run(coro)
    except RuntimeError as e:
        # Handle case where there's already an event loop running
        if "There is no current event loop in thread" in str(e):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        else:
            raise


@overload
def to_sync(func: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P, T]: ...


@overload
def to_sync(
    *, name: str | None = None
) -> Callable[[Callable[P, Coroutine[Any, Any, T]]], Callable[P, T]]: ...


def to_sync(
    func: Callable[P, Coroutine[Any, Any, T]] | None = None,
    *,
    name: str | None = None,
) -> Callable[P, T] | Callable[[Callable[P, Coroutine[Any, Any, T]]], Callable[P, T]]:
    """
    Decorator to convert an async function to a sync function.

    This decorator can be used with or without arguments:

    @to_sync
    async def my_func(): ...

    @to_sync(name="my_func")
    async def my_func(): ...

    Args:
        func: Async function to convert
        name: Optional name for the wrapper function

    Returns:
        Synchronous wrapper function
    """

    def decorator(async_func: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P, T]:
        @functools.wraps(async_func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return run_async(async_func(*args, **kwargs))

        # Set a custom name if provided
        if name:
            wrapper.__name__ = name

        return wrapper

    if func is None:
        return decorator

    return decorator(func)


@overload
def to_async(func: Callable[P, T]) -> Callable[P, Coroutine[Any, Any, T]]: ...


@overload
def to_async(
    *, name: str | None = None
) -> Callable[[Callable[P, T]], Callable[P, Coroutine[Any, Any, T]]]: ...


def to_async(
    func: Callable[P, T] | None = None,
    *,
    name: str | None = None,
) -> (
    Callable[P, Coroutine[Any, Any, T]]
    | Callable[[Callable[P, T]], Callable[P, Coroutine[Any, Any, T]]]
):
    """
    Decorator to convert a sync function to an async function.

    This decorator can be used with or without arguments:

    @to_async
    def my_func(): ...

    @to_async(name="my_func")
    def my_func(): ...

    Args:
        func: Sync function to convert
        name: Optional name for the wrapper function

    Returns:
        Async wrapper function
    """

    def decorator(sync_func: Callable[P, T]) -> Callable[P, Coroutine[Any, Any, T]]:
        @functools.wraps(sync_func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return sync_func(*args, **kwargs)

        # Set a custom name if provided
        if name:
            wrapper.__name__ = name

        return wrapper

    if func is None:
        return decorator

    return decorator(func)


async def gather_with_concurrency(
    limit: int,
    *tasks: Coroutine[Any, Any, T],
    return_exceptions: bool = False,
) -> list[T]:
    """
    Run coroutines with a concurrency limit.

    This is useful for limiting the number of concurrent requests to a provider.

    Args:
        limit: Maximum number of concurrent tasks
        *tasks: Coroutines to run
        return_exceptions: If True, exceptions will be returned instead of raised

    Returns:
        List of results from the coroutines
    """
    semaphore = asyncio.Semaphore(limit)

    async def with_semaphore(task: Coroutine[Any, Any, T]) -> T:
        async with semaphore:
            return await task

    return await asyncio.gather(
        *(with_semaphore(task) for task in tasks),
        return_exceptions=return_exceptions,
    )


class AsyncContextManager:
    """
    Base class for implementing async context managers.

    This simplifies the creation of classes that need to be used with
    async with statements.

    Example:
        class MyClient(AsyncContextManager):
            async def __aenter__(self):
                # Setup code
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                # Cleanup code
                pass
    """

    async def __aenter__(self) -> Any:
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the async context manager."""
        pass


def with_async_timeout(
    timeout: float,
) -> Callable[
    [Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T]]
]:
    """
    Decorator to add a timeout to an async function.

    Args:
        timeout: Timeout in seconds

    Returns:
        Decorated function with timeout
    """

    def decorator(
        func: Callable[P, Coroutine[Any, Any, T]],
    ) -> Callable[P, Coroutine[Any, Any, T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning(
                    f"Function {func.__name__} timed out after {timeout} seconds"
                )
                raise TimeoutError(
                    f"Operation timed out after {timeout} seconds"
                ) from None

        return wrapper

    return decorator
