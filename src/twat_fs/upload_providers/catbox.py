#!/usr/bin/env python3
# this_file: src/twat_fs/upload_providers/catbox.py

"""
Catbox.moe file upload provider.
Supports both anonymous and authenticated uploads, as well as URL-based uploads.
API documentation: https://catbox.moe/tools.php
"""

import os
from pathlib import Path
from typing import TypedDict
import aiohttp
from loguru import logger

from . import ProviderClient, UploadResult
from .core import (
    with_async_retry,
    with_retry,
    validate_file,
    async_to_sync,
    with_url_validation,
    RetryableError,
    NonRetryableError,
)

CATBOX_API_URL = "https://catbox.moe/user/api.php"


class CatboxCredentials(TypedDict, total=False):
    """Credentials for Catbox provider."""

    userhash: str | None


class CatboxProvider(ProviderClient):
    """Provider for catbox.moe file uploads."""

    def __init__(self, credentials: CatboxCredentials | None = None) -> None:
        """Initialize the Catbox provider with optional credentials."""
        self.credentials = credentials or {}
        self.userhash = self.credentials.get("userhash")

    @with_url_validation
    @with_async_retry(
        max_attempts=3,
        exceptions=(aiohttp.ClientError, RetryableError),
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
        Upload a file to catbox.moe.

        Args:
            file_path: Local path to the file
            remote_path: Ignored for Catbox
            unique: If True, ensures unique filename (not supported by Catbox)
            force: If True, overwrites existing file (not supported by Catbox)
            upload_path: Custom upload path (not supported by Catbox)

        Returns:
            UploadResult with the public URL

        Raises:
            FileNotFoundError: If the file doesn't exist
            RetryableError: For temporary failures that can be retried
            NonRetryableError: For permanent failures
        """
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        data = aiohttp.FormData()
        data.add_field("reqtype", "fileupload")

        # Add userhash if authenticated
        if self.userhash:
            data.add_field("userhash", self.userhash)

        # Add the file
        with open(file_path, "rb") as f:
            data.add_field(
                "fileToUpload",
                f,
                filename=file_path.name,
                content_type="application/octet-stream",
            )

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(CATBOX_API_URL, data=data) as response:
                    if response.status != 200:
                        msg = f"Upload failed with status {response.status}"
                        raise RetryableError(msg, "catbox")

                    url = await response.text()
                    if not url.startswith("http"):
                        msg = f"Invalid response from server: {url}"
                        raise NonRetryableError(msg, "catbox")

                    return UploadResult(
                        url=url,
                        metadata={
                            "provider": "catbox",
                            "userhash": self.userhash is not None,
                        },
                    )

            except aiohttp.ClientError as e:
                msg = f"Upload failed: {e}"
                raise RetryableError(msg, "catbox") from e

    @with_url_validation
    @with_async_retry(
        max_attempts=3,
        exceptions=(aiohttp.ClientError, RetryableError),
    )
    async def async_upload_url(
        self,
        url: str,
        *,
        unique: bool = False,
        force: bool = False,
    ) -> UploadResult:
        """
        Upload a file from a URL to catbox.moe.

        Args:
            url: The URL to upload from
            unique: If True, ensures unique filename (not supported by Catbox)
            force: If True, overwrites existing file (not supported by Catbox)

        Returns:
            UploadResult with the public URL

        Raises:
            RetryableError: For temporary failures that can be retried
            NonRetryableError: For permanent failures
        """
        data = aiohttp.FormData()
        data.add_field("reqtype", "urlupload")
        data.add_field("url", url)

        if self.userhash:
            data.add_field("userhash", self.userhash)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(CATBOX_API_URL, data=data) as response:
                    if response.status != 200:
                        msg = f"Upload failed with status {response.status}"
                        raise RetryableError(msg, "catbox")

                    url = await response.text()
                    if not url.startswith("http"):
                        msg = f"Invalid response from server: {url}"
                        raise NonRetryableError(msg, "catbox")

                    return UploadResult(
                        url=url,
                        metadata={
                            "provider": "catbox",
                            "userhash": self.userhash is not None,
                        },
                    )

            except aiohttp.ClientError as e:
                msg = f"Upload failed: {e}"
                raise RetryableError(msg, "catbox") from e

    @with_async_retry(
        max_attempts=3,
        exceptions=(aiohttp.ClientError, RetryableError),
    )
    async def async_delete_files(self, files: list[str]) -> bool:
        """
        Delete files from catbox.moe (requires authentication).

        Args:
            files: List of filenames to delete (e.g., ["eh871k.png", "d9pove.gif"])

        Returns:
            True if deletion was successful

        Raises:
            NonRetryableError: If not authenticated or deletion fails
            RetryableError: If connection issues occur
        """
        if not self.userhash:
            msg = "Authentication required for file deletion"
            raise NonRetryableError(msg, "catbox")

        data = aiohttp.FormData()
        data.add_field("reqtype", "deletefiles")
        data.add_field("userhash", self.userhash)
        data.add_field("files", " ".join(files))

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(CATBOX_API_URL, data=data) as response:
                    if response.status == 429:  # Rate limit
                        error_text = await response.text()
                        msg = f"Rate limited: {error_text}"
                        raise RetryableError(msg, "catbox")
                    elif response.status != 200:
                        error_text = await response.text()
                        msg = f"File deletion failed: {error_text}"
                        raise NonRetryableError(msg, "catbox")
                    return True
            except aiohttp.ClientError as e:
                msg = f"Connection error: {e!s}"
                raise RetryableError(msg, "catbox") from e

    @validate_file
    @async_to_sync
    async def upload_file(
        self,
        local_path: str | Path,
        remote_path: str | Path | None = None,
        *,
        unique: bool = False,
        force: bool = False,
        upload_path: str | None = None,
    ) -> str:
        """
        Synchronously upload a file to catbox.moe.

        Args:
            local_path: Path to the local file
            remote_path: Ignored for Catbox
            unique: If True, ensures unique filename (not supported by Catbox)
            force: If True, overwrites existing file (not supported by Catbox)
            upload_path: Custom upload path (not supported by Catbox)

        Returns:
            The public URL of the uploaded file

        Raises:
            FileNotFoundError: If the file doesn't exist
            RetryableError: For temporary failures that can be retried
            NonRetryableError: For permanent failures
        """
        result = await self.async_upload_file(
            Path(local_path),
            remote_path,
            unique=unique,
            force=force,
            upload_path=upload_path,
        )
        return result.url


@with_retry(max_attempts=3)
def get_credentials() -> CatboxCredentials | None:
    """
    Get Catbox credentials from environment variables.

    Returns:
        Dict with credentials if CATBOX_USERHASH is set, None otherwise
    """
    userhash = os.getenv("CATBOX_USERHASH")
    return {"userhash": userhash} if userhash else None


@with_retry(max_attempts=3)
def get_provider() -> ProviderClient | None:
    """
    Initialize and return the Catbox provider.

    Returns:
        Configured CatboxProvider instance, or None if initialization fails
    """
    try:
        return CatboxProvider(get_credentials())
    except Exception as e:
        logger.error(f"Failed to initialize Catbox provider: {e}")
        return None
