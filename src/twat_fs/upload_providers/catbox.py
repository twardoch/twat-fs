# this_file: src/twat_fs/upload_providers/catbox.py

"""
Catbox.moe file upload provider.
Supports both anonymous and authenticated uploads, as well as URL-based uploads.
API documentation: https://catbox.moe/tools.php
"""

from __future__ import annotations

from typing import Any

import os
from pathlib import Path
from typing import (
    TypedDict,
    ClassVar,
    TypeVar,
    ParamSpec,
    cast,
)
import aiohttp
import requests
import time

from twat_fs.upload_providers.protocols import ProviderClient, Provider, ProviderHelp
from twat_fs.upload_providers.types import UploadResult
from twat_fs.upload_providers.core import (
    convert_to_upload_result,
    with_async_retry,
    async_to_sync,
    with_url_validation,
    with_timing,
    RetryableError,
    NonRetryableError,
)

# Type variables for generic functions
T = TypeVar("T", covariant=True)
P = ParamSpec("P")

CATBOX_API_URL = "https://catbox.moe/user/api.php"

# Provider-specific help messages
PROVIDER_HELP: ProviderHelp = {
    "setup": """No setup required. Note: Files are stored permanently.
Optional: Set CATBOX_USERHASH environment variable for authenticated uploads.""",
    "deps": """No additional dependencies required.""",
}


class CatboxCredentials(TypedDict, total=False):
    """Credentials for Catbox provider."""

    userhash: str | None


class CatboxProvider(ProviderClient, Provider):
    """Provider for catbox.moe file uploads."""

    PROVIDER_HELP: ClassVar[ProviderHelp] = PROVIDER_HELP
    provider_name = "catbox"

    def __init__(self, credentials: CatboxCredentials | None = None) -> None:
        """Initialize the Catbox provider with optional credentials."""
        self.credentials = credentials or {}
        self.userhash = self.credentials.get("userhash")

    @classmethod
    def get_credentials(cls) -> CatboxCredentials | None:
        """Get provider credentials from environment, ensuring userhash is a string."""
        userhash = os.getenv("CATBOX_USERHASH")
        if not userhash:
            return None
        return {"userhash": str(userhash)}

    @classmethod
    def get_provider(cls) -> ProviderClient | None:
        """Initialize and return the provider client."""
        return cls(cls.get_credentials())

    @with_url_validation
    @with_timing
    async def async_upload_file(
        self,
        file_path: str | Path,
        remote_path: str | Path | None = None,
        *,
        unique: bool = False,
        force: bool = False,
        upload_path: str | None = None,
        **kwargs: Any,
    ) -> UploadResult:
        """
        Upload a file to catbox.moe.

        Args:
            file_path: Path to the file to upload
            remote_path: Ignored for this provider
            unique: Ignored for this provider
            force: Ignored for this provider
            upload_path: Ignored for this provider
            **kwargs: Additional provider-specific arguments

        Returns:
            UploadResult: Upload result with URL and metadata

        Raises:
            FileNotFoundError: If the file doesn't exist
            RetryableError: For temporary failures that can be retried
            NonRetryableError: For permanent failures
        """
        file_path = Path(str(file_path))
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        data = aiohttp.FormData()
        data.add_field("reqtype", "fileupload")
        if self.userhash:
            data.add_field("userhash", self.userhash)

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
                    async with session.post(CATBOX_API_URL, data=data) as response:
                        if response.status == 503:
                            msg = "Service temporarily unavailable"
                            raise RetryableError(msg, "catbox")
                        elif response.status == 404:
                            msg = "API endpoint not found - service may be down or API has changed"
                            raise RetryableError(msg, "catbox")
                        elif response.status != 200:
                            error_text = await response.text()
                            msg = f"Upload failed with status {response.status}: {error_text}"
                            if response.status in (400, 401, 403):
                                raise NonRetryableError(msg, "catbox")
                            raise RetryableError(msg, "catbox")

                        url = await response.text()
                        if not url.startswith("http"):
                            msg = f"Invalid response from server: {url}"
                            raise NonRetryableError(msg, "catbox")

                        return convert_to_upload_result(
                            url,
                            metadata={
                                "provider": self.provider_name,
                                "authenticated": bool(self.userhash),
                            },
                        )

                except aiohttp.ClientError as e:
                    msg = f"Upload failed: {e}"
                    raise RetryableError(msg, "catbox") from e

        except Exception as e:
            msg = f"Upload failed: {e}"
            raise RetryableError(msg, "catbox") from e

    @with_url_validation
    @with_async_retry(
        max_attempts=3,
        exceptions=(aiohttp.ClientError, RetryableError),
    )
    @with_timing
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
        data.add_field("url", str(url))

        if self.userhash:
            data.add_field("userhash", str(self.userhash))

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

                    return convert_to_upload_result(
                        url,
                        metadata={
                            "provider": "catbox",
                            "authenticated": bool(self.userhash),
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
        data.add_field("userhash", str(self.userhash))
        data.add_field("files", ",".join(files))

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(CATBOX_API_URL, data=data) as response:
                    if response.status != 200:
                        msg = f"Deletion failed with status {response.status}"
                        raise RetryableError(msg, "catbox")

                    result = await response.text()
                    return result == "success"

            except aiohttp.ClientError as e:
                msg = f"Deletion failed: {e}"
                raise RetryableError(msg, "catbox") from e

    def upload_file(
        self,
        local_path: str | Path,
        remote_path: str | Path | None = None,
        *,
        unique: bool = False,
        force: bool = False,
        upload_path: str | None = None,
        **kwargs: Any,
    ) -> UploadResult:
        """
        Synchronously upload a file to catbox.moe.

        Args:
            local_path: Path to the file to upload
            remote_path: Ignored for this provider
            unique: Ignored for this provider
            force: Ignored for this provider
            upload_path: Ignored for this provider
            **kwargs: Additional provider-specific arguments

        Returns:
            UploadResult: Upload result with URL and metadata

        Raises:
            FileNotFoundError: If the file doesn't exist
            RetryableError: For temporary failures that can be retried
            NonRetryableError: For permanent failures
        """
        return cast(
            UploadResult,
            async_to_sync(self.async_upload_file)(
                local_path,
                remote_path,
                unique=unique,
                force=force,
                upload_path=upload_path,
                **kwargs,
            ),
        )

    def delete_files(self, files: list[str]) -> bool:
        """
        Synchronously delete files from catbox.moe.

        Args:
            files: List of filenames to delete

        Returns:
            True if deletion was successful

        Raises:
            NonRetryableError: If not authenticated or deletion fails
            RetryableError: If connection issues occur
        """
        result: bool = async_to_sync(self.async_delete_files)(files)
        return result

    def upload_url(
        self, url: str, *, unique: bool = False, force: bool = False
    ) -> UploadResult:
        """
        Synchronously upload a file from a URL to catbox.moe.

        Args:
            url: The URL to upload from
            unique: If True, ensures unique filename (not supported by Catbox)
            force: If True, overwrites existing file (not supported by Catbox)

        Returns:
            UploadResult: Upload result with URL and metadata

        Raises:
            RetryableError: For temporary failures that can be retried
            NonRetryableError: For permanent failures
        """
        result: UploadResult = async_to_sync(self.async_upload_url)(
            url, unique=unique, force=force
        )
        return result


def get_credentials() -> CatboxCredentials | None:
    """Get provider credentials from environment."""
    return CatboxProvider.get_credentials()


def get_provider() -> ProviderClient | None:
    """Initialize and return the provider client."""
    return CatboxProvider.get_provider()


def upload_file(
    local_path: str | Path, remote_path: str | Path | None = None
) -> UploadResult:
    """
    Upload a file to catbox.moe.

    Args:
        local_path: Path to the file to upload
        remote_path: Ignored for this provider

    Returns:
        UploadResult: Upload result with URL and metadata

    Raises:
        FileNotFoundError: If the file doesn't exist
        RetryableError: For temporary failures that can be retried
        NonRetryableError: For permanent failures
    """
    provider = get_provider()
    if not provider:
        msg = "Failed to initialize Catbox provider"
        raise NonRetryableError(msg, "catbox")
    return provider.upload_file(local_path, remote_path)


def upload_catbox(file_path: Path, max_retries: int = 3, backoff: int = 2) -> str:
    """
    Upload a file to Catbox. It retries on certain HTTP errors (e.g., 503).

    :param file_path: Path object representing the file to upload
    :param max_retries: Maximum number of retry attempts
    :param backoff: Seconds to wait between retries
    :return: The direct download URL from Catbox
    :raises RuntimeError: If the upload fails after the allowed retries
    """
    url = "https://catbox.moe/user/api.php"
    files = {"fileToUpload": open(file_path, "rb")}
    data = {"reqtype": "fileupload"}

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, files=files, data=data, timeout=30)
            if response.status_code == 200 and response.text.startswith("http"):
                return response.text.strip()
            else:
                # This covers unexpected status codes or a non-url response
                msg = f"Unexpected response (status {response.status_code}): {response.text}"
                raise RuntimeError(msg)
        except (requests.exceptions.RequestException, RuntimeError) as exc:
            # We log or print the error for debug/troubleshooting
            if attempt < max_retries:
                time.sleep(backoff)
            else:
                msg = f"Failed to upload file to Catbox after {max_retries} attempts: {exc}"
                raise RuntimeError(msg) from exc
    # This return won't be reached, but keeps linters happy
    return ""
