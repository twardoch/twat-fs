#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "fal-client",
#   "loguru",
# ]
# ///
# this_file: src/twat_fs/upload_providers/fal.py

"""
FAL provider for file uploads.
This module provides functionality to upload files to FAL's storage service.
"""

import os
from pathlib import Path
from loguru import logger


def get_credentials() -> str | None:
    """
    Get FAL credentials from environment variables.
    This function only checks environment variables and returns them,
    without importing or initializing any external dependencies.

    Returns:
        Optional[str]: FAL API key if present, None otherwise
    """
    key = os.getenv("FAL_KEY")
    if not key:
        logger.debug("FAL_KEY environment variable is not set")
        return None
    return key


def get_provider(credentials: str | None = None):
    """
    Initialize and return the FAL provider client.
    This function handles importing dependencies and creating the client.

    Args:
        credentials: Optional FAL API key to use. If None, will call get_credentials()

    Returns:
        Any: FAL client if successful, None otherwise
    """
    if credentials is None:
        credentials = get_credentials()

    if not credentials:
        return None

    try:
        import fal_client

        # Initialize client with credentials
        fal_client.set_key(credentials)

        # Test connection
        fal_client.status()

        return fal_client

    except Exception as e:
        logger.warning(f"Failed to initialize FAL provider: {e}")
        return None


def _validate_file(local_path: Path) -> None:
    """
    Validate file exists and can be read.

    Args:
        local_path: Path to the file to validate

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If path is not a file
        PermissionError: If file cannot be read
    """
    if not local_path.exists():
        msg = f"File not found: {local_path}"
        raise FileNotFoundError(msg)

    if not local_path.is_file():
        msg = f"Path is not a file: {local_path}"
        raise ValueError(msg)

    try:
        # Test if file can be read
        with open(local_path, "rb") as f:
            f.read(1)
    except PermissionError:
        msg = f"Permission denied: {local_path}"
        raise PermissionError(msg)
    except Exception as e:
        msg = f"Error validating file: {e}"
        raise ValueError(msg)


def upload_file(file_path: str | Path, remote_path: str | Path | None = None) -> str:
    """
    Upload a file to FAL storage and return its URL.

    Args:
        file_path: Path to the file to upload (str or Path)
        remote_path: Optional remote path (ignored for FAL provider)

    Returns:
        str: URL of the uploaded file

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If path is not a file or FAL_KEY is not set
        PermissionError: If file cannot be read
    """
    if not get_provider():
        msg = "FAL_KEY environment variable must be set"
        raise ValueError(msg)

    path = Path(file_path)
    _validate_file(path)

    try:
        # remote_path is ignored for FAL provider as it uses its own path handling
        return get_provider().upload_file(str(path))
    except Exception as e:
        logger.error(f"Failed to upload file to FAL: {e}")
        msg = f"Upload failed: {e}"
        raise ValueError(msg)
