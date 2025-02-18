#!/usr/bin/env -S uv run
# /// script
# dependencies = ["fire", "loguru", "rich"]
# ///
# this_file: src/twat_fs/cli.py

"""
Command-line interface for twat-fs package.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NoReturn

import fire
from loguru import logger
from rich.console import Console

from twat_fs.upload import (
    PROVIDERS_PREFERENCE,
    ProviderStatus,
    setup_provider as _setup_provider,
    setup_providers as _setup_providers,
    upload_file as _upload_file,
)

# Configure logging: errors and warnings to stderr, provider info to stdout
logger.remove()  # Remove default handler
log_level = os.getenv("LOGURU_LEVEL", "INFO").upper()

# All warnings and errors go to stderr
logger.add(
    sys.stderr,
    level="WARNING",
    format="<red>Error: {message}</red>",
)

# Info and debug messages go to stdout, but only for non-error records
logger.add(
    sys.stdout,
    level=log_level,
    format="{message}",
    filter=lambda record: record["level"].no < logger.level("WARNING").no,
)


def parse_provider_list(provider: str) -> list[str] | None:
    """Parse a provider list string like '[s3,dropbox]' into a list."""
    if provider.startswith("[") and provider.endswith("]"):
        try:
            return [p.strip() for p in provider[1:-1].split(",")]
        except Exception:
            return None
    return None


class UploadProviderCommands:
    """Commands for managing upload providers."""

    def status(self, provider_id: str | None = None, online: bool = False) -> NoReturn:
        """
        Show status information for a specific provider or all providers.

        Args:
            provider_id: Optional provider ID to show status info for.
                       If not provided, shows info for all providers.
            online: If True, performs an online test by uploading and downloading a small file.
        """
        console = Console(stderr=True)  # Use stderr for error messages

        if provider_id:
            # For a specific provider, print only the provider ID to stdout if it's ready
            result = _setup_provider(provider_id, verbose=True, online=online)
            if result.status == ProviderStatus.READY:
                sys.exit(0)
            else:
                console.print(
                    f"\n[red]Error:[/red] Provider '{provider_id}' is not ready"
                )
                console.print(f"[red]Reason:[/red] {result.message}")
                if result.details:
                    console.print("\n[yellow]Setup Instructions:[/yellow]")
                    console.print(result.details)
                sys.exit(1)  # Provider not ready
        else:
            # For all providers, show detailed status info
            _setup_providers(verbose=True, online=online)
            sys.exit(0)

    def list(self, online: bool = False) -> None:
        """List all available (ready) provider IDs, one per line. If --online is provided, run online tests.
        In online mode, reconfigure logger so that info messages are printed to stderr."""
        if online:
            # Reconfigure logger to send all info messages to stderr
            logger.remove()
            logger.add(sys.stderr, level="INFO", format="{message}")

        active_providers = []

        for provider in PROVIDERS_PREFERENCE:
            if provider.lower() == "simple":
                continue  # Skip the base provider
            result = _setup_provider(provider, verbose=False, online=online)
            if result.status == ProviderStatus.READY:
                active_providers.append(provider)

        # Print each active provider ID, one per line, to stdout
        for provider in active_providers:
            print(provider)

        sys.exit(0)


class TwatFS:
    """
    A robust and extensible file upload utility with support for multiple storage providers.

    Commands:
        upload              Upload a file using configured providers
        upload_provider    Manage upload providers (status, list)
    """

    def __init__(self) -> None:
        self.upload_provider = UploadProviderCommands()

    def upload(
        self,
        file_path: str | Path,
        provider: str | list[str] = PROVIDERS_PREFERENCE,
        unique: bool = False,
        force: bool = False,
        remote_path: str | None = None,
    ) -> str:
        """
        Upload a file using the specified provider(s) with automatic fallback.

        Args:
            file_path: Path to the file to upload
            provider: Provider(s) to use for upload. Can be a single provider or a list
            unique: Add timestamp to filename to ensure uniqueness
            force: Overwrite existing files if they exist
            remote_path: Custom remote path/prefix (provider-specific)

        Returns:
            URL of the uploaded file
        """
        try:
            # Handle provider list passed as string
            if isinstance(provider, str):
                providers = parse_provider_list(provider)
                if providers is not None:
                    provider = providers

            # Verify file exists
            if not Path(file_path).exists():
                logger.error(f"File not found: {file_path}")
                sys.exit(1)

            url = _upload_file(
                file_path,
                provider=provider,
                unique=unique,
                force=force,
                upload_path=remote_path,
            )
            return url
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            sys.exit(1)


def main() -> None:
    """Entry point for the CLI."""
    if __name__ == "__main__":
        fire.Fire(TwatFS)
    else:
        # When imported as a module
        fire.Fire(TwatFS())


# Backwards compatibility for the API
upload_file = TwatFS().upload
setup_provider = TwatFS().upload_provider.status


def setup_providers():
    return TwatFS().upload_provider.status(None)


if __name__ == "__main__":
    main()
