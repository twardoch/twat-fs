# this_file: src/twat_fs/upload_providers/catbox.py

"""
Catbox.moe upload provider implementation.
"""

from collections.abc import Awaitable
from pathlib import Path
from typing import Any, cast

import aiohttp

from twat_fs.upload_providers.protocols import ProviderClient, ProviderHelp, Provider
from twat_fs.upload_providers.core import (
    UploadResult,
)
from twat_fs.upload_providers.utils import (
    handle_http_response,
    log_upload_attempt,
    validate_file,
)

PROVIDER_HELP: ProviderHelp = {
    "setup": "No setup required. Files are kept indefinitely unless reported or unused for 1 month.",
    "deps": "aiohttp",
}


class CatboxProvider(Provider, ProviderClient):
    """Provider for uploading files to catbox.moe."""

    PROVIDER_HELP = PROVIDER_HELP
    provider_name = "catbox"
    upload_url = "https://catbox.moe/user/api.php"

    @classmethod
    def get_credentials(cls) -> None:
        """No credentials needed for this provider."""
        return None

    @classmethod
    def get_provider(cls) -> ProviderClient | None:
        """Get an instance of the provider."""
        return cls()

    async def _do_upload(self, file_path: Path) -> UploadResult:
        """
        Internal implementation of the file upload to catbox.moe.

        Args:
            file_path: Path to the file to upload

        Returns:
            UploadResult with the URL of the uploaded file

        Raises:
            RetryableError: If the upload fails due to rate limiting
            NonRetryableError: If the upload fails for any other reason
        """
        validate_file(file_path)

        data = aiohttp.FormData()
        data.add_field("reqtype", "fileupload")

        with open(file_path, "rb") as f:
            data.add_field("fileToUpload", f, filename=file_path.name)

            async with aiohttp.ClientSession() as session:
                async with session.post(self.upload_url, data=data) as response:
                    handle_http_response(response, self.provider_name)
                    url = await response.text()
                    log_upload_attempt(self.provider_name, file_path, True)
                    return UploadResult(url=url)

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
        Upload a file to catbox.moe.

        Args:
            local_path: Path to the file to upload
            remote_path: Ignored for this provider
            unique: Ignored for this provider
            force: Ignored for this provider
            upload_path: Ignored for this provider
            **kwargs: Additional provider-specific arguments

        Returns:
            UploadResult with the URL of the uploaded file

        Raises:
            RetryableError: If the upload fails due to rate limiting
            NonRetryableError: If the upload fails for any other reason
        """
        import asyncio

        return asyncio.run(self._do_upload(Path(str(local_path))))

    async def async_upload_file(
        self,
        file_path: str | Path,
        remote_path: str | Path | None = None,
        *,
        unique: bool = False,
        force: bool = False,
        upload_path: str | None = None,
        **kwargs: Any,
    ) -> Awaitable[UploadResult]:
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
            Awaitable that resolves to an UploadResult with the URL of the uploaded file

        Raises:
            RetryableError: If the upload fails due to rate limiting
            NonRetryableError: If the upload fails for any other reason
        """
        try:
            result = await self._do_upload(Path(str(file_path)))
            return cast(Awaitable[UploadResult], result)
        except Exception as e:
            log_upload_attempt(self.provider_name, file_path, False, e)
            raise


def get_provider() -> CatboxProvider:
    """Get an instance of the Catbox provider."""
    return CatboxProvider()


def upload_file(
    local_path: str | Path,
    remote_path: str | Path | None = None,
    *,
    unique: bool = False,
    force: bool = False,
    upload_path: str | None = None,
) -> UploadResult:
    """
    Upload a file to catbox.moe.

    Args:
        local_path: Path to the file to upload
        remote_path: Ignored for this provider
        unique: Ignored for this provider
        force: Ignored for this provider
        upload_path: Ignored for this provider

    Returns:
        UploadResult with the URL of the uploaded file

    Raises:
        RetryableError: If the upload fails due to rate limiting
        NonRetryableError: If the upload fails for any other reason
    """
    provider = get_provider()
    return provider.upload_file(
        local_path,
        remote_path,
        unique=unique,
        force=force,
        upload_path=upload_path,
    )
