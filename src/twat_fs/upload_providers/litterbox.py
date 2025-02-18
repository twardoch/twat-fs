#!/usr/bin/env python3
# this_file: src/twat_fs/upload_providers/litterbox.py

"""
Litterbox.catbox.moe file upload provider.
Supports temporary file uploads with configurable expiration times.
API documentation: https://litterbox.catbox.moe/tools.php
"""

import os
from pathlib import Path
from typing import Any, ClassVar
import aiohttp
from loguru import logger

from twat_fs.upload_providers.protocols import ProviderClient, Provider, ProviderHelp
from twat_fs.upload_providers.types import ExpirationTime, UploadResult
from twat_fs.upload_providers.core import (
    validate_file,
    async_to_sync,
    with_url_validation,
    RetryableError,
    NonRetryableError,
)

LITTERBOX_API_URL = "https://litterbox.catbox.moe/resources/internals/api.php"

# Provider-specific help messages
PROVIDER_HELP: ProviderHelp = {
    "setup": """No setup required. Note: Files are deleted after 24 hours by default.
Optional: Set LITTERBOX_DEFAULT_EXPIRATION environment variable to change expiration time (1h, 12h, 24h, 72h).""",
    "deps": """No additional dependencies required.""",
}


class LitterboxProvider(ProviderClient, Provider):
    """Provider for litterbox.catbox.moe temporary file uploads."""

    PROVIDER_HELP: ClassVar[ProviderHelp] = PROVIDER_HELP

    def __init__(
        self, default_expiration: ExpirationTime | str = ExpirationTime.HOURS_12
    ) -> None:
        """
        Initialize the Litterbox provider.

        Args:
            default_expiration: Default expiration time for uploads

        Raises:
            ValueError: If the expiration time is invalid
        """
        # If a string is provided, convert it to ExpirationTime
        if not isinstance(default_expiration, ExpirationTime):
            try:
                default_expiration = ExpirationTime(default_expiration)
            except Exception as e:
                msg = f"Invalid expiration time: {default_expiration}"
                raise ValueError(msg) from e
        self.default_expiration = default_expiration

    @classmethod
    def get_credentials(cls) -> dict[str, Any] | None:
        """
        Get litterbox credentials from environment.
        Currently no credentials are needed for litterbox.

        Returns:
            None: Litterbox doesn't require credentials
        """
        return None

    @classmethod
    def get_provider(cls) -> ProviderClient | None:
        """
        Initialize and return the litterbox provider.

        Returns:
            ProviderClient: Configured litterbox provider
        """
        default_expiration = str(
            os.getenv("LITTERBOX_DEFAULT_EXPIRATION", "24h")
        ).strip()
        try:
            expiration = ExpirationTime(str(default_expiration))
        except ValueError:
            logger.warning(
                f"Invalid expiration time {default_expiration}, using 24h default"
            )
            expiration = ExpirationTime.HOURS_24
        return cls(default_expiration=expiration)

    @with_url_validation
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
            FileNotFoundError: If the file doesn't exist
            RetryableError: For temporary failures that can be retried
            NonRetryableError: For permanent failures
        """
        file_path = Path(file_path) if isinstance(file_path, str) else file_path
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        expiration = expiration or self.default_expiration
        data = aiohttp.FormData()
        data.add_field("reqtype", "fileupload")
        data.add_field(
            "time",
            str(
                expiration.value
                if isinstance(expiration, ExpirationTime)
                else expiration
            ),
        )

        try:
            # Read file content first
            with open(str(file_path), "rb") as f:
                file_content = f.read()

            # Create FormData with file content
            data.add_field(
                "fileToUpload",
                file_content,
                filename=str(file_path.name),
                content_type="application/octet-stream",
            )

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(LITTERBOX_API_URL, data=data) as response:
                        if response.status == 503:
                            msg = "Service temporarily unavailable"
                            raise RetryableError(msg, "litterbox")
                        elif response.status == 404:
                            msg = "API endpoint not found - service may be down or API has changed"
                            raise RetryableError(msg, "litterbox")
                        elif response.status != 200:
                            error_text = await response.text()
                            msg = f"Upload failed with status {response.status}: {error_text}"
                            if response.status in (400, 401, 403):
                                raise NonRetryableError(msg, "litterbox")
                            raise RetryableError(msg, "litterbox")

                        url = await response.text()
                        if not url.startswith("http"):
                            msg = f"Invalid response from server: {url}"
                            raise NonRetryableError(msg, "litterbox")

                        return UploadResult(
                            url=url,
                            metadata={
                                "expiration": expiration.value,
                                "provider": "litterbox",
                            },
                        )

                except aiohttp.ClientError as e:
                    msg = f"Upload failed: {e}"
                    raise RetryableError(msg, "litterbox") from e

        except Exception as e:
            msg = f"Upload failed: {e}"
            raise RetryableError(msg, "litterbox") from e

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
        file_path = Path(local_path) if isinstance(local_path, str) else local_path

        result = await self.async_upload_file(
            file_path,
            remote_path,
            unique=unique,
            force=force,
            upload_path=upload_path,
            expiration=expiration,
        )
        return result.url


def get_credentials() -> dict[str, Any] | None:
    """Get provider credentials from environment."""
    return LitterboxProvider.get_credentials()


def get_provider() -> ProviderClient | None:
    """Initialize and return the provider client."""
    return LitterboxProvider.get_provider()


def upload_file(
    local_path: str | Path,
    remote_path: str | Path | None = None,
    *,
    expiration: ExpirationTime | None = None,
) -> str:
    """
    Upload a file and return its URL.

    Args:
        local_path: Path to the file to upload
        remote_path: Optional remote path (ignored for this provider)
        expiration: Optional expiration time, defaults to provider default

    Returns:
        str: URL to the uploaded file

    Raises:
        ValueError: If upload fails
    """
    provider = get_provider()
    if not provider:
        msg = "Failed to initialize provider"
        raise ValueError(msg)
    return provider.upload_file(local_path, remote_path, expiration=expiration)
