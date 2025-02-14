#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "loguru",
# ]
# ///
# this_file: src/twat_fs/upload.py

"""
Main upload module that provides a unified interface for uploading files
using different providers.
"""

from pathlib import Path
from typing import Literal
from loguru import logger

ProviderType = Literal["fal", "dropbox"]
PROVIDERS_PREFERENCE = [
    "dropbox",
    "fal",
]


def _try_provider(provider: str, file_path: str | Path) -> tuple[bool, str | None]:
    """
    Try to use a specific provider for upload.

    Args:
        provider: Name of the provider to try
        file_path: Path to the file to upload

    Returns:
        tuple[bool, str | None]: (success, url if successful else None)
    """
    try:
        # Import provider module only when needed
        provider_module = __import__(
            f"twat_fs.upload_providers.{provider}",
            fromlist=["upload_file", "provider_auth"],
        )

        # Check if provider is authenticated
        if not provider_module.provider_auth():
            logger.debug(f"Provider {provider} is not authenticated")
            return False, None

        # Try upload
        url = provider_module.upload_file(file_path)
        return True, url

    except ImportError as e:
        logger.warning(f"Failed to import {provider} provider: {e}")
        return False, None
    except Exception as e:
        logger.warning(f"Upload failed with {provider} provider: {e}")
        return False, None


def upload_file(
    file_path: str | Path,
    provider: ProviderType | list[ProviderType] | None = PROVIDERS_PREFERENCE,
) -> str:
    """
    Upload a file using the specified provider(s).

    Args:
        file_path: Path to the file to upload (str or Path)
        provider: Name of the provider to use or list of providers to try in order.
                 Defaults to PROVIDERS_PREFERENCE.

    Returns:
        str: URL of the uploaded file

    Raises:
        ValueError: If no providers are available or all providers fail
        ImportError: If provider module cannot be imported
    """
    # Convert single provider to list for uniform handling
    if not provider:
        provider = PROVIDERS_PREFERENCE
    providers = (
        [p.strip() for p in provider.split(",")]
        if isinstance(provider, str)
        else provider
    )

    # Validate providers
    invalid_providers = [p for p in providers if p not in PROVIDERS_PREFERENCE]
    if invalid_providers:
        msg = f"Unsupported provider(s): {', '.join(invalid_providers)}"
        raise ValueError(msg)

    # Try each provider in order
    for p in providers:
        success, url = _try_provider(p, file_path)
        if success and url:
            logger.info(f"Successfully uploaded using {p} provider")
            return url

    # If we get here, all providers failed
    msg = (
        f"All providers failed. Please check authentication and try again. "
        f"Tried providers: {', '.join(providers)}"
    )
    raise ValueError(msg)
