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

import os
from pathlib import Path
from typing import Any, Union

from loguru import logger  # type: ignore

from twat_fs.upload_providers import (
    PROVIDERS_PREFERENCE,
    get_provider_help,
    get_provider_module,
    Provider,
)

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
                f"Provider '{provider}' is not configured. "
                f"Please set up the required credentials:\n\n{help_info['setup']}"
            )

        # Try to get provider client
        if client := provider_module.get_provider():
            return (
                True,
                f"You can upload files to: {provider} (client: {type(client).__name__})",
            )

        # If we have credentials but client init failed, probably missing dependencies
        help_info = get_provider_help(provider)
        if not help_info:
            return (
                False,
                f"Provider '{provider}' has credentials but additional setup is needed.",
            )
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


def _try_provider(
    provider: str,
    local_path: Path,
    remote_path: str | Path | None = None,
    *,  # Force keyword arguments for boolean flags
    unique: bool = False,
    force: bool = False,
    upload_path: str | None = None,
) -> tuple[bool, str | None]:
    """
    Try to upload a file using a specific provider.

    Args:
        provider: Name of the provider to use
        local_path: Path to the file to upload
        remote_path: Optional remote path to use
        unique: Whether to ensure unique filenames
        force: Whether to overwrite existing files
        upload_path: Custom base upload path

    Returns:
        Tuple[bool, str | None]: (success, url)
        - If upload succeeds: (True, url)
        - If upload fails: (False, error message)
    """
    try:
        # Import provider module
        provider_module = get_provider_module(provider)
        if not provider_module:
            return False, f"Provider '{provider}' is not available"

        # Check credentials
        credentials = provider_module.get_credentials()
        if not credentials:
            return False, f"Provider '{provider}' is not configured"

        # Try to get provider client
        client = provider_module.get_provider()
        if not client:
            return False, f"Provider '{provider}' failed to initialize"

        # Try to upload
        try:
            url = client.upload_file(
                local_path,
                remote_path=remote_path,
                unique=unique,
                force=force,
                upload_path=upload_path,
            )
            return True, url

        except Exception as e:
            return False, f"Upload failed: {e!s}"

    except Exception as e:
        return False, f"Provider error: {e!s}"


def get_provider(provider: ProviderType = None) -> tuple[str | None, Any]:
    """
    Get a working provider client from the specified provider(s).

    Args:
        provider: Provider to use, or list of providers to try in order.
                 If None, uses default provider order.

    Returns:
        tuple[str | None, Any]: Tuple of (provider_name, provider_client)
        If no provider is available, returns (None, None)

    Raises:
        ValueError: If a specific provider is requested but fails to initialize
    """
    # If a specific provider is requested, only try that one
    if isinstance(provider, str):
        provider_module = get_provider_module(provider)
        if not provider_module:
            msg = f"Provider '{provider}' module not found"
            raise ValueError(msg)

        # Check credentials and get client
        if not provider_module.get_credentials():
            msg = f"Provider '{provider}' has no credentials configured"
            raise ValueError(msg)

        client = provider_module.get_provider()
        if not client:
            msg = f"Failed to initialize provider '{provider}'"
            raise ValueError(msg)

        logger.info(f"Using provider: {provider}")
        return provider, client

    # For a list of providers or default preference, try each in order
    providers_to_try = provider if isinstance(provider, list) else PROVIDERS_PREFERENCE

    for p in providers_to_try:
        try:
            provider_module = get_provider_module(p)
            if not provider_module:
                continue

            # Check credentials first
            if not provider_module.get_credentials():
                logger.debug(f"Provider {p} has no credentials configured")
                continue

            # Try to get provider client
            if client := provider_module.get_provider():
                logger.info(f"Using provider: {p}")
                return p, client

        except Exception as e:
            logger.warning(f"Failed to initialize provider {p}: {e}")
            continue

    return None, None


def upload_file(
    file_path: str | Path,
    provider: ProviderType = None,
    remote_path: str | Path | None = None,
    *,  # Force keyword arguments for boolean flags
    unique: bool = False,
    force: bool = False,
    upload_path: str | None = None,
) -> str:
    """
    Upload a file using the specified provider.

    Args:
        file_path: Path to the file to upload
        provider: Provider to use, or list of providers to try in order
        remote_path: Optional remote path to use
        unique: Whether to ensure unique filenames
        force: Whether to overwrite existing files
        upload_path: Custom base upload path

    Returns:
        str: URL to the uploaded file

    Raises:
        ValueError: If upload fails or path is not a file
        FileNotFoundError: If file does not exist
        PermissionError: If file cannot be read
    """
    local_path = Path(file_path)
    if not local_path.exists():
        msg = f"File {local_path} does not exist"
        raise FileNotFoundError(msg)

    if not local_path.is_file():
        msg = "Path is not a file"
        raise ValueError(msg)

    if not os.access(local_path, os.R_OK):
        msg = f"File {local_path} cannot be read"
        raise PermissionError(msg)

    # If a specific provider is requested, only try that one
    if isinstance(provider, str):
        success, result = _try_provider(
            provider,
            local_path,
            remote_path=remote_path,
            unique=unique,
            force=force,
            upload_path=upload_path,
        )
        if success and result:
            return result
        msg = result if result else "No provider available or all providers failed"
        raise ValueError(msg)

    # Try providers in order of preference
    providers = provider if isinstance(provider, list) else PROVIDERS_PREFERENCE
    for p in providers:
        success, result = _try_provider(
            p,
            local_path,
            remote_path=remote_path,
            unique=unique,
            force=force,
            upload_path=upload_path,
        )
        if success and result:
            return result

    msg = "No provider available or all providers failed"
    raise ValueError(msg)
