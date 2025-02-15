#!/usr/bin/env python
# /// script
# dependencies = [
#   "fire",
# ]
# ///
# this_file: src/twat_fs/cli.py

"""
Command-line interface for twat-fs package.
"""

import sys
import os
from pathlib import Path
from typing import NoReturn

import fire
from loguru import logger

# Configure logging before other imports
logger.remove()  # Remove default handler
log_level = os.getenv("LOGURU_LEVEL", "INFO").upper()  # Default to INFO if not set
logger.add(sys.stderr, level=log_level)

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
    unique: bool = False,
    force: bool = False,
    upload_path: str | None = None,
) -> str:
    """
    Upload a file using the specified provider.

    Args:
        file_path: Path to the file to upload
        provider: Provider to use (s3, dropbox, fal) or list of providers to try in order
                 Default: Try providers in order of preference
        unique: Whether to ensure unique filenames by adding a timestamp
        force: Whether to overwrite existing files
        upload_path: Custom base upload path (provider-specific)

    Returns:
        str: URL of the uploaded file

    Example:
        twat-fs upload path/to/file.txt
        twat-fs upload path/to/file.txt --provider s3
        twat-fs upload path/to/file.txt --provider dropbox --unique
        twat-fs upload path/to/file.txt --provider dropbox --force
        twat-fs upload path/to/file.txt --provider "[s3,dropbox,fal]"
    """
    logger.debug(f"Upload requested for file: {file_path}")
    logger.debug(f"Provider argument type: {type(provider)}, value: {provider}")
    logger.debug(
        f"Upload options: unique={unique}, force={force}, upload_path={upload_path}"
    )

    # Handle provider argument properly
    if isinstance(provider, str):
        # If it's a string in list format, parse it
        if provider.startswith("[") and provider.endswith("]"):
            try:
                # Strip brackets and split by comma
                providers = [p.strip() for p in provider[1:-1].split(",")]
                logger.debug(f"Parsed provider list: {providers}")
                return _upload_file(
                    file_path,
                    provider=providers,
                    unique=unique,
                    force=force,
                    upload_path=upload_path,
                )
            except Exception as e:
                logger.error(f"Invalid provider list format: {e}")
                raise ValueError(f"Invalid provider list format: {provider}") from e
        # Otherwise, use it as a single provider
        logger.debug(f"Using single provider: {provider}")
        try:
            return _upload_file(
                file_path,
                provider=provider,
                unique=unique,
                force=force,
                upload_path=upload_path,
            )
        except Exception as e:
            # When a specific provider is requested, don't fall back to others
            logger.error(f"Upload failed with provider {provider}: {e}")
            raise ValueError(f"Upload failed with provider {provider}: {e}") from e

    # For other cases (None or list), pass through
    logger.debug(f"Using provider(s): {provider}")
    return _upload_file(
        file_path,
        provider=provider,
        unique=unique,
        force=force,
        upload_path=upload_path,
    )


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
