# this_file: src/twat_fs/upload_providers/__init__.py

"""
Upload provider registry and base classes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# from loguru import logger # F401 Unused import

from twat_fs.upload_providers.core import RetryableError, NonRetryableError, UploadError
from twat_fs.upload_providers.protocols import ProviderClient, Provider, ProviderHelp
from twat_fs.upload_providers.provider_types import ExpirationTime, UploadResult
from twat_fs.upload_providers.factory import ProviderFactory

if TYPE_CHECKING:
    pass
    # from pathlib import Path # F401 Unused import (Path is not used in this file in a TYPE_CHECKING block context)

# List of available providers in order of preference
PROVIDERS_PREFERENCE = [
    # Anonymous providers — verified working (sorted by reliability + retention)
    "catbox",  # Permanent, 200 MB, integrity verified
    "litterbox",  # 1-72h selectable, 1 GB, integrity verified
    "x0at",  # 3-100 days, 512 MiB, integrity verified
    "tmpfilelink",  # 7 days, 100 MB, integrity verified
    "tmpfilesorg",  # 60 min only, integrity verified
    "senditsh",  # 1 day, 3 GB, single-download, integrity verified
    # Anonymous providers — need fixes or have caveats
    "www0x0",  # Works with user-agent fix
    "uguu",  # 24h, blocks .zip files
    "pixeldrain",  # 90 days, 20 GB, needs PUT method fix
    "filebin",  # Unreliable
    # Authenticated providers (require setup)
    "fal",
    "s3",
    "dropbox",
]

__all__ = [
    "PROVIDERS_PREFERENCE",
    "ExpirationTime",
    "NonRetryableError",
    "Provider",
    "ProviderClient",
    "ProviderFactory",
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

    This function is maintained for backward compatibility.
    New code should use ProviderFactory.get_provider_module() instead.

    Args:
        provider: Name of the provider to get

    Returns:
        Optional[Provider]: Provider module if found and properly configured
    """
    return ProviderFactory.get_provider_module(provider)


def get_provider_help(provider: str) -> ProviderHelp | None:
    """
    Get help information for a provider.

    This function is maintained for backward compatibility.
    New code should use ProviderFactory.get_provider_help() instead.

    Args:
        provider: Name of the provider to get help for

    Returns:
        Optional[ProviderHelp]: Help information if provider exists
    """
    return ProviderFactory.get_provider_help(provider)
