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
import time

from loguru import logger

from twat_fs.upload_providers.simple import SimpleProviderBase, UploadResult
from twat_fs.upload_providers.protocols import ProviderHelp, ProviderClient

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
            # Upload with retries
            max_retries = 3
            retry_delay = 2
            last_error = None

            for attempt in range(max_retries):
                try:
                    files = {"file": (file.name, file)}
                    headers = {"User-Agent": "twat-fs/1.0"}
                    response = requests.post(
                        self.url,
                        files=files,
                        headers=headers,
                        timeout=30,
                    )

                    if response.status_code == 429:  # Rate limit
                        last_error = f"Rate limited: {response.text}"
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            file.seek(0)
                            continue

                    if response.status_code != 200:
                        last_error = f"Upload failed with status {response.status_code}: {response.text}"
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            file.seek(0)
                            continue
                        break

                    # Parse response JSON to get file ID
                    try:
                        data = response.json()
                    except ValueError as e:
                        last_error = f"Invalid JSON response: {e}"
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            file.seek(0)
                            continue
                        break

                    if not data or "id" not in data:
                        last_error = f"Invalid response from pixeldrain: {data}"
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            retry_delay *= 2
                            file.seek(0)
                            continue
                        break

                    # Construct public URL
                    url = f"https://pixeldrain.com/u/{data['id']}"
                    logger.info(f"Successfully uploaded to pixeldrain.com: {url}")
                    return UploadResult(
                        url=url,
                        success=True,
                        raw_response=data,
                        metadata={"provider": "pixeldrain"},
                    )

                except requests.RequestException as e:
                    last_error = f"Request failed: {e}"
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        file.seek(0)

            if last_error:
                raise ValueError(last_error)
            msg = "Upload failed after retries"
            raise ValueError(msg)

        except Exception as e:
            logger.error(f"Failed to upload to pixeldrain.com: {e}")
            return UploadResult(
                url="",
                success=False,
                error=str(e),
                metadata={"provider": "pixeldrain"},
            )


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
