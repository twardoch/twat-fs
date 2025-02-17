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
from typing import Any, Protocol, runtime_checkable, BinaryIO
from collections.abc import Generator


from . import ProviderHelp


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


class SimpleProviderBase(ABC):
    """Base class for simple upload providers"""

    PROVIDER_HELP: ProviderHelp = {
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
    def get_provider(cls) -> SimpleProviderClient:
        """Return an instance of this provider"""
        return cls()  # type: ignore

    def upload_file(
        self, local_path: str | Path, remote_path: str | Path | None = None
    ) -> str:
        """
        Upload a file and return its URL.
        Implements the ProviderClient interface by wrapping the async upload_file method.

        Args:
            local_path: Path to the file to upload
            remote_path: Ignored for simple providers

        Returns:
            str: URL to the uploaded file

        Raises:
            ValueError: If upload fails
        """
        import asyncio

        file_path = Path(local_path)
        self._validate_file(file_path)

        result = asyncio.run(self.async_upload_file(file_path))
        if not result.success:
            msg = f"Upload failed: {result.error}"
            raise ValueError(msg)
        return result.url

    @abstractmethod
    async def async_upload_file(self, file_path: Path) -> UploadResult:
        """
        Async method to upload a file. Must be implemented by subclasses.

        Args:
            file_path: Path to the file to upload

        Returns:
            UploadResult containing the URL and status
        """
