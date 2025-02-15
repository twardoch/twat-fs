#!/usr/bin/env -S uv run
# this_file: src/twat_fs/__init__.py

"""
twat-fs package - File system utilities for twat.
"""

from importlib import metadata

from twat_fs.cli import main, setup_provider, setup_providers, upload_file
from twat_fs.upload import ProviderType, PROVIDERS_PREFERENCE

__version__ = metadata.version(__name__)

__all__ = [
    "main",
    "upload_file",
    "setup_provider",
    "setup_providers",
    "ProviderType",
    "PROVIDERS_PREFERENCE",
]
