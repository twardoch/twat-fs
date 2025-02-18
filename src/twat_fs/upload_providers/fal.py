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
from twat_fs.upload_providers.types import UploadResult
from twat_fs.upload_providers.core import (
    with_url_validation,
    with_async_retry,
    RetryableError,
    NonRetryableError,
    validate_file,
)

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
            # Ensure the key is a clean string by stripping whitespace
            return cls(key=str(creds["key"]).strip())
        except Exception as err:
            logger.warning(f"Failed to initialize FAL provider: {err}")
            return None

    @validate_file
    @with_url_validation
    @with_async_retry(
        max_attempts=3,
        exceptions=(RetryableError, Exception),
    )
    async def async_upload_file(
        self,
        file_path: Path,
        remote_path: str | Path | None = None,
        *,
        unique: bool = False,
        force: bool = False,
        upload_path: str | None = None,
    ) -> UploadResult:
        """
        Upload a file using FAL.

        Args:
            file_path: Path to the file to upload
            remote_path: Optional remote path (ignored for FAL)
            unique: Whether to ensure unique filenames (ignored for FAL)
            force: Whether to overwrite existing files (ignored for FAL)
            upload_path: Base path for uploads (ignored for FAL)

        Returns:
            UploadResult with the public URL

        Raises:
            FileNotFoundError: If the file doesn't exist
            RetryableError: For temporary failures that can be retried
            NonRetryableError: For permanent failures
        """
        # Verify FAL client is properly initialized
        if not hasattr(self.client, "upload_file"):
            msg = "FAL client not properly initialized"
            raise NonRetryableError(msg, "fal")

        # Check if FAL key is still valid
        try:
            # Just try to access a property that requires auth
            _ = self.client.key
            logger.debug("FAL: API credentials verified")
        except Exception as e:
            if "401" in str(e) or "unauthorized" in str(e).lower():
                msg = "FAL API key is invalid or expired. Please generate a new key."
                raise NonRetryableError(msg, "fal")
            msg = f"FAL API check failed: {e}"
            raise RetryableError(msg, "fal")

        try:
            # Ensure file path is a string
            file_path_str = str(file_path)
            try:
                result = self.client.upload_file(file_path_str)
            except Exception as e:
                if "TypeError" in str(e) or "str" in str(e):
                    # Try reading the file and uploading the content directly
                    with open(file_path_str, "rb") as f:
                        result = self.client.upload_file(f)

            if not result:
                msg = "FAL upload failed - no URL in response"
                raise RetryableError(msg, "fal")

            result_str = str(result).strip()
            if not result_str:
                msg = "FAL upload failed - empty URL in response"
                raise RetryableError(msg, "fal")

            return UploadResult(
                url=result_str,
                metadata={
                    "provider": "fal",
                },
            )

        except Exception as e:
            if "401" in str(e) or "unauthorized" in str(e).lower():
                msg = f"FAL upload failed - unauthorized: {e}"
                raise NonRetryableError(msg, "fal")
            msg = f"FAL upload failed: {e}"
            raise RetryableError(msg, "fal")

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
        import asyncio

        try:
            result = asyncio.run(
                self.async_upload_file(
                    Path(local_path),
                    remote_path,
                    unique=unique,
                    force=force,
                    upload_path=upload_path,
                )
            )
            return result.url
        except (RetryableError, NonRetryableError) as e:
            raise ValueError(str(e)) from e


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
