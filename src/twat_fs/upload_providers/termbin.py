#!/usr/bin/env python
# /// script
# dependencies = []
# ///
# this_file: src/twat_fs/upload_providers/termbin.py

"""
Termbin upload provider.
A simple provider that uploads text files to termbin.com using netcat.
"""

import asyncio
from pathlib import Path

from loguru import logger

from twat_fs.upload_providers.simple import SimpleProviderBase, UploadResult
from twat_fs.upload_providers.protocols import ProviderHelp, ProviderClient

# Provider help messages
PROVIDER_HELP: ProviderHelp = {
    "setup": "No setup required. Note: Only works with text files.",
    "deps": "System package: netcat (nc)",
}


class TermbinProvider(SimpleProviderBase):
    """Provider for termbin.com uploads"""

    def __init__(self) -> None:
        super().__init__()
        self.host = "termbin.com"
        self.port = 9999

    async def async_upload_file(
        self, file_path: Path, remote_path: str | Path | None = None
    ) -> UploadResult:
        """
        Upload text file to termbin.com using netcat

        Args:
            file_path: Path to the file to upload
            remote_path: Optional remote path (ignored as termbin.com doesn't support custom paths)

        Returns:
            UploadResult containing the URL and status
        """
        try:
            # Read file content
            with self._open_file(file_path) as f:
                content = f.read()

            # Connect to termbin.com
            reader, writer = await asyncio.open_connection(self.host, self.port)

            # Send file content
            writer.write(content)
            await writer.drain()

            # Get response
            response = await reader.read()
            writer.close()
            await writer.wait_closed()

            # Parse URL from response
            url = response.decode().strip()
            if not url.startswith("http"):
                msg = f"Invalid response from termbin: {url}"
                raise ValueError(msg)

            logger.info(f"Successfully uploaded to termbin: {url}")
            return UploadResult(url=url, success=True, raw_response=url)

        except Exception as e:
            logger.error(f"Failed to upload to termbin: {e}")
            return UploadResult(url="", success=False, error=str(e))


# Module-level functions to implement the Provider protocol
def get_credentials() -> None:
    """Simple providers don't need credentials"""
    return None


def get_provider() -> ProviderClient | None:
    """Return an instance of the provider"""
    return TermbinProvider()


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
