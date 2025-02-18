#!/usr/bin/env python
# /// script
# dependencies = ["aiohttp"]
# ///
# this_file: src/twat_fs/upload_providers/bashupload.py

"""
Bashupload.com upload provider.
A simple provider that uploads files to bashupload.com.
Files are automatically deleted after 3 days.
"""

import aiohttp
from pathlib import Path

from loguru import logger

from twat_fs.upload_providers.simple import SimpleProviderBase, UploadResult
from twat_fs.upload_providers.protocols import ProviderHelp, ProviderClient

# Provider help messages
PROVIDER_HELP: ProviderHelp = {
    "setup": "No setup required. Note: Files are deleted after 3 days.",
    "deps": "Python package: aiohttp",
}


class BashUploadProvider(SimpleProviderBase):
    """Provider for bashupload.com uploads"""

    def __init__(self) -> None:
        super().__init__()
        self.url = "https://bashupload.com"

    async def async_upload_file(
        self, file_path: Path, remote_path: str | Path | None = None
    ) -> UploadResult:
        """
        Upload file to bashupload.com

        Args:
            file_path: Path to the file to upload
            remote_path: Optional remote path (ignored as bashupload.com doesn't support custom paths)

        Returns:
            UploadResult containing the URL and status
        """
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                with self._open_file(file_path) as f:
                    data.add_field("file", f, filename=file_path.name)

                    async with session.post(self.url, data=data) as response:
                        if response.status != 200:
                            error = await response.text()
                            msg = (
                                f"Upload failed with status {response.status}: {error}"
                            )
                            raise ValueError(msg)

                        text = await response.text()
                        # Extract URL from response text
                        for line in text.splitlines():
                            if line.startswith("wget "):
                                url = line.split(" ")[1].strip()
                                logger.info(
                                    f"Successfully uploaded to bashupload: {url}"
                                )
                                return UploadResult(
                                    url=url, success=True, raw_response=text
                                )

                        msg = f"Could not find URL in response: {text}"
                        raise ValueError(msg)

        except Exception as e:
            logger.error(f"Failed to upload to bashupload: {e}")
            return UploadResult(url="", success=False, error=str(e))


# Module-level functions to implement the Provider protocol
def get_credentials() -> None:
    """Simple providers don't need credentials"""
    return None


def get_provider() -> ProviderClient | None:
    """Return an instance of the provider"""
    return BashUploadProvider()


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
