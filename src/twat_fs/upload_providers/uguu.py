# this_file: src/twat_fs/upload_providers/uguu.py

"""
Uguu.se upload provider.
A simple provider that uploads files to uguu.se.
Files are automatically deleted after 48 hours.
"""

from typing import Any, cast
from twat_fs.upload_providers.types import UploadResult
import requests
from pathlib import Path
from typing import BinaryIO, ClassVar

from loguru import logger

from twat_fs.upload_providers.simple import BaseProvider

from twat_fs.upload_providers.protocols import ProviderHelp, ProviderClient

# Provider help messages
PROVIDER_HELP: ProviderHelp = {
    "setup": "No setup required. Note: Files are deleted after 48 hours.",
    "deps": "Python package: requests",
}


class UguuProvider(BaseProvider):
    """Provider for uguu.se uploads"""

    PROVIDER_HELP: ClassVar[ProviderHelp] = PROVIDER_HELP
    provider_name: str = "uguu"

    def __init__(self) -> None:
        super().__init__()
        self.url = "https://uguu.se/upload.php"

    def upload_file_impl(self, file: BinaryIO) -> UploadResult:
        """
        Upload file to uguu.se

        Args:
            file: Open file handle to upload

        Returns:
            UploadResult containing the URL and status

        Raises:
            RetryableError: For temporary failures that can be retried
            NonRetryableError: For permanent failures
        """
        try:
            files = {"files[]": file}
            response = requests.post(self.url, files=files, timeout=30)

            if response.status_code == 429:  # Rate limit
                msg = f"Rate limited: {response.text}"
                raise RetryableError(msg, "uguu")
            elif response.status_code != 200:
                msg = (
                    f"Upload failed with status {response.status_code}: {response.text}"
                )
                raise NonRetryableError(msg, "uguu")

            result = response.json()
            if not result or "files" not in result:
                msg = f"Invalid response from uguu.se: {result}"
                raise NonRetryableError(msg, "uguu")

            url = result["files"][0]["url"]
            logger.debug(f"Successfully uploaded to uguu.se: {url}")

            return UploadResult(
                url=url,
                metadata={
                    "provider": "uguu",
                    "success": True,
                    "raw_response": result,
                },
            )

        except requests.Timeout as e:
            msg = f"Upload timed out: {e}"
            raise RetryableError(msg, "uguu") from e
        except requests.ConnectionError as e:
            msg = f"Connection error: {e}"
            raise RetryableError(msg, "uguu") from e
        except (ValueError, NonRetryableError, RetryableError) as e:
            raise e
        except Exception as e:
            msg = f"Upload failed: {e}"
            return UploadResult(
                url="",
                metadata={
                    "provider": "uguu",
                    "success": False,
                    "error": str(e),
                },
            )

    @classmethod
    def get_credentials(cls) -> dict[str, Any] | None:
        """Simple providers don't need credentials"""
        return None

    @classmethod
    def get_provider(cls) -> ProviderClient | None:
        """Initialize and return the provider client."""
        return cast(ProviderClient, cls())


# Module-level functions to implement the Provider protocol
def get_credentials() -> dict[str, Any] | None:
    """Simple providers don't need credentials"""
    return UguuProvider.get_credentials()


def get_provider() -> ProviderClient | None:
    """Return an instance of the provider"""
    return UguuProvider.get_provider()


def upload_file(
    local_path: str | Path,
    remote_path: str | Path | None = None,
) -> UploadResult:
    """
    Upload a file and return convert_to_upload_result(its URL.

    Args:
        local_path: Path to the file to upload)
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
