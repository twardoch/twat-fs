#!/usr/bin/env python
# /// script
# dependencies = ["fire"]

"""
Command-line interface for twat-fs package.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import fire
from loguru import logger

from twat_fs.upload import (
    PROVIDERS_PREFERENCE,
    setup_provider as _setup_provider,
    setup_providers as _setup_providers,
    upload_file as _upload_file,
)

# Configure logging
logger.remove()  # Remove default handler
log_level = os.getenv("LOGURU_LEVEL", "INFO").upper()  # Default to INFO if not set
logger.add(sys.stderr, level=log_level)


class TwatFS:
    """
    A robust and extensible file upload utility with support for multiple storage providers.

    This CLI tool provides a unified interface for uploading files to various storage services,
    from simple providers like 0x0 and uguu to advanced services like s3 and dropbox.
    Key features include:

    * Provider Flexibility: Seamlessly switch between storage providers
    * Fault Tolerance: Graceful fallback between providers if primary fails
    * Progressive Enhancement: Start simple (no config needed) and scale up as needed
    * Multiple Provider Support: s3, dropbox, fal, and several simple providers
    * Comprehensive Setup Tools: Easy provider configuration and status checks

    Configuration:
    Advanced providers require environment variables:
    * s3: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET
    * dropbox: DROPBOX_ACCESS_TOKEN
    * fal: FAL_KEY

    Logging Configuration:
    Set LOGURU_LEVEL environment variable to control logging:
    * DEBUG: Detailed debugging information
    * INFO: General operational information (default)
    * WARNING: Warning messages only
    * ERROR: Error messages only

    Basic usage:
        twat-fs upload path/to/file.txt                     # Uses default provider
        twat-fs upload --provider s3 path/to/file.txt       # Uses specific provider
        twat-fs upload --provider "[s3,dropbox]" file.txt   # Try providers in order
        twat-fs setup provider s3                           # Check s3 configuration
        twat-fs setup all                                   # Check all providers
    """

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

        This command supports both simple and advanced upload scenarios. When multiple
        providers are specified, it will try them in order until successful.

        Args:
            file_path: Path to the file to upload
            provider: Provider(s) to use for upload: `s3`, `dropbox`, `fal`, `0x0`, `uguu`, `catbox`, `litterbox`, `bashupload`, `termbin` or multiple: `[s3,dropbox]`, Default: Uses provider preference order
            unique: Add timestamp to filename to ensure uniqueness
            force: Overwrite existing files if they exist
            remote_path: Custom remote path/prefix (provider-specific):
                        - S3: Bucket prefix
                        - Dropbox: Folder path
                        - Simple providers: Ignored

        Returns:
            URL of the uploaded file

        Examples:
            # Simple upload with default provider
            twat-fs upload image.png

            # Upload to S3 with custom path
            twat-fs upload data.csv --provider s3 --remote-path "data/2024/"

            # Try multiple providers with unique filename
            twat-fs upload log.txt --provider "[s3,dropbox]" --unique

            # Force upload to specific provider
            twat-fs upload config.json --provider dropbox --force
        """
        logger.debug(f"Upload requested for file: {file_path}")
        logger.debug(f"Provider argument type: {type(provider)}, value: {provider}")
        logger.debug(
            f"Upload options: unique={unique}, force={force}, remote_path={remote_path}"
        )

        if isinstance(provider, str):
            # Support a provider list passed as a string, e.g. "[s3,dropbox]"
            if provider.startswith("[") and provider.endswith("]"):
                try:
                    providers = [p.strip() for p in provider[1:-1].split(",")]
                    logger.debug(f"Parsed provider list: {providers}")
                    return _upload_file(
                        file_path,
                        provider=providers,
                        unique=unique,
                        force=force,
                        upload_path=remote_path,
                    )
                except Exception as e:
                    logger.error(f"Invalid provider list format: {e}")
                    msg = f"Invalid provider list format: {provider}"
                    raise ValueError(msg) from e
            logger.debug(f"Using single provider: {provider}")
            try:
                return _upload_file(
                    file_path,
                    provider=provider,
                    unique=unique,
                    force=force,
                    upload_path=remote_path,
                )
            except Exception as e:
                logger.error(f"Upload failed with provider {provider}: {e}")
                msg = f"Upload failed with provider {provider}: {e}"
                raise ValueError(msg) from e

        logger.debug(f"Using provider(s): {provider}")
        return _upload_file(
            file_path,
            provider=provider,
            unique=unique,
            force=force,
            upload_path=remote_path,
        )

    class _SetupFS:
        """
        Provider setup and configuration management commands.

        These commands help you:
        * Verify provider credentials and configurations
        * Test actual connectivity to provider services
        * View detailed setup requirements for each provider
        * Diagnose configuration issues with helpful messages
        * Get provider-specific troubleshooting guidance

        Available providers include:

        Simple Providers (no setup required):
            0x0             General file uploads
            uguu            Temporary file uploads (24h)
            termbin        Text-only uploads
            bashupload     General file uploads

        Advanced Providers (requires configuration):
            s3             Enterprise-grade storage (AWS)
            dropbox        Cloud storage integration
            fal            AI-powered file hosting

        Commands:
            setup provider <name>    Check specific provider:
                                    - Verifies environment variables
                                    - Tests API connectivity
                                    - Shows detailed status

            setup all               Check all providers:
                                   - Shows setup status overview
                                   - Identifies missing configurations
                                   - Lists available providers
        """

        def provider(self, provider: str) -> tuple[bool, str]:
            """
            Check setup status for a specific provider.

            Args:
                provider: Provider to check (s3, dropbox, fal).

            Returns:
                A tuple (success, explanation).
            """
            return _setup_provider(provider)

        def all(self) -> dict[str, tuple[bool, str]]:
            """
            Check setup status for all available providers.

            Returns:
                A dict mapping provider names to (success, explanation) tuples.
            """
            return _setup_providers()

    # Expose the setup commands as a subcommand.
    setup = _SetupFS()


def main() -> None:
    fire.Fire(TwatFS)


# Backwards compatibility for the API:
# These names are still exported for external imports.
upload_file = TwatFS().upload
setup_provider = TwatFS().setup.provider
setup_providers = TwatFS().setup.all
