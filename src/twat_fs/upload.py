#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "loguru",
#   "fire",
# ]
# ///
# this_file: src/twat_fs/upload.py

"""
Main upload module that provides a unified interface for uploading files
using different providers.
"""

import importlib
from pathlib import Path
from typing import Literal, Any
from loguru import logger

ProviderType = Literal["fal", "dropbox", "s3"]
PROVIDERS_PREFERENCE = [
    "s3",  # S3 is most reliable, so try it first
    "dropbox",
    "fal",
]

# Provider-specific help messages
PROVIDER_HELP = {
    "s3": {
        "setup": """To use AWS S3 storage:
1. Create an AWS account if you don't have one
2. Create an S3 bucket to store your files
3. Set up AWS credentials by either:
   - Creating an IAM user and setting AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
   - Using AWS CLI: run 'aws configure'
   - Setting up IAM roles if running on AWS infrastructure
4. Set the following environment variables:
   - AWS_S3_BUCKET: Name of your S3 bucket
   - AWS_DEFAULT_REGION: AWS region (e.g. us-east-1)
   Optional:
   - AWS_ENDPOINT_URL: Custom S3 endpoint
   - AWS_S3_PATH_STYLE: Set to 'true' for path-style endpoints
   - AWS_ROLE_ARN: ARN of role to assume""",
        "deps": """Additional setup needed:
1. Install the AWS SDK: pip install boto3
2. If using AWS CLI: pip install awscli
3. Configure AWS credentials using one of the methods above
4. Ensure your IAM user/role has necessary S3 permissions:
   - s3:PutObject
   - s3:GetObject
   - s3:ListBucket""",
    },
    "dropbox": {
        "setup": """To use Dropbox storage:
1. Create a Dropbox account if you don't have one
2. Go to https://www.dropbox.com/developers/apps
3. Create a new app or use an existing one
4. Generate an access token from the app console
5. Set the following environment variables:
   - DROPBOX_ACCESS_TOKEN: Your Dropbox access token
   Optional:
   - DROPBOX_REFRESH_TOKEN: OAuth2 refresh token
   - DROPBOX_APP_KEY: Dropbox app key
   - DROPBOX_APP_SECRET: Dropbox app secret""",
        "deps": """Additional setup needed:
1. Install the Dropbox SDK: pip install dropbox
2. If using OAuth2:
   - Set up your redirect URI in the app console
   - Implement the OAuth2 flow to get refresh tokens""",
    },
    "fal": {
        "setup": """To use FAL storage:
1. Create a FAL account at https://fal.ai
2. Generate an API key from your account settings
3. Set the following environment variable:
   - FAL_KEY: Your FAL API key""",
        "deps": """Additional setup needed:
1. Install the FAL client: pip install fal-client
2. Ensure your API key has the necessary permissions""",
    },
}


def setup_provider(provider: str) -> tuple[bool, str]:
    """
    Check a provider's setup status and return instructions if needed.

    Args:
        provider: Name of the provider to check

    Returns:
        Tuple[bool, str]: (success, explanation)
        - If provider is fully working: (True, "You can upload files to: {provider}")
        - If credentials exist but setup needed: (False, detailed setup instructions)
        - If no credentials: (False, complete setup guide including credentials)
    """
    try:
        # Import provider module
        provider_module = _get_provider_module(provider)
        if not provider_module:
            return (
                False,
                f"Provider '{provider}' is not available.\n\n{PROVIDER_HELP[provider]['setup']}",
            )

        # Check credentials
        credentials = provider_module.get_credentials()
        if not credentials:
            return False, (
                f"Provider '{provider}' is not configured. "
                f"Please set up the required credentials:\n\n{PROVIDER_HELP[provider]['setup']}"
            )

        # Try to get provider client
        if client := provider_module.get_provider():
            return True, f"You can upload files to: {provider}"

        # If we have credentials but client init failed, probably missing dependencies
        return False, (
            f"Provider '{provider}' has credentials but additional setup is needed:\n\n"
            f"{PROVIDER_HELP[provider]['deps']}"
        )

    except Exception as e:
        logger.warning(f"Error checking provider {provider}: {e}")
        return False, (
            f"Provider '{provider}' encountered an error: {e!s}\n\n"
            f"Complete setup guide:\n{PROVIDER_HELP[provider]['setup']}\n\n"
            f"{PROVIDER_HELP[provider]['deps']}"
        )


def setup_providers() -> dict[str, tuple[bool, str]]:
    """
    Check setup status for all available providers.

    Returns:
        Dict[str, Tuple[bool, str]]: Dictionary mapping provider names to their setup status and explanation
    """
    results = {}
    for provider in PROVIDERS_PREFERENCE:
        success, explanation = setup_provider(provider)
        results[provider] = (success, explanation)

        # Log the result
        if success:
            logger.info(explanation)
        else:
            logger.warning(f"Provider {provider} needs setup:\n{explanation}")

    return results


def _get_provider_module(provider: str):
    """
    Import a provider module dynamically.

    Args:
        provider: Name of the provider to import

    Returns:
        module: The imported provider module or None if import fails
    """
    try:
        return importlib.import_module(f"twat_fs.upload_providers.{provider}")
    except ImportError as e:
        logger.warning(f"Failed to import provider {provider}: {e}")
        return None


def _try_provider(provider: str, file_path: str | Path) -> tuple[bool, str | None]:
    """
    Try to use a specific provider for upload.

    Args:
        provider: Name of the provider to try
        file_path: Path to the file to upload

    Returns:
        tuple[bool, str | None]: (success, url if successful else None)
    """
    try:
        # Import provider module
        provider_module = _get_provider_module(provider)
        if not provider_module:
            return False, None

        # Check if provider has credentials
        if not provider_module.get_credentials():
            logger.debug(f"Provider {provider} has no credentials configured")
            return False, None

        # Get provider client
        client = provider_module.get_provider()
        if not client:
            logger.debug(f"Provider {provider} failed to initialize")
            return False, None

        # Try upload
        url = provider_module.upload_file(file_path)
        return True, url

    except Exception as e:
        logger.warning(f"Provider {provider} failed: {e}")
        return False, None


def get_provider(provider: str | None = None) -> tuple[str | None, Any]:
    """
    Get a provider client by name or try providers in order of preference.

    Args:
        provider: Optional specific provider to use

    Returns:
        tuple[str | None, Any]: Tuple of (provider_name, provider_client) if successful, (None, None) otherwise
    """
    providers_to_try = [provider] if provider else PROVIDERS_PREFERENCE

    for p in providers_to_try:
        try:
            provider_module = _get_provider_module(p)
            if not provider_module:
                continue

            # Check credentials first
            if not provider_module.get_credentials():
                logger.debug(f"Provider {p} has no credentials configured")
                continue

            # Try to get provider client
            if client := provider_module.get_provider():
                logger.info(f"Using provider: {p}")
                return p, client

        except Exception as e:
            logger.warning(f"Failed to initialize provider {p}: {e}")
            continue

    return None, None


def upload_file(
    local_path: str | Path,
    remote_path: str | Path | None = None,
    *,
    provider: str | list[str] | None = None,
) -> str:
    """
    Upload a file using the specified provider(s) or try providers in order of preference.

    Args:
        local_path: Path to the file to upload
        remote_path: Optional remote path to use
        provider: Optional specific provider(s) to use

    Returns:
        str: URL to the uploaded file

    Raises:
        ValueError: If no provider is available or file upload fails
    """
    providers_to_try = (
        [provider]
        if isinstance(provider, str)
        else provider
        if isinstance(provider, list)
        else PROVIDERS_PREFERENCE
    )

    for p in providers_to_try:
        success, url = _try_provider(p, local_path)
        if success and url:
            return url

    msg = "No provider available or all providers failed"
    raise ValueError(msg)
