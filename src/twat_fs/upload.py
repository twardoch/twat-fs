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

from pathlib import Path
from typing import Any, Union
from loguru import logger
import os

from twat_fs.upload_providers import (
    PROVIDERS_PREFERENCE,
    get_provider_module,
    get_provider_help,
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
    provider: str, local_path: Path, remote_path: str | Path | None = None
) -> tuple[bool, str | None]:
    """
    Attempt to upload using a specific provider.

    Args:
        provider: The provider name to try
        local_path: The local file path as a Path object
        remote_path: Optional remote file path

    Returns:
        A tuple of (success flag, URL if successful)
    """
    try:
        provider_module = get_provider_module(provider)
        if provider_module is None:
            logger.debug(f"Provider {provider} module not found")
            return False, None

        provider_instance = provider_module.get_provider()
        if provider_instance is None:
            logger.debug(f"Provider {provider} has no credentials configured")
            return False, None

        try:
            # Check if the provider's upload_file method accepts remote_path
            import inspect

            sig = inspect.signature(provider_instance.upload_file)
            if len(sig.parameters) > 1:
                url = provider_instance.upload_file(local_path, remote_path)
            else:
                url = provider_instance.upload_file(local_path)
            return True, url
        except Exception as e:
            logger.warning(f"Provider {provider} failed: {e}")
            return False, None

    except Exception as e:
        logger.warning(f"Provider {provider} failed: {e}")
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
    """
    providers_to_try = (
        [provider]
        if isinstance(provider, str)
        else provider
        if isinstance(provider, list)
        else PROVIDERS_PREFERENCE
    )

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
    local_path: str | Path,
    remote_path: str | Path | None = None,
    *,
    provider: ProviderType = None,
) -> str:
    """
    Upload a file using the specified provider(s) and return the public URL.

    Args:
        local_path: Path to the local file to upload
        remote_path: Optional remote path/name for the uploaded file
        provider: Provider to use, or list of providers to try in order.
                 If None, uses default provider order.

    Returns:
        str: Public URL of the uploaded file

    Raises:
        ValueError: If no working provider is found or if the file upload fails
    """
    # Validate the file path before processing
    local_path = Path(local_path)
    if not local_path.exists():
        msg = f"File not found: {local_path}"
        raise FileNotFoundError(msg)
    if not local_path.is_file():
        msg = "Path is not a file"
        raise ValueError(msg)
    if not os.access(local_path, os.R_OK):
        msg = f"No read permission for file: {local_path}"
        raise PermissionError(msg)

    providers_to_try = (
        [provider]
        if isinstance(provider, str)
        else provider
        if isinstance(provider, list)
        else PROVIDERS_PREFERENCE
    )

    for p in providers_to_try:
        success, url = _try_provider(p, local_path, remote_path)
        if success and url:
            return url

    msg = "No provider available or all providers failed"
    raise ValueError(msg)
