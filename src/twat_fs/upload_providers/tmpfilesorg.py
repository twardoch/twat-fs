# this_file: src/twat_fs/upload_providers/tmpfilesorg.py

"""
tmpfiles.org file upload provider.
A simple provider that uploads files to tmpfiles.org.
Retention: 60 minutes only. No auth required.
"""

from __future__ import annotations

import requests
from pathlib import Path
from typing import BinaryIO, ClassVar, cast

from twat_fs.upload_providers.types import UploadResult
from twat_fs.upload_providers.core import NonRetryableError
from twat_fs.upload_providers.simple import BaseProvider
from twat_fs.upload_providers.protocols import ProviderHelp, ProviderClient
from twat_fs.upload_providers.utils import (
    create_provider_help,
    handle_http_response,
    log_upload_attempt,
    standard_upload_wrapper,
)

# Use standardized provider help format
PROVIDER_HELP: ProviderHelp = create_provider_help(
    setup_instructions="No setup required. WARNING: Files expire after 60 minutes.",
    dependency_info="Python package: requests",
    max_size="Unknown",
    retention="60 minutes",
    auth_required="None",
)


class TmpfilesorgProvider(BaseProvider):
    """Provider for tmpfiles.org uploads."""

    PROVIDER_HELP: ClassVar[ProviderHelp] = PROVIDER_HELP
    provider_name: str = "tmpfilesorg"
    upload_url: str = "https://tmpfiles.org/api/v1/upload"

    def __init__(self) -> None:
        """Initialize the tmpfiles.org provider."""
        self.provider_name = "tmpfilesorg"

    @staticmethod
    def _transform_to_download_url(url: str) -> str:
        """
        Transform a tmpfiles.org URL to a direct download URL.

        tmpfiles.org returns URLs like: https://tmpfiles.org/12345/file.ext
        Direct download requires inserting /dl/: https://tmpfiles.org/dl/12345/file.ext

        Args:
            url: The URL returned by the API

        Returns:
            str: The direct download URL
        """
        # Insert /dl/ after the domain
        prefix = "https://tmpfiles.org/"
        if url.startswith(prefix):
            path = url[len(prefix) :]
            return f"{prefix}dl/{path}"
        # Also handle http:// variant
        http_prefix = "http://tmpfiles.org/"
        if url.startswith(http_prefix):
            path = url[len(http_prefix) :]
            return f"https://tmpfiles.org/dl/{path}"
        return url

    def _do_upload(self, file: BinaryIO) -> str:
        """
        Internal implementation of the file upload to tmpfiles.org.

        Args:
            file: Open file handle to upload

        Returns:
            str: Direct download URL of the uploaded file

        Raises:
            NonRetryableError: If the upload fails or response is invalid
        """
        files = {"file": (Path(file.name).name, file, "application/octet-stream")}
        response = requests.post(
            self.upload_url,
            files=files,
            timeout=30,
            headers={"User-Agent": "twat-fs/1.0"},
        )

        # Use standardized HTTP response handling
        handle_http_response(response, self.provider_name)

        # Parse JSON response: {"status": "success", "data": {"url": "..."}}
        try:
            data = response.json()
        except ValueError as e:
            msg = f"Invalid JSON response: {e}"
            raise NonRetryableError(msg, self.provider_name) from e

        try:
            upload_url = data["data"]["url"]
        except (KeyError, TypeError) as e:
            msg = f"Unexpected response structure: {data}"
            raise NonRetryableError(msg, self.provider_name) from e

        if not upload_url or not isinstance(upload_url, str):
            msg = f"Invalid URL in response: {upload_url}"
            raise NonRetryableError(msg, self.provider_name)

        # Transform to direct download URL
        return self._transform_to_download_url(upload_url)

    def upload_file_impl(self, file: BinaryIO) -> UploadResult:
        """
        Implement the actual file upload logic.

        Args:
            file: Open file handle to upload

        Returns:
            UploadResult containing the URL and status
        """
        try:
            url = self._do_upload(file)

            log_upload_attempt(
                provider_name=self.provider_name,
                file_path=file.name,
                success=True,
            )

            return UploadResult(
                url=url,
                metadata={
                    "provider": self.provider_name,
                    "success": True,
                    "raw_url": url,
                    "expires_minutes": 60,
                },
            )
        except NonRetryableError:
            raise
        except Exception as e:
            log_upload_attempt(
                provider_name=self.provider_name,
                file_path=file.name,
                success=False,
                error=e,
            )

            return UploadResult(
                url="",
                metadata={
                    "provider": self.provider_name,
                    "success": False,
                    "error": str(e),
                },
            )

    @classmethod
    def get_credentials(cls) -> None:
        """Simple providers don't need credentials."""
        return None

    @classmethod
    def get_provider(cls) -> ProviderClient | None:
        """Initialize and return the provider client."""
        return cast(ProviderClient, cls())


# Module-level functions to implement the Provider protocol
def get_credentials() -> None:
    """Simple providers don't need credentials."""
    return TmpfilesorgProvider.get_credentials()


def get_provider() -> ProviderClient | None:
    """Return an instance of the provider."""
    return TmpfilesorgProvider.get_provider()


def upload_file(
    local_path: str | Path,
    remote_path: str | Path | None = None,
    *,
    unique: bool = False,
    force: bool = False,
    upload_path: str | None = None,
) -> UploadResult:
    """
    Upload a file and return its URL.

    WARNING: tmpfiles.org files expire after 60 minutes.

    Args:
        local_path: Path to the file to upload
        remote_path: Optional remote path (ignored for simple providers)
        unique: Ignored for this provider
        force: Ignored for this provider
        upload_path: Ignored for this provider

    Returns:
        UploadResult: URL of the uploaded file
    """
    return standard_upload_wrapper(
        get_provider(),
        "tmpfilesorg",
        local_path,
        remote_path,
        unique=unique,
        force=force,
        upload_path=upload_path,
    )
