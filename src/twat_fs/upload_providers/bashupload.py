# this_file: src/twat_fs/upload_providers/bashupload.py

"""
Bashupload.com upload provider.
A simple provider that uploads files to bashupload.com.
Files are automatically deleted after 3 days.
"""

from collections.abc import Awaitable
from pathlib import Path
from typing import Any, cast

import aiohttp

from twat_fs.upload_providers.protocols import Provider, ProviderClient, ProviderHelp
from twat_fs.upload_providers.types import UploadResult
from twat_fs.upload_providers.core import NonRetryableError
from twat_fs.upload_providers.utils import (
    handle_http_response,
    log_upload_attempt,
    validate_file,
)

PROVIDER_HELP: ProviderHelp = {
    "setup": "No setup required. Files are deleted after 3 days.",
    "deps": "requests, aiohttp",
}


class BashUploadProvider(Provider, ProviderClient):
    """Provider for bashupload.com uploads"""

    PROVIDER_HELP = PROVIDER_HELP
    provider_name = "bashupload"
    upload_url = "https://bashupload.com"

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
        Internal implementation of the file upload to bashupload.com.

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

        with open(file_path, "rb") as f:
            data.add_field("file", f, filename=file_path.name)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.upload_url,
                    data=data,
                    timeout=None,
                ) as response:
                    handle_http_response(response, self.provider_name)

                    response_text = await response.text()
                    for line in response_text.splitlines():
                        if line.startswith("wget "):
                            url = line.split(" ")[1].strip()
                            log_upload_attempt(self.provider_name, file_path, True)
                            return UploadResult(
                                url=f"{url}?download=1",
                                metadata={
                                    "provider": self.provider_name,
                                    "success": True,
                                    "raw_response": response_text,
                                },
                            )

                    msg = f"Could not find URL in response: {response_text}"
                    raise NonRetryableError(msg, self.provider_name)

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
        Upload a file to bashupload.com.

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
        Upload a file to bashupload.com.

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


def get_provider() -> BashUploadProvider:
    """Get an instance of the BashUpload provider."""
    return BashUploadProvider()


def upload_file(
    local_path: str | Path,
    remote_path: str | Path | None = None,
    *,
    unique: bool = False,
    force: bool = False,
    upload_path: str | None = None,
) -> UploadResult:
    """
    Upload a file to bashupload.com.

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
