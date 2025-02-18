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
import time
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
            # Ensure the key is a clean string by stripping whitespace
            return cls(key=str(creds["key"]).strip())
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

        # Verify FAL client is properly initialized
        if not hasattr(self.client, "upload_file"):
            msg = "FAL client not properly initialized"
            raise ValueError(msg)

        # Check if FAL key is still valid
        try:
            self.client.rest_call("GET", "/auth/v1/accounts/me")
            logger.debug("FAL: API credentials verified")
        except Exception as e:
            if "401" in str(e) or "unauthorized" in str(e).lower():
                msg = "FAL API key is invalid or expired. Please generate a new key."
                raise ValueError(msg)
            msg = f"FAL API check failed: {e}"
            raise ValueError(msg)

        # Upload with retries
        max_retries = 3
        retry_delay = 2
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"FAL: Attempting upload of {path} (attempt {attempt + 1}/{max_retries})"
                )

                # Attempt the upload with additional error logging
                try:
                    result = self.client.upload_file(str(path))
                except Exception as inner_error:
                    logger.error(f"FAL: Exception during upload: {inner_error}")
                    last_error = f"Upload exception: {inner_error}"
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    break

                result_str = str(result).strip()
                logger.debug(f"FAL: upload result: {result_str}")
                if not result_str:
                    last_error = "FAL upload failed - no URL in response"
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    break

                # Add a delay before validation to allow for propagation
                logger.debug(f"FAL: Waiting for URL propagation: {result_str}")
                time.sleep(5.0)  # Increased propagation delay

                # Validate URL is accessible
                import requests

                logger.debug(f"FAL: Validating URL: {result_str}")
                response = requests.head(
                    str(result_str),
                    timeout=30,
                    allow_redirects=True,
                    headers={"User-Agent": "twat-fs/1.0"},
                )

                logger.debug(f"FAL: URL validation response: {response.status_code}")

                if 200 <= response.status_code < 300:
                    logger.info(
                        f"FAL: Successfully uploaded and validated: {result_str}"
                    )
                    return str(result_str)

                last_error = f"URL validation failed with status {response.status_code}"
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2

            except (requests.RequestException, TypeError) as e:
                last_error = f"Upload or validation failed: {e}"
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2

        if last_error:
            raise ValueError(last_error)
        msg = "Upload failed after retries"
        raise ValueError(msg)


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
