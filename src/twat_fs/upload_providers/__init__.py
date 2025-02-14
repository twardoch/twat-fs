#!/usr/bin/env python
# /// script
# dependencies = []
# ///
# this_file: src/twat_fs/upload_providers/__init__.py

"""
Provider registry and common interfaces for upload providers.
This module defines the provider registry and common interfaces that all providers must implement.
"""

from typing import Any, TypedDict, Literal, Protocol, runtime_checkable
from pathlib import Path
import importlib
from loguru import logger

# Define provider preference order - this drives everything else
PROVIDERS_PREFERENCE = ["fal", "dropbox", "s3"]

# Create ProviderType from PROVIDERS_PREFERENCE to ensure they stay in sync
ProviderType = Literal[tuple(PROVIDERS_PREFERENCE)]  # type: ignore


class ProviderHelp(TypedDict):
    """Type for provider help messages."""

    setup: str
    deps: str


@runtime_checkable
class ProviderClient(Protocol):
    """Protocol defining what a provider client must implement."""

    def upload_file(
        self, local_path: str | Path, remote_path: str | Path | None = None
    ) -> str:
        """
        Upload a file to the provider's storage.

        Args:
            local_path: Path to the file to upload
            remote_path: Optional remote path to use

        Returns:
            str: URL to the uploaded file

        Raises:
            ValueError: If upload fails
        """
        ...


@runtime_checkable
class Provider(Protocol):
    """Protocol defining what a provider module must implement."""

    PROVIDER_HELP: ProviderHelp

    def get_credentials() -> Any | None:
        """
        Get provider credentials from environment.

        Returns:
            Optional[Any]: Provider-specific credentials or None if not configured
        """
        ...

    def get_provider() -> ProviderClient | None:
        """
        Initialize and return the provider client.

        Returns:
            Optional[ProviderClient]: Provider client if successful, None otherwise
        """
        ...

    def upload_file(self: str | Path, remote_path: str | Path | None = None) -> str:
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
    if provider not in PROVIDERS_PREFERENCE:
        msg = f"Invalid provider: {provider}"
        raise KeyError(msg)

    if provider not in _provider_modules:
        try:
            module = importlib.import_module(f"twat_fs.upload_providers.{provider}")
            if isinstance(module, Provider):
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
