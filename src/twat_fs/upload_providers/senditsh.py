# this_file: src/twat_fs/upload_providers/senditsh.py

"""
sendit.sh file upload provider.
A simple provider that uploads files to sendit.sh using PUT method.
Max size: 3 GB. Retention: 1 day. SINGLE DOWNLOAD ONLY — file is deleted after first download.
"""

from __future__ import annotations

import re
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
    setup_instructions=(
        "No setup required. Max 3 GB. Retention: 1 day. "
        "WARNING: Single download only — file is deleted after first download."
    ),
    dependency_info="Python package: requests",
    max_size="3 GB",
    retention="1 day (single download only)",
    auth_required="None",
)

# Regex to extract URL from response text
_URL_PATTERN = re.compile(r"https?://sendit\.sh/\S+")


class SenditshProvider(BaseProvider):
    """Provider for sendit.sh uploads (PUT method, single-download)."""

    PROVIDER_HELP: ClassVar[ProviderHelp] = PROVIDER_HELP
    provider_name: str = "senditsh"
    upload_url: str = "https://sendit.sh/"

    def __init__(self) -> None:
        """Initialize the sendit.sh provider."""
        self.provider_name = "senditsh"

    def _do_upload(self, file: BinaryIO) -> str:
        """
        Internal implementation of the file upload to sendit.sh.

        Uses PUT method with raw file content.

        Args:
            file: Open file handle to upload

        Returns:
            str: URL of the uploaded file

        Raises:
            NonRetryableError: If the upload fails or response is invalid
        """
        filename = Path(file.name).name
        file_content = file.read()

        response = requests.put(
            f"{self.upload_url}{filename}",
            data=file_content,
            headers={
                "Content-Type": "application/octet-stream",
                "User-Agent": "twat-fs/1.0",
            },
            timeout=60,
        )

        # Use standardized HTTP response handling
        handle_http_response(response, self.provider_name)

        # Parse the response — extract URL with regex
        match = _URL_PATTERN.search(response.text)
        if not match:
            msg = f"Could not find download URL in response: {response.text[:200]}"
            raise NonRetryableError(msg, self.provider_name)

        return match.group(0)

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
                    "single_download": True,
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
    return SenditshProvider.get_credentials()


def get_provider() -> ProviderClient | None:
    """Return an instance of the provider."""
    return SenditshProvider.get_provider()


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

    WARNING: sendit.sh is single-download only. The file is deleted after the first download.

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
        "senditsh",
        local_path,
        remote_path,
        unique=unique,
        force=force,
        upload_path=upload_path,
    )
