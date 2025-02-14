#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "fire",
# ]
# ///
# this_file: src/twat_fs/__main__.py

"""
Command-line interface for twat-fs package.

Usage:
    twat-fs upload FILE [--provider PROVIDER]
    twat-fs setup provider PROVIDER
    twat-fs setup all

Commands:
    upload      Upload a file using the specified provider
    setup       Check provider setup and configuration

Examples:
    # Upload a file using default provider
    twat-fs upload path/to/file.txt

    # Upload using specific provider
    twat-fs upload path/to/file.txt --provider s3

    # Check provider setup
    twat-fs setup provider s3
    twat-fs setup all
"""

import sys
from pathlib import Path
from typing import NoReturn

import fire
from loguru import logger

from twat_fs.upload import (
    upload_file as _upload_file,
    setup_provider as _setup_provider,
    setup_providers as _setup_providers,
    ProviderType,
    PROVIDERS_PREFERENCE,
)


def upload_file(
    file_path: str | Path,
    provider: ProviderType | list[ProviderType] | None = PROVIDERS_PREFERENCE,
) -> str:
    """
    Upload a file using the specified provider.

    Args:
        file_path: Path to the file to upload
        provider: Provider to use (s3, dropbox, fal) or list of providers to try in order
                 Default: Try providers in order of preference

    Returns:
        str: URL of the uploaded file

    Example:
        twat-fs upload path/to/file.txt
        twat-fs upload path/to/file.txt --provider s3
        twat-fs upload path/to/file.txt --provider "[s3,dropbox,fal]"
    """
    return _upload_file(file_path, provider)


def setup_provider(provider: ProviderType) -> tuple[bool, str]:
    """
    Check setup status for a specific provider.

    Args:
        provider: Provider to check (s3, dropbox, fal)

    Returns:
        Tuple[bool, str]: (success, explanation)
        - If provider is working: (True, success message)
        - If provider needs setup: (False, setup instructions)

    Example:
        twat-fs setup provider s3
        twat-fs setup provider dropbox
    """
    return _setup_provider(provider)


def setup_providers() -> dict[str, tuple[bool, str]]:
    """
    Check setup status for all available providers.

    Returns:
        Dict[str, Tuple[bool, str]]: Status and explanation for each provider

    Example:
        twat-fs setup all
    """
    return _setup_providers()


def show_help() -> NoReturn:
    """Show help message and exit."""
    print(__doc__)
    sys.exit(0)


def main() -> None:
    """Entry point for the CLI."""
    if len(sys.argv) == 1 or "--help" in sys.argv or "-h" in sys.argv:
        show_help()

    commands = {
        "upload": upload_file,
        "setup": {
            "provider": setup_provider,
            "all": setup_providers,
        },
    }

    try:
        fire.Fire(commands)
    except KeyboardInterrupt:
        logger.warning("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
