#!/usr/bin/env python3
# this_file: src/twat_fs/upload_providers/litterbox.py

"""
Litterbox.catbox.moe file upload provider.
Supports temporary file uploads with configurable expiration times.
API documentation: https://litterbox.catbox.moe/tools.php
"""

import os
from pathlib import Path
from typing import Any
import aiohttp
import asyncio
from loguru import logger

from .protocols import ProviderClient
from .types import ExpirationTime, UploadResult

LITTERBOX_API_URL = "https://litterbox.catbox.moe/resources/internals/api.php"


class LitterboxProvider(ProviderClient):
    """Provider for litterbox.catbox.moe temporary file uploads."""

    def __init__(
        self, default_expiration: ExpirationTime = ExpirationTime.HOURS_12
    ) -> None:
        """
        Initialize the Litterbox provider.

        Args:
            default_expiration: Default expiration time for uploads

        Raises:
            ValueError: If the expiration time is invalid
        """
        if not isinstance(default_expiration, ExpirationTime):
            msg = f"Invalid expiration time: {default_expiration}"
            raise ValueError(msg)
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
        Upload a file to litterbox.catbox.moe.

        Args:
            file_path: Path to the file to upload
            remote_path: Ignored for this provider
            unique: Ignored for this provider
            force: Ignored for this provider
            upload_path: Ignored for this provider
            expiration: Optional expiration time, defaults to provider default

        Returns:
            UploadResult: Upload result with URL and metadata

        Raises:
            RuntimeError: If the upload fails
        """
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise RuntimeError(msg)

        expiration = expiration or self.default_expiration
        data = aiohttp.FormData()
        data.add_field("reqtype", "fileupload")
        data.add_field("time", expiration.value)

        with open(file_path, "rb") as f:
            data.add_field("fileToUpload", f, filename=file_path.name)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(LITTERBOX_API_URL, data=data) as response:
                    if response.status != 200:
                        msg = f"Upload failed with status {response.status}"
                        raise RuntimeError(msg)

                    url = await response.text()
                    if not url.startswith("http"):
                        msg = f"Invalid response from server: {url}"
                        raise RuntimeError(msg)

                    return UploadResult(
                        url=url,
                        metadata={
                            "expiration": expiration.value,
                            "provider": "litterbox",
                        },
                    )

            except aiohttp.ClientError as e:
                msg = f"Upload failed: {e}"
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
            local_path: Path to the file to upload
            remote_path: Ignored for this provider
            unique: Ignored for this provider
            force: Ignored for this provider
            upload_path: Ignored for this provider
            expiration: Optional expiration time, defaults to provider default

        Returns:
            str: URL to the uploaded file

        Raises:
            RuntimeError: If the upload fails
        """
        if isinstance(local_path, str):
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
    Get litterbox credentials from environment.
    Currently no credentials are needed for litterbox.

    Returns:
        None: Litterbox doesn't require credentials
    """
    return None


def get_provider() -> ProviderClient | None:
    """
    Initialize and return the litterbox provider.

    Returns:
        ProviderClient: Configured litterbox provider
    """
    default_expiration = os.getenv("LITTERBOX_DEFAULT_EXPIRATION", "24h")
    try:
        expiration = ExpirationTime(default_expiration)
    except ValueError:
        logger.warning(
            f"Invalid expiration time {default_expiration}, using 24h default"
        )
        expiration = ExpirationTime.HOURS_24

    return LitterboxProvider(default_expiration=expiration)
