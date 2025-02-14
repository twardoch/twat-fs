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
import fal_client
from pathlib import Path
from loguru import logger


def provider_auth() -> bool:
    """
    Check if FAL provider is properly authenticated.

    Returns:
        bool: True if FAL_KEY environment variable is set, False otherwise
    """
    has_key = bool(os.getenv("FAL_KEY"))
    if not has_key:
        logger.warning("FAL_KEY environment variable is not set")
    return has_key


def upload_file(file_path: str | Path) -> str:
    """
    Upload a file to FAL storage and return its URL.

    Args:
        file_path: Path to the file to upload (str or Path)

    Returns:
        str: URL of the uploaded file

    Raises:
        Exception: If upload fails or FAL_KEY is not set
    """
    if not provider_auth():
        msg = "FAL_KEY environment variable must be set"
        raise ValueError(msg)

    url = fal_client.upload_file(str(file_path))
    return url
