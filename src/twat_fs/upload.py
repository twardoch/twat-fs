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


def setup_provider(provider: str, verbose: bool = False) -> ProviderInfo:
    """
    Check a provider's setup status and return its information.

    Args:
        provider: Name of the provider to check
        verbose: Whether to include detailed setup instructions

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

        # Check if this is a simple provider (no setup required)
        if (
            help_info
            and "setup" in help_info
            and "no setup required" in help_info["setup"].lower()
        ):
            return ProviderInfo(
                ProviderStatus.READY,
                f"{provider} (SimpleProvider)"
                + (f" - {retention_note}" if retention_note else ""),
            )

        # Check credentials for providers that need them
        credentials = provider_module.get_credentials()
        if not credentials:
            if not help_info:
                return ProviderInfo(
                    ProviderStatus.NEEDS_CONFIG,
                    f"Provider '{provider}' needs configuration.",
                )
            return ProviderInfo(
                ProviderStatus.NEEDS_CONFIG,
                f"Provider '{provider}' needs configuration.",
                help_info["setup"] if verbose else "",
            )

        # Try to get provider client
        try:
            if client := provider_module.get_provider():
                return ProviderInfo(
                    ProviderStatus.READY,
                    f"{provider} ({type(client).__name__})"
                    + (f" - {retention_note}" if retention_note else ""),
                )
        except Exception as e:
            help_info = get_provider_help(provider)
            if not help_info:
                return ProviderInfo(
                    ProviderStatus.NEEDS_CONFIG,
                    f"Provider '{provider}' initialization failed: {e}",
                )
            details = ""
            if verbose:
                if (
                    provider.lower() == "dropbox"
                    or "expired_access_token" in str(e).lower()
                ):
                    details = (
                        f"Please set up the DROPBOX_ACCESS_TOKEN environment variable with a valid token.\n\n"
                        f"Setup instructions:\n{help_info['setup']}\n\n"
                        f"Additional setup needed:\n{help_info['deps']}"
                    )
                else:
                    details = (
                        f"Setup instructions:\n{help_info['setup']}\n\n"
                        f"Additional setup needed:\n{help_info['deps']}"
                    )
            return ProviderInfo(
                ProviderStatus.NEEDS_CONFIG,
                f"Provider '{provider}' initialization failed: {e}",
                details,
            )

        # If we get here, we have credentials but provider initialization failed
        help_info = get_provider_help(provider)
        if not help_info:
            return ProviderInfo(
                ProviderStatus.NEEDS_CONFIG,
                f"Provider '{provider}' has credentials but needs additional setup.",
            )
        details = ""
        if verbose:
            if provider.lower() == "dropbox":
                details = (
                    f"Please set up the DROPBOX_ACCESS_TOKEN environment variable with a valid token.\n\n"
                    f"Setup instructions:\n{help_info['setup']}\n\n"
                    f"Additional setup needed:\n{help_info['deps']}"
                )
            else:
                details = f"Additional setup needed:\n{help_info['deps']}"
        return ProviderInfo(
            ProviderStatus.NEEDS_CONFIG,
            f"Provider '{provider}' needs additional setup.",
            details,
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


def setup_providers(verbose: bool = False) -> None:
    """
    Check setup status for all available providers and display a summary.

    Args:
        verbose: Whether to show detailed setup instructions
    """
    console = Console()

    # Get status for all providers except 'simple'
    provider_infos = {
        provider: setup_provider(provider, verbose)
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
        remote_path: Optional remote path to use
        unique: If True, ensure unique filename
        force: If True, overwrite existing file
        upload_path: Optional custom upload path

    Returns:
        str: URL to the uploaded file

    Raises:
        ValueError: If provider is not available or upload fails
    """
    provider = _get_provider_module(provider_name)
    if not provider:
        msg = f"Provider {provider_name} is not available"
        raise ValueError(msg)

    client = provider.get_provider()
    if not client:
        msg = f"Provider {provider_name} is not properly configured"
        raise ValueError(msg)

    try:
        return client.upload_file(
            local_path=file_path,
            remote_path=remote_path,
            unique=unique,
            force=force,
            upload_path=upload_path,
        )
    except Exception as e:
        msg = f"An error occurred while uploading with {provider_name}: {e}"
        raise ValueError(msg) from e


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
