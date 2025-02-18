#!/usr/bin/env python3
# this_file: src/twat_fs/upload_providers/litterbox.py

"""
Litterbox.catbox.moe file upload provider.
Supports temporary file uploads with configurable expiration times.
API documentation: https://litterbox.catbox.moe/tools.php
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any
import aiohttp
import asyncio
from loguru import logger

from . import ProviderClient, UploadResult

LITTERBOX_API_URL = "https://litterbox.catbox.moe/resources/internals/api.php"


class ExpirationTime(str, Enum):
    """Valid expiration times for Litterbox uploads."""

    HOUR_1 = "1h"
    HOURS_12 = "12h"
    HOURS_24 = "24h"
    HOURS_72 = "72h"


class LitterboxProvider(ProviderClient):
    """Provider for litterbox.catbox.moe temporary file uploads."""

    def __init__(
        self, default_expiration: ExpirationTime = ExpirationTime.HOURS_24
    ) -> None:
        """
        Initialize the Litterbox provider.

        Args:
            default_expiration: Default expiration time for uploads
        """
        self.default_expiration = default_expiration

    async def async_upload_file(
        self,
        file_path: Path,
        remote_path: str | Path | None = None,
        *,
        unique: bool = False,
        force: bool = False,
        upload_path: str | None = None,
        expiration: ExpirationTime | None = None,
    ) -> UploadResult:
        """
        Upload a file to litterbox.catbox.moe with expiration.

        Args:
            file_path: Local path to the file
            remote_path: Ignored for Litterbox
            unique: If True, ensures unique filename (not supported by Litterbox)
            force: If True, overwrites existing file (not supported by Litterbox)
            upload_path: Custom upload path (not supported by Litterbox)
            expiration: Optional expiration time, defaults to instance default

        Returns:
            UploadResult with the public URL

        Raises:
            FileNotFoundError: If the file doesn't exist
            RuntimeError: If the upload fails
        """
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        expiration = expiration or self.default_expiration

        data = aiohttp.FormData()
        data.add_field("reqtype", "fileupload")
        data.add_field("time", expiration.value)

        # Add the file
        data.add_field(
            "fileToUpload",
            open(file_path, "rb"),
            filename=file_path.name,
            content_type="application/octet-stream",
        )

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(LITTERBOX_API_URL, data=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        msg = f"Upload failed: {error_text}"
                        raise RuntimeError(msg)

                    url = await response.text()
                    return UploadResult(
                        url=url.strip(), metadata={"expiration": expiration.value}
                    )
            except aiohttp.ClientError as e:
                msg = f"Upload failed: {e!s}"
                raise RuntimeError(msg) from e

    def upload_file(
        self,
        local_path: str | Path,
        remote_path: str | Path | None = None,
        *,
        unique: bool = False,
        force: bool = False,
        upload_path: str | None = None,
        expiration: ExpirationTime | None = None,
    ) -> str:
        """
        Synchronously upload a file to litterbox.catbox.moe.

        Args:
            local_path: Path to the local file
            remote_path: Ignored for Litterbox
            unique: If True, ensures unique filename (not supported by Litterbox)
            force: If True, overwrites existing file (not supported by Litterbox)
            upload_path: Custom upload path (not supported by Litterbox)
            expiration: Optional expiration time, defaults to instance default

        Returns:
            The public URL of the uploaded file
        """
        local_path = Path(local_path)
        result = asyncio.run(
            self.async_upload_file(
                local_path,
                remote_path,
                unique=unique,
                force=force,
                upload_path=upload_path,
                expiration=expiration,
            )
        )
        return result.url


def get_credentials() -> dict[str, Any] | None:
    """
    Get Litterbox credentials (none required).

    Returns:
        None as Litterbox doesn't require authentication
    """
    return None


def get_provider() -> ProviderClient | None:
    """
    Initialize and return the Litterbox provider.

    Returns:
        Configured LitterboxProvider instance, or None if initialization fails
    """
    try:
        # Get default expiration from environment or use 24h
        default_expiration = os.getenv("LITTERBOX_DEFAULT_EXPIRATION", "24h")
        try:
            expiration = ExpirationTime(default_expiration)
        except ValueError:
            logger.warning(f"Invalid expiration time '{default_expiration}', using 24h")
            expiration = ExpirationTime.HOURS_24

        return LitterboxProvider(default_expiration=expiration)
    except Exception as e:
        logger.error(f"Failed to initialize Litterbox provider: {e}")
        return None
