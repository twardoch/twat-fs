#!/usr/bin/env python
# /// script
# dependencies = ["aiohttp"]
# ///
# this_file: src/twat_fs/upload_providers/bashupload.py

"""
Bashupload.com upload provider.
A simple provider that uploads files to bashupload.com.
"""

import aiohttp
from pathlib import Path

from loguru import logger

from .simple import SimpleProviderBase, UploadResult


class BashUploadProvider(SimpleProviderBase):
    """Provider for bashupload.com uploads"""

    PROVIDER_HELP = {"setup": "No setup required.", "deps": "Python package: aiohttp"}

    def __init__(self) -> None:
        self.upload_url = "https://bashupload.com/"

    async def async_upload_file(self, file_path: Path) -> UploadResult:
        """Upload file to bashupload.com"""
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field("file", open(file_path, "rb"), filename=file_path.name)

                async with session.post(self.upload_url, data=data) as response:
                    if response.status != 200:
                        error = await response.text()
                        msg = f"Upload failed with status {response.status}: {error}"
                        raise ValueError(
                            msg
                        )

                    text = await response.text()
                    # Parse the wget URL from response
                    for line in text.splitlines():
                        if line.startswith("wget "):
                            url = line.split(" ")[1].strip()
                            # Transform URL to add download parameter
                            download_url = f"{url}?download=1"
                            logger.info(
                                f"Successfully uploaded to bashupload.com: {download_url}"
                            )
                            return UploadResult(
                                url=download_url, success=True, raw_response=text
                            )

                    msg = "Could not parse upload URL from response"
                    raise ValueError(msg)

        except Exception as e:
            logger.error(f"Failed to upload to bashupload.com: {e}")
            return UploadResult(url="", success=False, error=str(e))
