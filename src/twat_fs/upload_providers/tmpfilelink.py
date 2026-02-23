# this_file: src/twat_fs/upload_providers/tmpfilelink.py

"""
tmpfile.link file upload provider.
A simple provider that uploads files to tmpfile.link.
Max size: 100 MB. Retention: 7 days. No auth required.
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
    setup_instructions="No setup required. Max 100 MB. Retention: 7 days.",
    dependency_info="Python package: requests",
    max_size="100 MB",
    retention="7 days",
    auth_required="None",
)


class TmpfilelinkProvider(BaseProvider):
    """Provider for tmpfile.link uploads."""

    PROVIDER_HELP: ClassVar[ProviderHelp] = PROVIDER_HELP
    provider_name: str = "tmpfilelink"
    upload_url: str = "https://tmpfile.link/api/upload"

    def __init__(self) -> None:
        """Initialize the tmpfile.link provider."""
        self.provider_name = "tmpfilelink"

    def _do_upload(self, file: BinaryIO) -> str:
        """
        Internal implementation of the file upload to tmpfile.link.

        Args:
            file: Open file handle to upload

        Returns:
            str: Download URL of the uploaded file

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

        # Parse JSON response containing downloadLink
        try:
            data = response.json()
        except ValueError as e:
            msg = f"Invalid JSON response: {e}"
            raise NonRetryableError(msg, self.provider_name) from e

        download_link = data.get("downloadLink")
        if not download_link or not isinstance(download_link, str):
            msg = f"Missing or invalid downloadLink in response: {data}"
            raise NonRetryableError(msg, self.provider_name)

        if not download_link.startswith("http"):
            msg = f"Invalid download URL: {download_link}"
            raise NonRetryableError(msg, self.provider_name)

        return str(download_link)

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
                    "expires_days": 7,
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
    return TmpfilelinkProvider.get_credentials()


def get_provider() -> ProviderClient | None:
    """Return an instance of the provider."""
    return TmpfilelinkProvider.get_provider()


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
        "tmpfilelink",
        local_path,
        remote_path,
        unique=unique,
        force=force,
        upload_path=upload_path,
    )
