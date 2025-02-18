#!/usr/bin/env python
# /// script
# dependencies = []
# ///
# this_file: src/twat_fs/upload_providers/__init__.py

"""
Upload provider registry and base classes.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, cast

from loguru import logger

from .core import RetryableError, NonRetryableError, UploadError
from .protocols import ProviderClient, Provider, ProviderHelp
from .types import ExpirationTime, UploadResult

if TYPE_CHECKING:
    from pathlib import Path

# List of available providers in order of preference
PROVIDERS_PREFERENCE = [
    "catbox",
    "litterbox",
    "dropbox",
    "s3",
    "fal",
    "bashupload",
    "termbin",
    "uguu",
    "www0x0",
    "filebin",
    "pixeldrain",
    "simple",
]

__all__ = [
    "PROVIDERS_PREFERENCE",
    "ExpirationTime",
    "NonRetryableError",
    "Provider",
    "ProviderClient",
    "ProviderHelp",
    "RetryableError",
    "UploadError",
    "UploadResult",
    "get_provider_help",
    "get_provider_module",
]


def get_provider_module(provider: str) -> Provider | None:
    """
    Get the provider module for a given provider name.

    Args:
        provider: Name of the provider to get

    Returns:
        Optional[Provider]: Provider module if found and properly configured
    """
    try:
        module = importlib.import_module(f".{provider}", __package__)
        if not hasattr(module, "get_provider") or not hasattr(
            module, "get_credentials"
        ):
            logger.debug(f"Module {provider} does not implement Provider protocol")
            return None
        return cast(Provider, module)
    except ImportError as e:
        logger.debug(f"Failed to import provider {provider}: {e}")
        return None


def get_provider_help(provider: str) -> ProviderHelp | None:
    """
    Get help information for a provider.

    Args:
        provider: Name of the provider to get help for

    Returns:
        Optional[ProviderHelp]: Help information if provider exists
    """
    module = get_provider_module(provider)
    if module is None:
        return None
    return getattr(module, "PROVIDER_HELP", None)
