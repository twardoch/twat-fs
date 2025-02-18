#!/usr/bin/env python
# /// script
# dependencies = ["requests"]
# ///
# this_file: src/twat_fs/upload_providers/bashupload.py

"""
Bashupload.com upload provider.
A simple provider that uploads files to bashupload.com.
Files are automatically deleted after 3 days.
"""

import requests
from pathlib import Path
from typing import BinaryIO, ClassVar

from loguru import logger

from twat_fs.upload_providers.simple import SimpleProviderBase, UploadResult
from twat_fs.upload_providers.protocols import ProviderHelp, ProviderClient
from twat_fs.upload_providers.core import RetryableError, NonRetryableError

# Provider help messages
PROVIDER_HELP: ProviderHelp = {
    "setup": "No setup required. Note: Files are deleted after 3 days.",
    "deps": "Python package: requests",
}


class BashUploadProvider(SimpleProviderBase):
    """Provider for bashupload.com uploads"""

    PROVIDER_HELP: ClassVar[ProviderHelp] = PROVIDER_HELP

    def __init__(self) -> None:
        super().__init__()
        self.url = "https://bashupload.com"

    def upload_file_impl(self, file: BinaryIO) -> UploadResult:
        """
        Upload file to bashupload.com

        Args:
            file: Open file handle to upload

        Returns:
            UploadResult containing the URL and status

        Raises:
            RetryableError: For temporary failures that can be retried
            NonRetryableError: For permanent failures
        """
        try:
            files = {"file": file}
            response = requests.post(self.url, files=files, timeout=30)

            if response.status_code == 429:  # Rate limit
                msg = f"Rate limited: {response.text}"
                raise RetryableError(msg, "bashupload")
            elif response.status_code != 200:
                msg = (
                    f"Upload failed with status {response.status_code}: {response.text}"
                )
                raise NonRetryableError(msg, "bashupload")

            # Extract URL from response text
            for line in response.text.splitlines():
                if line.startswith("wget "):
                    url = line.split(" ")[1].strip()
                    logger.debug(f"Successfully uploaded to bashupload: {url}")
                    return UploadResult(
                        url=f"{url}?download=1",
                        success=True,
                        raw_response=response.text,
                        metadata={"provider": "bashupload"},
                    )

            msg = f"Could not find URL in response: {response.text}"
            raise NonRetryableError(msg, "bashupload")

        except requests.Timeout as e:
            msg = f"Upload timed out: {e}"
            raise RetryableError(msg, "bashupload") from e
        except requests.ConnectionError as e:
            msg = f"Connection error: {e}"
            raise RetryableError(msg, "bashupload") from e
        except Exception as e:
            msg = f"Upload failed: {e}"
            raise NonRetryableError(msg, "bashupload") from e

    @classmethod
    def get_credentials(cls) -> None:
        """Simple providers don't need credentials"""
        return None

    @classmethod
    def get_provider(cls) -> ProviderClient | None:
        """Return an instance of this provider"""
        return cls()


# Module-level functions to implement the Provider protocol
def get_credentials() -> None:
    """Simple providers don't need credentials"""
    return None


def get_provider() -> ProviderClient | None:
    """Return an instance of the provider"""
    return BashUploadProvider.get_provider()


def upload_file(local_path: str | Path, remote_path: str | Path | None = None) -> str:
    """
    Upload a file and return its URL.

    Args:
        local_path: Path to the file to upload
        remote_path: Optional remote path (ignored for simple providers)

    Returns:
        str: URL to the uploaded file

    Raises:
        ValueError: If upload fails
    """
    provider = get_provider()
    if not provider:
        msg = "Failed to initialize provider"
        raise ValueError(msg)
    return provider.upload_file(local_path, remote_path)
