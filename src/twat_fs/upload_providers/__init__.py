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
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Protocol,
    TypedDict,
    runtime_checkable,
    ClassVar,
)

from loguru import logger

if TYPE_CHECKING:
    from pathlib import Path


@runtime_checkable
class ProviderClient(Protocol):
    """Protocol defining the interface for upload providers."""

    def upload_file(
        self,
        local_path: str | Path,
        remote_path: str | Path | None = None,
        *,
        unique: bool = False,
        force: bool = False,
        upload_path: str | None = None,
    ) -> str:
        """Upload a file and return its public URL."""
        ...


class UploadResult:
    """Result of an upload operation."""

    def __init__(self, url: str, metadata: dict[str, Any] | None = None) -> None:
        """Initialize upload result."""
        self.url = url
        self.metadata = metadata or {}


# Order of preference for providers when none specified
PROVIDERS_PREFERENCE = [
    "catbox",  # Anonymous uploads, permanent
    "litterbox",  # Anonymous uploads, temporary
    "dropbox",  # Authenticated, permanent
    "s3",  # Authenticated, permanent
    "fal",  # Authenticated, permanent
    "www0x0",  # Anonymous uploads, permanent
    "uguu",  # Anonymous uploads, temporary
    "bashupload",  # Anonymous uploads, permanent
    "termbin",  # Anonymous uploads, text-only
]

# Map of provider module names to their import paths
PROVIDER_MODULES = {
    "catbox": "twat_fs.upload_providers.catbox",
    "litterbox": "twat_fs.upload_providers.litterbox",
    "dropbox": "twat_fs.upload_providers.dropbox",
    "s3": "twat_fs.upload_providers.s3",
    "fal": "twat_fs.upload_providers.fal",
    "www0x0": "twat_fs.upload_providers.www0x0",
    "uguu": "twat_fs.upload_providers.uguu",
    "bashupload": "twat_fs.upload_providers.bashupload",
    "termbin": "twat_fs.upload_providers.termbin",
}

# Provider help messages
PROVIDER_HELP = {
    "catbox": """
Catbox.moe File Upload Provider

Configuration:
- Optional: Set CATBOX_USERHASH for authenticated uploads
- No configuration needed for anonymous uploads

Features:
- Anonymous uploads (default)
- Authenticated uploads with user hash
- URL-based uploads
- File deletion (authenticated only)
""",
    "litterbox": """
Litterbox.catbox.moe Temporary File Upload Provider

Configuration:
- Optional: Set LITTERBOX_DEFAULT_EXPIRATION to '1h', '12h', '24h', or '72h'
- Defaults to '24h' if not specified

Features:
- Anonymous uploads only
- Configurable expiration times
- Files automatically deleted after expiration
""",
    # ... existing help messages ...
}

# Create ProviderType from PROVIDERS_PREFERENCE to ensure they stay in sync
ProviderType = Literal[tuple(PROVIDERS_PREFERENCE)]  # type: ignore


class ProviderHelp(TypedDict):
    """Type for provider help messages."""

    setup: str
    deps: str


@runtime_checkable
class Provider(Protocol):
    """Protocol defining what a provider module must implement."""

    PROVIDER_HELP: ClassVar[ProviderHelp]

    @classmethod
    def get_credentials(cls) -> Any | None:
        """
        Get provider credentials from environment.

        Returns:
            Optional[Any]: Provider-specific credentials or None if not configured
        """
        ...

    @classmethod
    def get_provider(cls) -> ProviderClient | None:
        """
        Initialize and return the provider client.

        Returns:
            Optional[ProviderClient]: Provider client if successful, None otherwise
        """
        ...

    def upload_file(
        self, local_path: str | Path, remote_path: str | Path | None = None
    ) -> str:
        """
        Upload a file using this provider.

        Args:
            local_path: Path to the file to upload
            remote_path: Optional remote path to use

        Returns:
            str: URL to the uploaded file

        Raises:
            ValueError: If upload fails
        """
        ...


# Provider module cache
_provider_modules: dict[str, Provider] = {}


def get_provider_module(provider: str) -> Provider | None:
    """
    Get a provider module, loading it if necessary.
    Uses a cache to avoid repeated imports.

    Args:
        provider: Name of the provider to load

    Returns:
        The provider module or None if import fails

    Raises:
        KeyError: If the provider is not in PROVIDERS_PREFERENCE
    """
    logger.debug(f"Getting provider module: {provider}")
    if provider not in PROVIDERS_PREFERENCE:
        msg = f"Invalid provider: {provider}"
        logger.error(msg)
        raise KeyError(msg)

    if provider not in _provider_modules:
        try:
            logger.debug(f"Importing provider module: {provider}")
            module = importlib.import_module(f"twat_fs.upload_providers.{provider}")
            if isinstance(module, Provider):
                logger.debug(f"Successfully loaded provider module: {provider}")
                _provider_modules[provider] = module
            else:
                logger.warning(
                    f"Module {provider} does not implement the Provider protocol"
                )
                return None
        except ImportError as e:
            logger.debug(f"Failed to import provider {provider}: {e}")
            return None
    return _provider_modules[provider]


def get_provider_help(provider: str) -> ProviderHelp | None:
    """Get help messages for a specific provider."""
    module = get_provider_module(provider)
    if not module:
        return None
    return module.PROVIDER_HELP if hasattr(module, "PROVIDER_HELP") else None
