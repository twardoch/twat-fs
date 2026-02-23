#!/usr/bin/env python3
# this_file: src/twat_fs/exceptions.py

"""
Custom exceptions for twat-fs.

Provides a structured exception hierarchy rooted at TwatFsError,
which extends the ecosystem-wide TwatError base class.
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


__all__ = ["TwatError", "TwatFsError"]
