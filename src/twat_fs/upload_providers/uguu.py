#!/usr/bin/env python
# /// script
# dependencies = ["requests"]
# ///
# this_file: src/twat_fs/upload_providers/uguu.py

"""
Uguu.se upload provider.
A simple provider that uploads files to uguu.se.
Files are automatically deleted after 48 hours.
"""

import requests
from pathlib import Path
from typing import BinaryIO

from loguru import logger

from twat_fs.upload_providers.simple import SimpleProviderBase, UploadResult
from twat_fs.upload_providers.protocols import ProviderHelp, ProviderClient

# Provider help messages
PROVIDER_HELP: ProviderHelp = {
    "setup": "No setup required. Note: Files are deleted after 48 hours.",
    "deps": "Python package: requests",
}


class UguuProvider(SimpleProviderBase):
    """Provider for uguu.se uploads"""

    def __init__(self) -> None:
        super().__init__()
        self.url = "https://uguu.se/upload.php"

    def upload_file_impl(self, file: BinaryIO) -> UploadResult:
        """
        Upload file to uguu.se

        Args:
            file: Open file handle to upload

        Returns:
            UploadResult containing the URL and status
        """
        try:
            files = {"files[]": file}
            response = requests.post(self.url, files=files)

            if response.status_code != 200:
                msg = (
                    f"Upload failed with status {response.status_code}: {response.text}"
                )
                raise ValueError(msg)

            result = response.json()
            if not result or "files" not in result:
                msg = f"Invalid response from uguu.se: {result}"
                raise ValueError(msg)

            url = result["files"][0]["url"]
            logger.debug(f"Successfully uploaded to uguu.se: {url}")

            return UploadResult(url=url, success=True, raw_response=result)

        except Exception as e:
            logger.error(f"Failed to upload to uguu.se: {e}")
            return UploadResult(url="", success=False, error=str(e))


# Module-level functions to implement the Provider protocol
def get_credentials() -> None:
    """Simple providers don't need credentials"""
    return None


def get_provider() -> ProviderClient | None:
    """Return an instance of the provider"""
    return UguuProvider()


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
