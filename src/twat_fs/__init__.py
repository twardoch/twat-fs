# this_file: src/twat_fs/__init__.py

"""twat-fs: File system utilities for twat."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("twat-fs")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

try:
    import twat_cache
    from twat_fs.paths import get_cache_dir

    # Configure twat_cache to use the paths from twat_os
    # Use the correct API to set the cache directory
    twat_cache.utils.get_cache_path = lambda *_, **__: get_cache_dir()
except ImportError:
    pass  # twat_cache is not installed, no configuration needed

from twat_fs.cli import main, setup_provider, setup_providers, upload_file
from twat_fs.exceptions import (
    FileValidationError,
    ProviderAuthError,
    ProviderConfigError,
    ProviderError,
    ProviderUnavailableError,
    TwatFsError,
)
from twat_fs.upload import PROVIDERS_PREFERENCE, ProviderType

__all__ = [
    "PROVIDERS_PREFERENCE",
    "FileValidationError",
    "ProviderAuthError",
    "ProviderConfigError",
    "ProviderError",
    "ProviderType",
    "ProviderUnavailableError",
    "TwatFsError",
    "__version__",
    "main",
    "setup_provider",
    "setup_providers",
    "upload_file",
]
