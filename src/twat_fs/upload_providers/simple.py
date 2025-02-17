#!/usr/bin/env python
# /// script
# dependencies = []
# ///
# this_file: src/twat_fs/upload_providers/simple.py

"""
Base implementation for simple file upload providers like termbin, 0x0.st etc.
These providers typically just upload a file and return a URL, without auth or complex configuration.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable, BinaryIO, ClassVar
from collections.abc import Generator

from . import ProviderHelp, Provider, ProviderClient


@dataclass
class UploadResult:
    """Result of a file upload operation"""

    url: str
    success: bool
    error: str | None = None
    raw_response: Any = None


@runtime_checkable
class SimpleProviderClient(Protocol):
    """Protocol for simple upload providers that just take a file and return a URL"""

    async def upload_file(self, file_path: Path) -> UploadResult:
        """Upload a file and return the result

        Args:
            file_path: Path to the file to upload

        Returns:
            UploadResult containing the URL and status
        """
        ...


class SimpleProviderBase(ABC, Provider):
    """Base class for simple upload providers"""

    # Class variable for provider help
    PROVIDER_HELP: ClassVar[ProviderHelp] = {
        "setup": "No setup required",
        "deps": "No additional dependencies required",
    }

    @contextmanager
    def _open_file(self, file_path: Path) -> Generator[BinaryIO, None, None]:
        """Safely open and close a file"""
        file = None
        try:
            file = open(file_path, "rb")
            yield file
        finally:
            if file:
                file.close()

    def _validate_file(self, file_path: Path) -> None:
        """Validate that a file exists and is readable"""
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)
        if not file_path.is_file():
            msg = f"Not a file: {file_path}"
            raise ValueError(msg)
        if not os.access(file_path, os.R_OK):
            msg = f"Cannot read file: {file_path}"
            raise PermissionError(msg)

    @classmethod
    def get_credentials(cls) -> None:
        """Simple providers don't need credentials"""
        return None

    @classmethod
    def get_provider(cls) -> ProviderClient | None:
        """Return an instance of this provider"""
        return cls()

    def upload_file(
        self, local_path: str | Path, remote_path: str | Path | None = None
    ) -> str:
        """
        Upload a file and return its URL.
        Implements the ProviderClient interface by wrapping the async upload_file method.

        Args:
            local_path: Path to the file to upload
            remote_path: Optional remote path to use (ignored for simple providers)

        Returns:
            str: URL to the uploaded file

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the path is not a file
            PermissionError: If the file can't be read
            RuntimeError: If the upload fails
        """
        path = Path(local_path)
        self._validate_file(path)

        with self._open_file(path) as file:
            result = self.upload_file_impl(file)
            if not result.success:
                msg = f"Upload failed: {result.error or 'Unknown error'}"
                raise RuntimeError(msg)
            return result.url

    @abstractmethod
    def upload_file_impl(self, file: BinaryIO) -> UploadResult:
        """
        Implement the actual file upload logic.
        This method should be implemented by concrete provider classes.

        Args:
            file: Open file handle to upload

        Returns:
            UploadResult containing the URL and status
        """
        ...
