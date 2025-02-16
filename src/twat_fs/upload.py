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

from loguru import logger

from twat_fs.upload_providers import (
    PROVIDERS_PREFERENCE,
    get_provider_help,
    get_provider_module,
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


def _get_provider_module(provider: str):
    """
    Import a provider module dynamically.

    Args:
        provider: Name of the provider to import

    Returns:
        module: The imported provider module or None if import fails
    """
    return get_provider_module(provider)


def _try_provider(
    provider: str,
    local_path: Path,
    remote_path: str | Path | None = None,
    unique: bool = False,
    force: bool = False,
    upload_path: str | None = None,
) -> tuple[bool, str | None]:
    """
    Attempt to upload using a specific provider.

    Args:
        provider: The provider name to try
        local_path: The local file path as a Path object
        remote_path: Optional remote file path
        unique: Whether to ensure unique filenames
        force: Whether to overwrite existing files
        upload_path: Custom base upload path

    Returns:
        A tuple of (success flag, URL if successful)

    The function will return (False, None) if:
    - Provider module is not found
    - Provider credentials are not configured
    - Upload fails for any reason
    """
    logger.debug(f"Attempting to use provider: {provider}")
    try:
        provider_module = get_provider_module(provider)
        if provider_module is None:
            logger.debug(f"Provider {provider} module not found")
            return False, None

        try:
            logger.debug(f"Getting provider instance for {provider}")
            provider_instance = provider_module.get_provider()
            if provider_instance is None:
                logger.debug(f"Provider {provider} has no credentials configured")
                return False, None

            # Check if the provider's upload_file method accepts additional parameters
            import inspect

            sig = inspect.signature(provider_instance.upload_file)
            kwargs = {}

            if "remote_path" in sig.parameters:
                kwargs["remote_path"] = remote_path
            if "unique" in sig.parameters:
                kwargs["unique"] = unique
            if "force" in sig.parameters:
                kwargs["force"] = force
            if "upload_path" in sig.parameters and upload_path is not None:
                kwargs["upload_path"] = upload_path

            logger.debug(f"Uploading to {provider} with kwargs: {kwargs}")
            url = provider_instance.upload_file(local_path, **kwargs)
            logger.debug(f"Upload successful with {provider}, got URL: {url}")
            return True, url

        except ValueError as e:
            # Provider-specific errors (like auth failures) are raised as ValueError
            logger.warning(f"Provider {provider} error: {e}")
            raise  # Re-raise to be caught by the upload_file function
        except Exception as e:
            logger.warning(f"Provider {provider} upload failed: {e}")
            return False, None

    except Exception as e:
        logger.warning(f"Provider {provider} initialization failed: {e}")
        return False, None


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
        success, url = _try_provider(
            provider,
            local_path,
            remote_path=remote_path,
            unique=unique,
            force=force,
            upload_path=upload_path,
        )
        if success and url:
            return url
        msg = "No provider available or all providers failed"
        raise ValueError(msg)

    # For a list of providers or default preference, try each in order
    providers_to_try = provider if isinstance(provider, list) else PROVIDERS_PREFERENCE

    for p in providers_to_try:
        success, url = _try_provider(
            p,
            local_path,
            remote_path=remote_path,
            unique=unique,
            force=force,
            upload_path=upload_path,
        )
        if success and url:
            return url

    msg = "No provider available or all providers failed"
    raise ValueError(msg)
