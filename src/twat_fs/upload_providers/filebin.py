# this_file: src/twat_fs/upload_providers/filebin.py

"""
Filebin.net upload provider.
A simple provider that uploads files to filebin.net.
Files are automatically deleted after 6 days.
"""

from twat_fs.upload_providers.types import UploadResult

import requests
from pathlib import Path
from typing import BinaryIO, cast, ClassVar
import time
import random
import string

from loguru import logger

from twat_fs.upload_providers.simple import BaseProvider, UploadResult

from twat_fs.upload_providers.protocols import ProviderHelp, ProviderClient

# Provider help messages
PROVIDER_HELP: ProviderHelp = {
    "setup": "No setup required. Note: Files are deleted after 6 days.",
    "deps": "Python package: requests",
}


class FilebinProvider(BaseProvider):
    """Provider for filebin.net uploads"""

    PROVIDER_HELP: ClassVar[ProviderHelp] = PROVIDER_HELP
    provider_name: str = "filebin"

    def __init__(self) -> None:
        super().__init__()
        self.url = "https://filebin.net"

    def upload_file_impl(self, file: BinaryIO) -> UploadResult:
        """
        Implement the actual file upload logic.

        Args:
            file: Open file handle to upload

        Returns:
            UploadResult containing the URL and status
        """
        try:
            # Get the filename from the file object
            filename = Path(file.name).name

            # Create a unique bin name using timestamp and random suffix
            timestamp = int(time.time())
            suffix = "".join(
                random.choices(string.ascii_lowercase + string.digits, k=6)
            )
            bin_name = f"twat-fs-{timestamp}-{suffix}"
            bin_url = f"{self.url}/{bin_name}"

            # Upload the file directly to the bin URL
            file_url = f"{bin_url}/{filename}"
            headers = {
                "Content-Type": "application/octet-stream",
                "User-Agent": "twat-fs/1.0",
            }

            # Upload with retries
            max_retries = 3
            retry_delay = 2
            last_error = None

            for attempt in range(max_retries):
                try:
                    response = requests.put(
                        file_url,
                        data=file,
                        headers=headers,
                        timeout=30,
                    )
                    if response.status_code in (200, 201, 204):
                        logger.debug(
                            f"Successfully uploaded to filebin.net: {file_url}"
                        )
                        return UploadResult(
                            url=str(file_url),
                            metadata={
                                "provider": "filebin",
                                "success": True,
                                "raw_response": response.text,
                            },
                        )

                    last_error = f"Upload failed with status {response.status_code}: {response.text}"
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        file.seek(0)  # Reset file pointer for retry
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
            logger.error(f"Failed to upload to filebin.net: {e}")
            return UploadResult(
                url="",
                metadata={
                    "provider": "filebin",
                    "success": False,
                    "error": str(e),
                },
            )

    @classmethod
    def get_credentials(cls) -> None:
        """Simple providers don't need credentials"""
        return None

    @classmethod
    def get_provider(cls) -> ProviderClient | None:
        """Initialize and return the provider client."""
        return cast(ProviderClient, cls())


# Module-level functions to implement the Provider protocol
def get_credentials() -> None:
    """Simple providers don't need credentials"""
    return None


def get_provider() -> ProviderClient | None:
    """Return an instance of the provider"""
    return FilebinProvider.get_provider()


def upload_file(
    local_path: str | Path, remote_path: str | Path | None = None
) -> UploadResult:
    """
    Upload a file and return its URL.

    Args:
        local_path: Path to the file to upload
        remote_path: Optional remote path (ignored for simple providers)

    Returns:
        UploadResult: URL of the uploaded file
    """
    provider = get_provider()
    if not provider:
        msg = "Failed to initialize provider"
        raise ValueError(msg)
    return provider.upload_file(local_path, remote_path)
