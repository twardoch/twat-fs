#!/usr/bin/env python
# /// script
# dependencies = ["aiohttp"]
# ///
# this_file: src/twat_fs/upload_providers/0x0.py

"""
0x0.st upload provider.
A simple provider that uploads files to 0x0.st.
"""

import aiohttp
from pathlib import Path

from loguru import logger

from .simple import SimpleProviderBase, UploadResult


class ZeroXZeroProvider(SimpleProviderBase):
    """Provider for 0x0.st uploads"""

    PROVIDER_HELP = {"setup": "No setup required.", "deps": "Python package: aiohttp"}

    def __init__(self) -> None:
        self.url = "https://0x0.st"

    async def async_upload_file(self, file_path: Path) -> UploadResult:
        """Upload file to 0x0.st"""
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field("file", open(file_path, "rb"), filename=file_path.name)

                async with session.post(self.url, data=data) as response:
                    if response.status != 200:
                        error = await response.text()
                        raise ValueError(
                            f"Upload failed with status {response.status}: {error}"
                        )

                    url = (await response.text()).strip()
                    logger.info(f"Successfully uploaded to 0x0.st: {url}")

                    return UploadResult(url=url, success=True, raw_response=url)

        except Exception as e:
            logger.error(f"Failed to upload to 0x0.st: {e}")
            return UploadResult(url="", success=False, error=str(e))
