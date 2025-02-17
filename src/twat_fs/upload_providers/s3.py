#!/usr/bin/env python
# /// script
# dependencies = [
#   "boto3",
#   "loguru",
# ]
# ///
# this_file: src/twat_fs/upload_providers/s3.py

"""
AWS S3 provider for file uploads.
This module provides functionality to upload files to Amazon S3 storage service.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import boto3
from loguru import logger

# Provider-specific help messages
PROVIDER_HELP = {
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
}


def get_credentials() -> dict[str, Any] | None:
    """
    Retrieve AWS S3 credentials from environment variables.

    Returns:
        Optional[Dict[str, Any]]: Credentials dict or None if not configured
    """
    bucket = os.getenv("AWS_S3_BUCKET")
    if not bucket:
        logger.debug("Required AWS_S3_BUCKET environment variable not set")
        return None

    region = os.getenv("AWS_DEFAULT_REGION")
    path_style = os.getenv("AWS_S3_PATH_STYLE", "").lower() == "true"
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")
    role_arn = os.getenv("AWS_ROLE_ARN")
    access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    session_token = os.getenv("AWS_SESSION_TOKEN")

    return {
        "bucket": bucket,
        "region": region,
        "path_style": path_style,
        "endpoint_url": endpoint_url,
        "role_arn": role_arn,
        "aws_access_key_id": access_key_id,
        "aws_secret_access_key": secret_access_key,
        "aws_session_token": session_token,
    }


def get_provider(creds: dict[str, Any] | None = None):
    """
    Initialize and return the S3 provider using the boto3 client.

    Args:
        creds: Optional credentials dict (if None, will fetch from environment)

    Returns:
        Optional[boto3.client]: Configured S3 client or None if initialization fails
    """
    if creds is None:
        creds = get_credentials()
    if not creds:
        return None

    client_kwargs = {}
    if creds.get("region"):
        client_kwargs["region_name"] = creds["region"]
    if creds.get("endpoint_url"):
        client_kwargs["endpoint_url"] = creds["endpoint_url"]
    if creds.get("path_style"):
        from boto3.session import Config

        client_kwargs["config"] = Config(s3={"addressing_style": "path"})

    try:
        client = boto3.client("s3", **client_kwargs)
        # Test the client by listing buckets
        try:
            client.list_buckets()
            return client
        except Exception as e:
            logger.warning(f"Failed to validate S3 client: {e}")
            return None
    except Exception as e:
        logger.warning(f"Failed to create S3 client: {e}")
        return None


def upload_file(
    local_path: str | Path,
    remote_path: str | Path | None = None,
    *,  # Force keyword arguments for boolean flags
    unique: bool = False,  # Ignored for S3
    force: bool = False,  # Ignored for S3
    upload_path: str | None = None,  # Ignored for S3
) -> str:
    """
    Upload a file to AWS S3, handling multipart uploads for large files.

    Args:
        local_path: Path to the file to upload
        remote_path: Optional remote path/key to use in S3
        unique: Whether to ensure unique filenames (ignored for S3)
        force: Whether to overwrite existing files (ignored for S3)
        upload_path: Custom base upload path (ignored for S3)

    Returns:
        str: URL to the uploaded file

    Raises:
        ValueError: If upload fails or credentials are missing
    """
    local_path = Path(local_path)
    creds = get_credentials()
    if not creds:
        msg = "S3 credentials not configured"
        raise ValueError(msg)

    client = get_provider(creds)
    if client is None:
        msg = "Failed to initialize S3 client"
        raise ValueError(msg)

    key = str(remote_path or local_path.name)
    try:
        # Use upload_fileobj for all files
        with open(local_path, "rb") as f:
            client.upload_fileobj(f, creds["bucket"], key)

        # Return the URL to the uploaded file
        if creds.get("endpoint_url"):
            return f"{creds['endpoint_url']}/{creds['bucket']}/{key}"
        return f"https://s3.amazonaws.com/{creds['bucket']}/{key}"
    except Exception as e:
        logger.warning(f"S3 upload failed: {e}")
        msg = "S3 upload failed"
        raise ValueError(msg) from e
