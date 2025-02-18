#!/usr/bin/env python
# /// script
# dependencies = [
#   "loguru",
#   "fire",
#   "rich",
# ]
# ///
# this_file: src/twat_fs/upload.py

"""
Main upload module that provides a unified interface for uploading files
using different providers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto
import hashlib
import requests
import time

from loguru import logger
from rich.console import Console
from rich.table import Table, Column

from twat_fs.upload_providers import (
    PROVIDERS_PREFERENCE,
    get_provider_help,
    get_provider_module,
    Provider,
    RetryableError,
    NonRetryableError,
    UploadResult,
)
from twat_fs.upload_providers.core import with_retry, RetryStrategy

# Type for provider specification - can be a single provider name or a list of providers
ProviderType = Union[str, list[str], None]


class ProviderStatus(Enum):
    """Status of a provider's setup."""

    READY = auto()
    NEEDS_CONFIG = auto()
    NOT_AVAILABLE = auto()


@dataclass
class ProviderInfo:
    """Information about a provider's setup status."""

    status: ProviderStatus
    message: str
    details: str = ""
    timing: dict[str, float] | None = None


def _test_provider_online(
    provider_name: str,
) -> tuple[bool, str, dict[str, float] | None]:
    """
    Test a provider by uploading and downloading a small file.

    Args:
        provider_name: Name of the provider to test

    Returns:
        Tuple[bool, str, dict[str, float] | None]: (success, message, timing_metrics)
    """
    from pathlib import Path

    test_file = Path(__file__).parent / "data" / "test.jpg"
    if not test_file.exists():
        return False, f"Test file not found: {test_file}", None

    try:
        # Calculate original file hash
        with open(test_file, "rb") as f:
            original_hash = hashlib.sha256(f.read()).hexdigest()

        # Get the provider module and client
        provider_module = get_provider_module(provider_name)
        if not provider_module:
            return False, f"Provider module {provider_name} not found", None

        client = provider_module.get_provider()
        if not client:
            return False, f"Provider {provider_name} not configured", None

        # Upload the file
        try:
            result = client.upload_file(test_file)
            if not result:
                return False, "Upload failed", None

            # Extract URL and timing metrics
            if isinstance(result, UploadResult):
                url = result.url
                timing_metrics = result.metadata.get("timing")
            else:
                url = result
                timing_metrics = None

            # Add a small delay to allow for propagation
            time.sleep(1.0)

            # Validate URL is accessible
            response = requests.head(
                url,
                timeout=30,
                allow_redirects=True,
                headers={"User-Agent": "twat-fs/1.0"},
            )
            if response.status_code not in (200, 201, 202, 203, 204):
                return (
                    False,
                    f"URL validation failed: status {response.status_code}",
                    timing_metrics,
                )

        except ValueError as e:
            if "401" in str(e) or "authentication" in str(e).lower():
                return False, f"Authentication required: {e}", None
            return False, f"Upload failed: {e}", None
        except requests.RequestException as e:
            return False, f"URL validation failed: {e}", None

        # Download and verify the file with retries
        max_retries = 3
        retry_delay = 2  # seconds
        last_error = None

        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    # Calculate downloaded content hash
                    downloaded_hash = hashlib.sha256(response.content).hexdigest()

                    # Compare hashes
                    if original_hash == downloaded_hash:
                        return True, "Online test passed successfully", timing_metrics
                    else:
                        last_error = f"Content verification failed: original {original_hash}, downloaded {downloaded_hash}"
                else:
                    last_error = f"Download failed with status {response.status_code}"

                # If we're not on the last attempt, wait before retrying
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
            except Exception as e:
                last_error = f"Download attempt {attempt + 1} failed: {e}"
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2

        return False, last_error or "Download failed after retries", timing_metrics

    except Exception as e:
        return False, f"Online test failed: {e}", None


def setup_provider(
    provider: str, verbose: bool = False, online: bool = False
) -> ProviderInfo:
    """
    Check a provider's setup status and return its information.

    Args:
        provider: Name of the provider to check
        verbose: Whether to include detailed setup instructions
        online: Whether to perform an online test

    Returns:
        ProviderInfo: Provider status information
    """
    try:
        # Skip the 'simple' provider as it's just a base class
        if provider.lower() == "simple":
            return ProviderInfo(
                ProviderStatus.NOT_AVAILABLE,
                f"Provider '{provider}' is not available.",
                "This is a base provider and should not be used directly.",
            )

        # Import provider module
        provider_module = get_provider_module(provider)
        if not provider_module:
            help_info = get_provider_help(provider)
            if not help_info:
                return ProviderInfo(
                    ProviderStatus.NOT_AVAILABLE,
                    f"Provider '{provider}' is not available.",
                )
            setup_info = help_info.get("setup", "")
            return ProviderInfo(
                ProviderStatus.NOT_AVAILABLE,
                f"Provider '{provider}' is not available.",
                setup_info if verbose else "",
            )

        # Get help info for notes about retention
        help_info = get_provider_help(provider)
        retention_note = ""
        if help_info:
            setup_info = help_info.get("setup", "").lower()
            if "no setup required" in setup_info:
                # Extract any retention information
                if "deleted after" in setup_info:
                    retention_note = setup_info[setup_info.find("note:") :].strip()
                elif "only works with" in setup_info:
                    retention_note = setup_info[setup_info.find("note:") :].strip()

        # Try to get provider client
        try:
            client = provider_module.get_provider()
            if not client:
                setup_info = help_info.get("setup", "") if help_info else ""
                return ProviderInfo(
                    ProviderStatus.NEEDS_CONFIG,
                    f"Provider '{provider}' needs configuration.",
                    setup_info if verbose else "",
                )

            provider_class = client.__class__
            # Check if it's a provider with both async_upload_file and upload_file
            has_async = hasattr(client, "async_upload_file") and not getattr(
                provider_class.async_upload_file,
                "__isabstractmethod__",
                False,
            )
            has_sync = hasattr(client, "upload_file") and not getattr(
                provider_class.upload_file,
                "__isabstractmethod__",
                False,
            )

            # A provider is ready if it has either:
            # 1. Both async_upload_file and upload_file methods
            # 2. Just the upload_file method
            if has_async and has_sync:
                provider_info = ProviderInfo(
                    ProviderStatus.READY,
                    f"{provider} ({type(client).__name__})"
                    + (f" - {retention_note}" if retention_note else ""),
                )
            elif has_sync:
                provider_info = ProviderInfo(
                    ProviderStatus.READY,
                    f"{provider} ({type(client).__name__})"
                    + (f" - {retention_note}" if retention_note else ""),
                )
            else:
                setup_info = help_info.get("setup", "") if help_info else ""
                provider_info = ProviderInfo(
                    ProviderStatus.NEEDS_CONFIG,
                    f"Provider '{provider}' needs configuration.",
                    setup_info if verbose else "",
                )

            if online and provider_info.status == ProviderStatus.READY:
                online_status, message, timing = _test_provider_online(provider)
                if not online_status:
                    provider_info = ProviderInfo(
                        ProviderStatus.NOT_AVAILABLE,
                        message,
                        provider_info.details if verbose else "",
                    )
                else:
                    provider_info.timing = timing
                    provider_info.message = (
                        f"{provider_info.message}\nOnline test passed successfully"
                    )
                    logger.debug(
                        f"Provider {provider} online test passed with timing: {timing}"
                    )

            return provider_info

        except Exception as e:
            logger.error(f"Error setting up provider {provider}: {e}")
            setup_info = help_info.get("setup", "") if help_info else ""
            return ProviderInfo(
                ProviderStatus.NEEDS_CONFIG,
                f"Provider '{provider}' setup failed: {e}",
                setup_info if verbose else "",
            )

    except Exception as e:
        logger.error(f"Unexpected error setting up provider {provider}: {e}")
        return ProviderInfo(
            ProviderStatus.NOT_AVAILABLE,
            f"Provider '{provider}' failed: {e}",
        )


def setup_providers(verbose: bool = False, online: bool = False) -> None:
    """
    Check all providers' setup status and display results.

    Args:
        verbose: Whether to include detailed setup instructions
        online: Whether to perform online tests
    """
    console = Console()

    # Create columns for the table
    columns = [
        Column("Provider", no_wrap=True, width=12),
        Column("Status", no_wrap=True, width=15),
        Column("Message", width=40),
    ]
    if online:
        columns.append(Column("Time (s)", width=10, no_wrap=True))

    # Create a table for results
    table = Table(
        *columns,
        title="Provider Status",
        title_style="bold magenta",
        show_lines=True,
        expand=True,
    )

    # Add providers in preference order
    for provider in PROVIDERS_PREFERENCE:
        info = setup_provider(provider, verbose, online=online)
        status_color = {
            ProviderStatus.READY: "green",
            ProviderStatus.NEEDS_CONFIG: "yellow",
            ProviderStatus.NOT_AVAILABLE: "red",
        }[info.status]

        timing_str = ""
        if online and info.timing:
            logger.debug(f"Timing info for {provider}: {info.timing}")
            timing_str = f"{info.timing['total_duration']:.2f}"
            logger.debug(f"Timing string for {provider}: {timing_str}")

        row = [
            provider,
            info.status.name,
            info.message + ("\n" + info.details if verbose and info.details else ""),
        ]
        if online:
            row.append(timing_str)
            logger.debug(f"Row for {provider}: {row}")

        table.add_row(*row, style=status_color)

    console.print(table)


def _get_provider_module(provider: str) -> Provider | None:
    """
    Import a provider module dynamically.

    Args:
        provider: Name of the provider to import

    Returns:
        Optional[Provider]: The imported provider module or None if import fails
    """
    return get_provider_module(provider)


def _try_upload_with_provider(
    provider_name: str,
    file_path: str | Path,
    *,
    remote_path: str | Path | None = None,
    unique: bool = False,
    force: bool = False,
    upload_path: str | None = None,
) -> UploadResult:
    """
    Try to upload a file using a specific provider.

    Args:
        provider_name: Name of the provider to use
        file_path: Path to the file to upload
        remote_path: Optional remote path
        unique: If True, ensures unique filename
        force: If True, overwrites existing file
        upload_path: Custom upload path

    Returns:
        UploadResult: Result containing URL and timing info

    Raises:
        ValueError: If provider is not available or upload fails
    """
    # Get provider module
    provider_module = get_provider_module(provider_name)
    if not provider_module:
        msg = f"Provider '{provider_name}' not available"
        raise ValueError(msg)

    # Get provider client
    client = provider_module.get_provider()
    if not client:
        msg = f"Provider '{provider_name}' not configured"
        raise ValueError(msg)

    # Track timing
    start_time = time.time()
    read_start = time.time()

    # Track file read time
    path = Path(str(file_path))
    if path.exists():
        with open(path, "rb") as f:
            _ = f.read()  # Read file to measure read time
    read_duration = time.time() - read_start

    # Track upload time
    upload_start = time.time()
    upload_result = client.upload_file(
        file_path,
        remote_path,
        unique=unique,
        force=force,
        upload_path=upload_path,
    )
    upload_duration = time.time() - upload_start

    # Track validation time
    validation_start = time.time()
    url = (
        upload_result.url if isinstance(upload_result, UploadResult) else upload_result
    )
    try:
        response = requests.head(
            url,
            timeout=30,
            allow_redirects=True,
            headers={"User-Agent": "twat-fs/1.0"},
        )
        if response.status_code not in (200, 201, 202, 203, 204):
            logger.warning(f"URL validation failed: status {response.status_code}")
    except Exception as e:
        logger.warning(f"URL validation failed: {e}")
    validation_duration = time.time() - validation_start

    end_time = time.time()
    total_duration = end_time - start_time

    # Create timing metrics
    timing = {
        "start_time": start_time,
        "end_time": end_time,
        "total_duration": total_duration,
        "read_duration": read_duration,
        "upload_duration": upload_duration,
        "validation_duration": validation_duration,
        "provider": provider_name,
    }

    # Convert string result to UploadResult if needed
    result = (
        UploadResult(url=upload_result, metadata={"provider": provider_name})
        if isinstance(upload_result, str)
        else upload_result
    )

    # Add timing information
    result.metadata["timing"] = timing

    # Log timing information
    logger.info(
        f"Upload timing for {provider_name}: "
        f"total={total_duration:.2f}s, "
        f"read={read_duration:.2f}s, "
        f"upload={upload_duration:.2f}s, "
        f"validation={validation_duration:.2f}s"
    )

    return result


def _try_next_provider(
    remaining_providers: Sequence[str],
    file_path: str | Path,
    *,
    remote_path: str | Path | None = None,
    unique: bool = False,
    force: bool = False,
    upload_path: str | None = None,
    fragile: bool = False,
    tried_providers: set[str] | None = None,
) -> str:
    """
    Try to upload a file using the next available provider.

    Args:
        remaining_providers: List of providers to try
        file_path: Path to the file to upload
        remote_path: Optional remote path
        unique: If True, ensures unique filename
        force: If True, overwrites existing file
        upload_path: Custom upload path
        fragile: If True, don't try other providers on failure
        tried_providers: Set of providers that have been tried

    Returns:
        str: URL of the uploaded file

    Raises:
        ValueError: If no providers are available or all uploads fail
    """
    if not remaining_providers:
        msg = "No providers available"
        raise ValueError(msg)

    # Keep track of tried providers to avoid loops
    tried = tried_providers or set()

    # Try each provider in sequence
    for provider in remaining_providers:
        if provider in tried:
            continue

        tried.add(provider)
        try:
            result = _try_upload_with_provider(
                provider,
                file_path,
                remote_path=remote_path,
                unique=unique,
                force=force,
                upload_path=upload_path,
            )
            return result.url

        except ValueError as e:
            if fragile:
                raise
            logger.warning(f"Provider {provider} failed: {e}")
            continue

    msg = f"All providers failed: {', '.join(tried)}"
    raise ValueError(msg)


@with_retry(
    max_attempts=2,  # One retry before falling back to next provider
    strategy=RetryStrategy.EXPONENTIAL,
    exceptions=(RetryableError,),  # Only retry on RetryableError
)
def upload_file(
    file_path: str | Path,
    provider: str | Sequence[str] | None = None,
    *,
    remote_path: str | Path | None = None,
    unique: bool = False,
    force: bool = False,
    upload_path: str | None = None,
    fragile: bool = False,
) -> str:
    """
    Upload a file using the specified provider(s) with fallback.

    Args:
        file_path: Path to the file to upload
        provider: Provider name or list of providers to try in order
        remote_path: Optional remote path to use
        unique: Whether to ensure unique filenames
        force: Whether to overwrite existing files
        upload_path: Base path for uploads
        fragile: If True, fail immediately without trying fallback providers

    Returns:
        str: URL to the uploaded file

    Raises:
        NonRetryableError: If all providers fail
        FileNotFoundError: If the file doesn't exist
        ValueError: If no valid providers are available
    """
    # Validate file exists
    path = Path(file_path)
    if not path.exists():
        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)
    if not path.is_file():
        msg = f"{path} is a directory"
        raise ValueError(msg)

    # Determine provider list
    providers = []
    if provider:
        if isinstance(provider, str):
            providers = [provider]
        else:
            providers = list(provider)
    else:
        providers = PROVIDERS_PREFERENCE

    # Validate providers
    if not providers:
        msg = "No providers specified"
        raise ValueError(msg)
    for p in providers:
        if p not in PROVIDERS_PREFERENCE:
            msg = f"Invalid provider: {p}"
            raise ValueError(msg)

    try:
        # Try first provider with retry
        return _try_upload_with_provider(
            providers[0],
            file_path,
            remote_path=remote_path,
            unique=unique,
            force=force,
            upload_path=upload_path,
        ).url
    except (RetryableError, NonRetryableError) as e:
        if fragile or len(providers) == 1:
            msg = f"Provider {providers[0]} failed: {e}"
            raise NonRetryableError(msg, providers[0])

        # Try remaining providers with circular fallback
        logger.info(f"Provider {providers[0]} failed, trying alternatives")
        return _try_next_provider(
            providers[1:],
            file_path,
            remote_path=remote_path,
            unique=unique,
            force=force,
            upload_path=upload_path,
            fragile=fragile,
            tried_providers={providers[0]},
        )
