#!/usr/bin/env python
# /// script
# dependencies = [
#   "loguru",
#   "fire",
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

from loguru import logger

from twat_fs.upload_providers import (
    PROVIDERS_PREFERENCE,
    get_provider_help,
    get_provider_module,
    Provider,
    RetryableError,
    NonRetryableError,
)
from .upload_providers.core import with_retry, RetryStrategy

# Type for provider specification - can be a single provider name or a list of providers
ProviderType = Union[str, list[str], None]


def setup_provider(provider: str) -> tuple[bool, str]:
    """
    Check a provider's setup status and return instructions if needed.

    Args:
        provider: Name of the provider to check

    Returns:
        Tuple[bool, str]: (success, explanation)
        - If provider is fully working: (True, "You can upload files to: {provider}")
        - If credentials exist but setup needed: (False, detailed setup instructions)
        - If no credentials: (False, complete setup guide including credentials)
    """
    try:
        # Import provider module
        provider_module = get_provider_module(provider)
        if not provider_module:
            help_info = get_provider_help(provider)
            if not help_info:
                return False, f"Provider '{provider}' is not available."
            return (
                False,
                f"Provider '{provider}' is not available.\n\n{help_info['setup']}",
            )

        # Check credentials
        credentials = provider_module.get_credentials()
        if not credentials:
            help_info = get_provider_help(provider)
            if not help_info:
                return False, f"Provider '{provider}' is not configured."
            return False, (
                f"Provider '{provider}' is not configured. Please set up the required credentials:\n\n{help_info['setup']}"
            )

        # Try to get provider client
        try:
            if client := provider_module.get_provider():
                return (
                    True,
                    f"You can upload files to: {provider} (client: {type(client).__name__})",
                )
        except Exception as e:
            help_info = get_provider_help(provider)
            if not help_info:
                return False, f"Provider '{provider}' initialization failed: {e}"
            if (
                provider.lower() == "dropbox"
                or "expired_access_token" in str(e).lower()
            ):
                return False, (
                    f"Provider '{provider}' initialization failed: expired_access_token\n\n"
                    f"Please set up the DROPBOX_ACCESS_TOKEN environment variable with a valid token.\n\n"
                    f"Setup instructions:\n{help_info['setup']}\n\n"
                    f"Additional setup needed:\n{help_info['deps']}"
                )
            return False, (
                f"Provider '{provider}' initialization failed: {e}\n\n"
                f"Setup instructions:\n{help_info['setup']}"
            )

        # If we get here, we have credentials but provider initialization failed
        help_info = get_provider_help(provider)
        if not help_info:
            return (
                False,
                f"Provider '{provider}' has credentials but additional setup is needed.",
            )
        if provider.lower() == "dropbox":
            return False, (
                f"Provider '{provider}' initialization failed: expired_access_token\n\n"
                f"Please set up the DROPBOX_ACCESS_TOKEN environment variable with a valid token.\n\n"
                f"Setup instructions:\n{help_info['setup']}\n\n"
                f"Additional setup needed:\n{help_info['deps']}"
            )
        else:
            return False, (
                f"Provider '{provider}' has credentials but additional setup is needed:\n\n"
                f"{help_info['deps']}"
            )

    except Exception as e:
        logger.warning(f"Error checking provider {provider}: {e}")
        help_info = get_provider_help(provider)
        if not help_info:
            return False, f"Provider '{provider}' encountered an error: {e!s}"
        return False, (
            f"Provider '{provider}' encountered an error: {e!s}\n\n"
            f"Complete setup guide:\n{help_info['setup']}\n\n"
            f"{help_info['deps']}"
        )


def setup_providers() -> dict[str, tuple[bool, str]]:
    """
    Check setup status for all available providers.

    Returns:
        Dict[str, Tuple[bool, str]]: Dictionary mapping provider names to their setup status and explanation
    """
    results = {}
    for provider in PROVIDERS_PREFERENCE:
        success, explanation = setup_provider(provider)
        results[provider] = (success, explanation)

        # Log the result
        if success:
            logger.info(explanation)
        else:
            logger.warning(f"Provider {provider} needs setup:\n{explanation}")

    return results


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
    """Try uploading with a specific provider."""
    provider_module = get_provider_module(provider_name)
    if not provider_module:
        msg = f"Provider {provider_name} not available"
        raise NonRetryableError(msg, provider_name)

    provider = provider_module.get_provider()
    if not provider:
        msg = f"Failed to initialize {provider_name} provider"
        raise NonRetryableError(msg, provider_name)

    return provider.upload_file(
        file_path,
        remote_path,
        unique=unique,
        force=force,
        upload_path=upload_path,
    )


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
        msg = f"Path is not a file: {path}"
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
