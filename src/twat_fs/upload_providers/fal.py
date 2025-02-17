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
from typing import Any, BinaryIO, ClassVar

import fal_client  # type: ignore
from loguru import logger  # type: ignore

from .simple import Provider, ProviderHelp, UploadResult, SimpleProviderBase

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


class FalProvider(SimpleProviderBase):
    """Provider for uploading files to FAL."""

    # Class variable for provider help
    PROVIDER_HELP: ClassVar[ProviderHelp] = PROVIDER_HELP

    def __init__(self, key: str) -> None:
        """Initialize the FAL provider with the given API key."""
        super().__init__()
        self.client = fal_client.SyncClient(key=key)

    @classmethod
    def get_credentials(cls) -> Any | None:
        """Get FAL credentials from environment."""
        return os.getenv("FAL_KEY")

    @classmethod
    def get_provider(cls) -> Provider | None:
        """
        Initialize and return the FAL provider if credentials are present.

        Returns:
            Optional[Provider]: FAL provider instance if credentials are present, None otherwise
        """
        key = cls.get_credentials()
        if not key:
            logger.debug("FAL_KEY not set in environment")
            return None

        try:
            # Create a provider instance with the key
            return cls(key=key)

        except Exception as err:
            logger.warning(f"Failed to initialize FAL provider: {err}")
            return None

    def upload_file_impl(self, file: BinaryIO) -> UploadResult:
        """
        Upload a file using FAL.

        Args:
            file: Open file handle to upload

        Returns:
            UploadResult containing the URL and status

        Raises:
            ValueError: If upload fails
        """
        try:
            # FAL client's upload_file only accepts a string path
            result = self.client.upload_file(str(file.name))
            if not result:
                return UploadResult(
                    url="",
                    success=False,
                    error="FAL upload failed - no URL in response",
                )
            return UploadResult(url=str(result), success=True)

        except TypeError as e:
            # Handle type errors from the FAL client
            return UploadResult(
                url="",
                success=False,
                error=f"FAL upload failed - invalid argument: {e}",
            )
        except Exception as e:
            return UploadResult(
                url="",
                success=False,
                error=f"FAL upload failed: {e}",
            )
