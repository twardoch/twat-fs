#!/usr/bin/env python
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

from __future__ import annotations

import os
from pathlib import Path

import fal_client
from loguru import logger

# Provider-specific help messages
PROVIDER_HELP = {
    "setup": """To use FAL storage:
1. Create a FAL account at https://fal.ai
2. Generate an API key from your account settings
3. Set the following environment variable:
   - FAL_KEY: Your FAL API key""",
    "deps": """Additional setup needed:
1. Install the FAL client: pip install fal-client
2. Ensure your API key has the necessary permissions""",
}


def get_credentials() -> str | None:
    """Get FAL credentials from environment."""
    return os.getenv("FAL_KEY")


def get_provider():
    """
    Initialize and return the FAL provider if credentials are present.
    """
    key = get_credentials()
    if not key:
        logger.debug("FAL_KEY not set in environment")
        return None

    try:
        # Create a client instance with the key
        return fal_client.SyncClient(key=key)

    except Exception as err:
        logger.warning(f"Failed to initialize FAL provider: {err}")
        return None


def upload_file(local_path: str | Path, remote_path: str | Path | None = None) -> str:
    """
    Upload a file using FAL.

    Args:
        local_path: Path to the file to upload
        remote_path: Optional remote path (ignored for FAL)

    Returns:
        str: URL to the uploaded file

    Raises:
        ValueError: If upload fails
    """
    try:
        client = get_provider()
        if not client:
            msg = "FAL provider not initialized"
            raise ValueError(msg)

        # Convert to Path object and use only the local path
        path = Path(local_path)
        result = client.upload_file(str(path))  # FAL client expects a string path
        if not result:
            msg = "FAL upload failed - no URL in response"
            raise ValueError(msg)
        return result

    except Exception as e:
        logger.warning(f"FAL upload failed: {e}")
        msg = "FAL upload failed"
        raise ValueError(msg) from e
