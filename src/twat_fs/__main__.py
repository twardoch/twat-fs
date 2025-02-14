#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "fire",
# ]
# ///
# this_file: src/twat_fs/__main__.py

"""
Command-line interface for twat-fs package.
"""

from pathlib import Path

import fire

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
        provider: Name of the provider to use

    Returns:
        str: URL of the uploaded file
    """
    return _upload_file(file_path, provider)


def setup_provider(provider: ProviderType) -> tuple[bool, str]:
    """
    Check setup status for a specific provider.

    Args:
        provider: Name of the provider to check

    Returns:
        Tuple[bool, str]: (success, explanation)
        - If provider is working: (True, success message)
        - If provider needs setup: (False, setup instructions)
    """
    return _setup_provider(provider)


def setup_providers() -> dict[str, tuple[bool, str]]:
    """
    Check setup status for all available providers.

    Returns:
        Dict[str, Tuple[bool, str]]: Status and explanation for each provider
    """
    return _setup_providers()


def main():
    """Entry point for the CLI."""
    fire.Fire(
        {
            "upload": upload_file,
            "setup": {
                "provider": setup_provider,
                "all": setup_providers,
            },
        }
    )


if __name__ == "__main__":
    main()
