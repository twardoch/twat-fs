#!/usr/bin/env python
# /// script
# dependencies = [
#   "fal-client",
#   "loguru",
# ]
# ///
# this_file: src/twat_fs/upload_providers/fal.py

"""
FAL provider for file uploads.
This module provides functionality to upload files to FAL's storage service.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar

import fal_client  # type: ignore
from loguru import logger  # type: ignore

from twat_fs.upload_providers.protocols import Provider, ProviderClient, ProviderHelp

# Provider-specific help messages
PROVIDER_HELP: ProviderHelp = {
    "setup": """To use FAL storage:
1. Create a FAL account at https://fal.ai
2. Generate an API key from your account settings
3. Set the following environment variable:
   - FAL_KEY: Your FAL API key""",
    "deps": """Additional setup needed:
1. Install the FAL client: pip install fal-client
2. Ensure your API key has the necessary permissions""",
}


class FalProvider(Provider):
    """Provider for uploading files to FAL."""

    # Class variable for provider help
    PROVIDER_HELP: ClassVar[ProviderHelp] = PROVIDER_HELP

    def __init__(self, key: str) -> None:
        """Initialize the FAL provider with the given API key."""
        self.client = fal_client.SyncClient(key=key)

    @classmethod
    def get_credentials(cls) -> dict[str, str] | None:
        """
        Fetch FAL credentials from environment.

        Returns:
            dict[str, str] | None: Dictionary with FAL key if present, None otherwise
        """
        key = os.getenv("FAL_KEY")
        return {"key": key} if key else None

    @classmethod
    def get_provider(cls) -> ProviderClient | None:
        """
        Initialize and return the FAL provider if credentials are present.

        Returns:
            Optional[Provider]: FAL provider instance if credentials are present, None otherwise
        """
        creds = cls.get_credentials()
        if not creds:
            logger.debug("FAL_KEY not set in environment")
            return None

        try:
            # Create a provider instance with the key
            return cls(key=creds["key"])
        except Exception as err:
            logger.warning(f"Failed to initialize FAL provider: {err}")
            return None

    def upload_file(
        self,
        local_path: str | Path,
        remote_path: str | Path | None = None,
        *,
        unique: bool = False,
        force: bool = False,
        upload_path: str | None = None,
    ) -> str:
        """
        Upload a file using FAL.

        Args:
            local_path: Path to the file to upload
            remote_path: Optional remote path (ignored for FAL)
            unique: Whether to ensure unique filenames (ignored for FAL)
            force: Whether to overwrite existing files (ignored for FAL)
            upload_path: Base path for uploads (ignored for FAL)

        Returns:
            str: URL to the uploaded file

        Raises:
            ValueError: If upload fails
            FileNotFoundError: If the file doesn't exist
        """
        path = Path(local_path)
        if not path.exists():
            msg = f"File not found: {path}"
            raise FileNotFoundError(msg)
        if not path.is_file():
            msg = f"Not a file: {path}"
            raise ValueError(msg)

        try:
            # FAL client's upload_file only accepts a string path
            result = self.client.upload_file(str(path))
            if not result:
                msg = "FAL upload failed - no URL in response"
                raise ValueError(msg)
            return str(result)

        except TypeError as e:
            # Handle type errors from the FAL client
            msg = f"FAL upload failed - invalid argument: {e}"
            raise ValueError(msg) from e
        except Exception as e:
            msg = f"FAL upload failed: {e}"
            raise ValueError(msg) from e


# Module-level functions that delegate to the FalProvider class
def get_credentials() -> dict[str, str] | None:
    """
    Get FAL credentials from environment.
    Delegates to FalProvider.get_credentials().
    """
    return FalProvider.get_credentials()


def get_provider() -> ProviderClient | None:
    """
    Initialize and return the FAL provider if credentials are present.
    Delegates to FalProvider.get_provider().
    """
    return FalProvider.get_provider()


def upload_file(
    local_path: str | Path,
    remote_path: str | Path | None = None,
    *,
    unique: bool = False,
    force: bool = False,
    upload_path: str | None = None,
) -> str:
    """
    Upload a file using FAL.
    Delegates to FalProvider.upload_file().
    """
    provider = get_provider()
    if not provider:
        msg = "FAL provider not configured"
        raise ValueError(msg)
    return provider.upload_file(
        local_path,
        remote_path=remote_path,
        unique=unique,
        force=force,
        upload_path=upload_path,
    )
