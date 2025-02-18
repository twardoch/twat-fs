#!/usr/bin/env python
# /// script
# dependencies = ["requests"]
# ///
# this_file: src/twat_fs/upload_providers/filebin.py

"""
Filebin.net upload provider.
A simple provider that uploads files to filebin.net.
Files are automatically deleted after 6 days.
"""

import requests
from pathlib import Path
from typing import BinaryIO, cast

from loguru import logger

from twat_fs.upload_providers.simple import SimpleProviderBase, UploadResult
from twat_fs.upload_providers.protocols import ProviderHelp, ProviderClient

# Provider help messages
PROVIDER_HELP: ProviderHelp = {
    "setup": "No setup required. Note: Files are deleted after 6 days.",
    "deps": "Python package: requests",
}


class FilebinProvider(SimpleProviderBase):
    """Provider for filebin.net uploads"""

    def __init__(self) -> None:
        super().__init__()
        self.url = "https://filebin.net"

    def upload_file_impl(self, file: BinaryIO) -> UploadResult:
        """
        Implement the actual file upload logic.

        Args:
            file: Open file handle to upload

        Returns:
            UploadResult containing the URL and status
        """
        try:
            files = {"file": (file.name, file)}
            response = requests.post(self.url, files=files)

            if response.status_code != 200:
                msg = (
                    f"Upload failed with status {response.status_code}: {response.text}"
                )
                raise ValueError(msg)

            # The response URL is in the response URL
            url = response.url
            if not url:
                msg = "No URL in response"
                raise ValueError(msg)

            logger.info(f"Successfully uploaded to filebin.net: {url}")
            return UploadResult(url=str(url), success=True, raw_response=response.text)

        except Exception as e:
            logger.error(f"Failed to upload to filebin.net: {e}")
            return UploadResult(url="", success=False, error=str(e))


# Module-level functions to implement the Provider protocol
def get_credentials() -> None:
    """Simple providers don't need credentials"""
    return None


def get_provider() -> ProviderClient | None:
    """Return an instance of the provider"""
    return cast(ProviderClient, FilebinProvider())


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
