#!/usr/bin/env python
# /// script
# dependencies = ["aiohttp"]
# ///
# this_file: src/twat_fs/upload_providers/www0x0.py

"""
0x0.st upload provider.
A simple provider that uploads files to 0x0.st.
Files are hosted at www.0x0.st.
"""

import aiohttp
from pathlib import Path

from loguru import logger

from .simple import SimpleProviderBase, UploadResult
from . import ProviderHelp, ProviderClient

# Provider help messages
PROVIDER_HELP: ProviderHelp = {
    "setup": "No setup required.",
    "deps": "Python package: aiohttp",
}


class ZeroXZeroProvider(SimpleProviderBase):
    """Provider for 0x0.st uploads (www.0x0.st)"""

    def __init__(self) -> None:
        super().__init__()
        self.url = "https://0x0.st"

    async def async_upload_file(
        self, file_path: Path, remote_path: str | Path | None = None
    ) -> UploadResult:
        """
        Upload file to 0x0.st (www.0x0.st)

        Args:
            file_path: Path to the file to upload
            remote_path: Optional remote path (ignored as 0x0.st doesn't support custom paths)

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

                        url = (await response.text()).strip()
                        logger.info(f"Successfully uploaded to 0x0.st: {url}")

                        return UploadResult(url=url, success=True, raw_response=url)

        except Exception as e:
            logger.error(f"Failed to upload to 0x0.st: {e}")
            return UploadResult(url="", success=False, error=str(e))


# Module-level functions to implement the Provider protocol
def get_credentials() -> None:
    """Simple providers don't need credentials"""
    return None


def get_provider() -> ProviderClient | None:
    """Return an instance of the provider"""
    return ZeroXZeroProvider()


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
