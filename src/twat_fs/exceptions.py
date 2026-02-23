#!/usr/bin/env python3
# this_file: src/twat_fs/exceptions.py

"""
Custom exceptions for twat-fs.

Provides a structured exception hierarchy rooted at TwatFsError,
which extends the ecosystem-wide TwatError base class.

Hierarchy::

    TwatError (twat.common.exceptions or fallback)
    └── TwatFsError
        ├── ProviderError
        │   ├── ProviderConfigError
        │   ├── ProviderAuthError
        │   └── ProviderUnavailableError
        ├── FileValidationError
        └── UploadError  (defined in upload_providers/core.py)
            ├── RetryableError
            └── NonRetryableError
"""

from __future__ import annotations


try:
    from twat.common.exceptions import TwatError
except ImportError:

    class TwatError(Exception):  # type: ignore[no-redef]
        """Fallback base when twat host package is not installed."""

        def __init__(
            self, message: str = "", *, context: dict[str, object] | None = None, cause: Exception | None = None
        ) -> None:
            super().__init__(message)
            self.context = context or {}
            if cause is not None:
                self.__cause__ = cause


class TwatFsError(TwatError):
    """Base exception for all twat-fs errors."""


class ProviderError(TwatFsError):
    """Error related to an upload provider."""

    def __init__(self, message: str = "", *, provider: str | None = None) -> None:
        super().__init__(message)
        self.provider = provider


class ProviderConfigError(ProviderError):
    """Provider is misconfigured (e.g., missing env vars, bad settings)."""


class ProviderAuthError(ProviderError):
    """Provider authentication failed (e.g., expired token, invalid credentials)."""


class ProviderUnavailableError(ProviderError):
    """Provider is temporarily or permanently unreachable."""


class FileValidationError(TwatFsError):
    """File validation failed (e.g., file not found, too large, wrong type)."""

    def __init__(self, message: str = "", *, file_path: str | None = None) -> None:
        super().__init__(message)
        self.file_path = file_path


__all__ = [
    "FileValidationError",
    "ProviderAuthError",
    "ProviderConfigError",
    "ProviderError",
    "ProviderUnavailableError",
    "TwatError",
    "TwatFsError",
]
