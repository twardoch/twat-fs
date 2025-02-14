#!/usr/bin/env -S uv run
# this_file: src/twat_fs/__init__.py

"""
twat-fs package - File system utilities for twat.
"""

from importlib import metadata
from twat_fs.upload import upload_file, ProviderType

__version__ = metadata.version(__name__)
__all__ = ["ProviderType", "upload_file"]
