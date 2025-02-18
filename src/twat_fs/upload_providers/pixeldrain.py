#!/usr/bin/env python
# /// script
# dependencies = ["requests"]
# ///
# this_file: src/twat_fs/upload_providers/pixeldrain.py

"""
Pixeldrain.com upload provider.
A simple provider that uploads files to pixeldrain.com.
"""

import requests
from pathlib import Path
from typing import BinaryIO, cast

from loguru import logger

from .simple import SimpleProviderBase, UploadResult
from . import ProviderHelp, ProviderClient

# Provider help messages
PROVIDER_HELP: ProviderHelp = {
    "setup": "No setup required.",
    "deps": "Python package: requests",
}


class PixeldrainProvider(SimpleProviderBase):
    """Provider for pixeldrain.com uploads"""

    def __init__(self) -> None:
        super().__init__()
        self.url = "https://pixeldrain.com/api/file"

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

            # Parse response JSON to get file ID
            data = response.json()
            if not data or "id" not in data:
                msg = f"Invalid response from pixeldrain: {data}"
                raise ValueError(msg)

            # Construct public URL
            url = f"https://pixeldrain.com/u/{data['id']}"
            logger.info(f"Successfully uploaded to pixeldrain.com: {url}")
            return UploadResult(url=url, success=True, raw_response=data)

        except Exception as e:
            logger.error(f"Failed to upload to pixeldrain.com: {e}")
            return UploadResult(url="", success=False, error=str(e))


# Module-level functions to implement the Provider protocol
def get_credentials() -> None:
    """Simple providers don't need credentials"""
    return None


def get_provider() -> ProviderClient | None:
    """Return an instance of the provider"""
    return cast(ProviderClient, PixeldrainProvider())


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
