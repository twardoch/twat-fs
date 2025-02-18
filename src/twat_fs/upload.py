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
from rich.table import Table

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


def _test_provider_online(provider_name: str) -> tuple[bool, str]:
    """
    Test a provider by uploading and downloading a small file.

    Args:
        provider_name: Name of the provider to test

    Returns:
        Tuple[bool, str]: (success, message)
    """
    from pathlib import Path

    test_file = Path(__file__).parent / "data" / "test.jpg"
    if not test_file.exists():
        return False, f"Test file not found: {test_file}"

    try:
        # Calculate original file hash
        with open(test_file, "rb") as f:
            original_hash = hashlib.sha256(f.read()).hexdigest()

        # Upload the file
        try:
            url = _try_upload_with_provider(provider_name, str(test_file))
            if not url:
                return False, "Upload failed"

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
                )

        except ValueError as e:
            if "401" in str(e) or "authentication" in str(e).lower():
                return False, f"Authentication required: {e}"
            return False, f"Upload failed: {e}"
        except requests.RequestException as e:
            return False, f"URL validation failed: {e}"

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
                        return True, "Online test passed successfully"
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

        return False, last_error or "Download failed after retries"

    except Exception as e:
        return False, f"Online test failed: {e}"


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
            return ProviderInfo(
                ProviderStatus.NOT_AVAILABLE,
                f"Provider '{provider}' is not available.",
                help_info["setup"] if verbose else "",
            )

        # Get help info for notes about retention
        help_info = get_provider_help(provider)
        retention_note = ""
        if help_info and "setup" in help_info:
            setup_info = help_info["setup"].lower()
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
                return ProviderInfo(
                    ProviderStatus.NEEDS_CONFIG,
                    f"Provider '{provider}' needs configuration.",
                    help_info["setup"] if verbose else "",
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

            # Check if it's a simple provider (has upload_file_impl)
            has_simple = hasattr(client, "upload_file_impl") and not getattr(
                provider_class.upload_file_impl,
                "__isabstractmethod__",
                False,
            )

            # A provider is ready if it has either:
            # 1. Both async_upload_file and upload_file methods
            # 2. Just the upload_file_impl method (simple provider)
            if has_async and has_sync:
                provider_info = ProviderInfo(
                    ProviderStatus.READY,
                    f"{provider} ({type(client).__name__})"
                    + (f" - {retention_note}" if retention_note else ""),
                )
            elif has_simple:
                provider_info = ProviderInfo(
                    ProviderStatus.READY,
                    f"{provider} ({type(client).__name__})"
                    + (f" - {retention_note}" if retention_note else ""),
                )
            elif has_async:
                # Provider has async_upload_file but no sync wrapper
                if online:
                    provider_info = ProviderInfo(
                        ProviderStatus.READY,
                        f"{provider} ({type(client).__name__})"
                        + (f" - {retention_note}" if retention_note else ""),
                    )
                else:
                    logger.debug(
                        f"Provider {provider} has async_upload_file but no sync wrapper"
                    )
                    error_msg = "Provider has async_upload_file but no sync wrapper"
                    return ProviderInfo(
                        ProviderStatus.NOT_AVAILABLE,
                        f"Provider '{provider}' is not available: {error_msg}",
                        help_info["setup"] if verbose else "",
                    )
            else:
                logger.debug(f"Provider {provider} missing required upload methods")
                error_msg = "Provider does not implement required upload methods"
                return ProviderInfo(
                    ProviderStatus.NOT_AVAILABLE,
                    f"Provider '{provider}' is not available: {error_msg}",
                    help_info["setup"] if verbose else "",
                )

            # If online testing is requested and the provider is ready, perform the test
            if online and provider_info.status == ProviderStatus.READY:
                success, message = _test_provider_online(provider)
                message = message.strip()
                if not success:
                    logger.error(f"{provider}: {message}")
                    if "authentication" in message.lower() or "401" in message:
                        return ProviderInfo(
                            ProviderStatus.NEEDS_CONFIG,
                            f"Provider '{provider}' needs configuration: {message}",
                            help_info["setup"] if verbose else "",
                        )
                    return ProviderInfo(
                        ProviderStatus.NOT_AVAILABLE,
                        f"Provider '{provider}' failed online test: {message}",
                        help_info["setup"] if verbose else "",
                    )
                provider_info.message += f" - {message}"

            return provider_info

        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "authentication" in error_msg.lower():
                return ProviderInfo(
                    ProviderStatus.NEEDS_CONFIG,
                    f"Provider '{provider}' needs configuration: {e}",
                    help_info["setup"] if verbose else "",
                )
            logger.debug(f"Provider {provider} failed to initialize: {e}")
            return ProviderInfo(
                ProviderStatus.NOT_AVAILABLE,
                f"Provider '{provider}' is not available: {e}",
                help_info["setup"] if verbose else "",
            )

    except Exception as e:
        logger.warning(f"Error checking provider {provider}: {e}")
        help_info = get_provider_help(provider)
        if not help_info:
            return ProviderInfo(
                ProviderStatus.NOT_AVAILABLE,
                f"Provider '{provider}' encountered an error: {e!s}",
            )
        return ProviderInfo(
            ProviderStatus.NOT_AVAILABLE,
            f"Provider '{provider}' encountered an error: {e!s}",
            f"Complete setup guide:\n{help_info['setup']}\n\n{help_info['deps']}"
            if verbose
            else "",
        )


def setup_providers(verbose: bool = False, online: bool = False) -> None:
    """
    Check setup status for all available providers and display a summary.

    Args:
        verbose: Whether to show detailed setup instructions
        online: Whether to perform online tests for ready providers
    """
    console = Console()

    # Get status for all providers except 'simple'
    provider_infos = {
        provider: setup_provider(provider, verbose, online)
        for provider in PROVIDERS_PREFERENCE
        if provider.lower() != "simple"
    }

    # Create status groups
    ready = [
        (name, info)
        for name, info in provider_infos.items()
        if info.status == ProviderStatus.READY
    ]
    needs_config = [
        (name, info)
        for name, info in provider_infos.items()
        if info.status == ProviderStatus.NEEDS_CONFIG
    ]
    not_available = [
        (name, info)
        for name, info in provider_infos.items()
        if info.status == ProviderStatus.NOT_AVAILABLE
    ]

    # Create and display the table
    table = Table(title="Provider Status")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Message", style="white", no_wrap=False)

    # Add ready providers
    for name, info in ready:
        table.add_row(name, "[green]Ready[/green]", info.message)
        if verbose and info.details:
            table.add_row("", "", info.details)

    # Add providers needing configuration
    for name, info in needs_config:
        table.add_row(name, "[yellow]Needs Setup[/yellow]", info.message)
        if verbose and info.details:
            table.add_row("", "", info.details)

    # Add unavailable providers
    for name, info in not_available:
        table.add_row(name, "[red]Not Available[/red]", info.message)
        if verbose and info.details:
            table.add_row("", "", info.details)

    console.print(table)

    # Print summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"✓ [green]{len(ready)}[/green] providers ready")
    if needs_config:
        console.print(f"⚠ [yellow]{len(needs_config)}[/yellow] providers need setup")
    if not_available:
        console.print(f"✗ [red]{len(not_available)}[/red] providers not available")

    if not verbose and (needs_config or not_available):
        console.print("\n[dim]Run with --verbose for detailed setup instructions[/dim]")


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
) -> str:
    """
    Try to upload a file using a specific provider.

    Args:
        provider_name: Name of the provider to use
        file_path: Path to the file to upload
        remote_path: Optional remote path/filename
        unique: Whether to ensure unique filenames
        force: Whether to force upload even if file exists
        upload_path: Optional base path for uploads

    Returns:
        str: URL of the uploaded file

    Raises:
        ValueError: If provider is not available or upload fails
    """
    provider = get_provider_module(provider_name)
    if not provider:
        msg = f"Provider '{provider_name}' not available"
        raise ValueError(msg)

    try:
        # Get provider client
        client = provider.get_provider()
        if not client:
            msg = f"Provider '{provider_name}' not configured"
            raise ValueError(msg)

        # Convert file_path to Path object
        path = Path(file_path) if isinstance(file_path, str) else file_path

        # Try async upload first if available
        if hasattr(client, "async_upload_file"):
            import asyncio

            result = asyncio.run(
                client.async_upload_file(
                    path,
                    remote_path=remote_path,
                    unique=unique,
                    force=force,
                    upload_path=upload_path,
                )
            )
            if isinstance(result, UploadResult):
                return result.url
            return result

        # Fall back to sync upload
        if hasattr(client, "upload_file"):
            url = client.upload_file(
                path,
                remote_path=remote_path,
                unique=unique,
                force=force,
                upload_path=upload_path,
            )
            return url

        msg = f"Provider '{provider_name}' does not implement upload methods"
        raise ValueError(msg)

    except Exception as e:
        if "401" in str(e) or "authentication" in str(e).lower():
            msg = f"Upload failed with status 401: {e}"
            raise ValueError(msg)
        msg = f"Failed to upload with {provider_name}: {e}"
        raise ValueError(msg)


def _try_next_provider(
    remaining_providers: Sequence[str],
    file_path: str | Path,
    *,
    remote_path: str | Path | None = None,
    unique: bool = False,
    force: bool = False,
    upload_path: str | None = None,
) -> str:
    """Try uploading with the next provider in the list."""
    if not remaining_providers:
        msg = "No more providers available"
        raise NonRetryableError(msg, None)

    provider = remaining_providers[0]
    next_providers = remaining_providers[1:]

    try:
        return _try_upload_with_provider(
            provider,
            file_path,
            remote_path=remote_path,
            unique=unique,
            force=force,
            upload_path=upload_path,
        )
    except (RetryableError, NonRetryableError) as e:
        logger.warning(f"Provider {provider} failed: {e}")
        if not next_providers:
            msg = "All providers failed"
            raise NonRetryableError(msg, None) from e
        return _try_next_provider(
            next_providers,
            file_path,
            remote_path=remote_path,
            unique=unique,
            force=force,
            upload_path=upload_path,
        )


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
        )
    except (RetryableError, NonRetryableError) as e:
        if len(providers) == 1:
            msg = f"Provider {providers[0]} failed: {e}"
            raise NonRetryableError(msg, providers[0])

        # Try remaining providers
        logger.info(f"Provider {providers[0]} failed, trying alternatives")
        return _try_next_provider(
            providers[1:],
            file_path,
            remote_path=remote_path,
            unique=unique,
            force=force,
            upload_path=upload_path,
        )
