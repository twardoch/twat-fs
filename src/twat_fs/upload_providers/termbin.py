#!/usr/bin/env python
# /// script
# dependencies = []
# ///
# this_file: src/twat_fs/upload_providers/termbin.py

"""
Termbin.com upload provider.
A simple provider that uploads files via netcat to termbin.com.
Best suited for text files as it sends raw file contents.
"""

import asyncio
from pathlib import Path

from loguru import logger

from .simple import SimpleProviderBase, UploadResult


class TermbinProvider(SimpleProviderBase):
    """Provider for termbin.com uploads"""

    PROVIDER_HELP = {
        "setup": "No setup required. Ensure you have netcat (nc) installed.",
        "deps": "System package: netcat (nc)",
    }

    def __init__(self) -> None:
        self.host = "termbin.com"
        self.port = 9999

    async def async_upload_file(self, file_path: Path) -> UploadResult:
        """Upload file contents to termbin.com using netcat-style connection"""
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)

            # Read and send file contents
            content = file_path.read_text()
            writer.write(content.encode())
            await writer.drain()

            # Get URL from response
            response = await reader.read()
            writer.close()
            await writer.wait_closed()

            url = response.decode().strip()
            logger.info(f"Successfully uploaded to termbin.com: {url}")

            return UploadResult(url=url, success=True, raw_response=url)

        except Exception as e:
            logger.error(f"Failed to upload to termbin.com: {e}")
            return UploadResult(url="", success=False, error=str(e))
