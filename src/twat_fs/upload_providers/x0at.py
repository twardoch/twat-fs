# this_file: src/twat_fs/upload_providers/x0at.py

"""
x0.at file upload provider.
A simple provider that uploads files to x0.at.
Max size: 512 MiB. Retention: 3-100 days (smaller files last longer).
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
    setup_instructions="No setup required. Max 512 MiB. Retention: 3-100 days (smaller files last longer).",
    dependency_info="Python package: requests",
    max_size="512 MiB",
    retention="3-100 days (smaller files last longer)",
    auth_required="None",
)


class X0atProvider(BaseProvider):
    """Provider for x0.at uploads."""

    PROVIDER_HELP: ClassVar[ProviderHelp] = PROVIDER_HELP
    provider_name: str = "x0at"
    upload_url: str = "https://x0.at/"

    def __init__(self) -> None:
        """Initialize the x0.at provider."""
        self.provider_name = "x0at"

    def _do_upload(self, file: BinaryIO) -> str:
        """
        Internal implementation of the file upload to x0.at.

        Args:
            file: Open file handle to upload

        Returns:
            str: URL of the uploaded file

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

        # Parse the response — plain text URL
        url = response.text.strip()
        if not url.startswith("http"):
            msg = f"Invalid response from server: {url}"
            raise NonRetryableError(msg, self.provider_name)

        return url

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
    return X0atProvider.get_credentials()


def get_provider() -> ProviderClient | None:
    """Return an instance of the provider."""
    return X0atProvider.get_provider()


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
        "x0at",
        local_path,
        remote_path,
        unique=unique,
        force=force,
        upload_path=upload_path,
    )
