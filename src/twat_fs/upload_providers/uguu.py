#!/usr/bin/env python
# /// script
# dependencies = ["aiohttp"]
# ///
# this_file: src/twat_fs/upload_providers/uguu.py

"""
Uguu.se upload provider.
A simple provider that uploads files to uguu.se.
Files are automatically deleted after some time.
"""

import aiohttp
from pathlib import Path

from loguru import logger

from .simple import SimpleProviderBase, UploadResult


class UguuProvider(SimpleProviderBase):
    """Provider for uguu.se uploads"""

    PROVIDER_HELP = {"setup": "No setup required.", "deps": "Python package: aiohttp"}

    def __init__(self) -> None:
        self.upload_url = "https://uguu.se/upload"

    async def async_upload_file(self, file_path: Path) -> UploadResult:
        """Upload file to uguu.se"""
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field(
                    "files[]", open(file_path, "rb"), filename=file_path.name
                )

                async with session.post(self.upload_url, data=data) as response:
                    if response.status != 200:
                        error = await response.text()
                        raise ValueError(
                            f"Upload failed with status {response.status}: {error}"
                        )

                    result = await response.json()
                    if not result.get("success"):
                        raise ValueError("Upload failed according to response")

                    url = result["files"][0]["url"]
                    logger.info(f"Successfully uploaded to uguu.se: {url}")

                    return UploadResult(url=url, success=True, raw_response=result)

        except Exception as e:
            logger.error(f"Failed to upload to uguu.se: {e}")
            return UploadResult(url="", success=False, error=str(e))
