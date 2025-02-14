#!/usr/bin/env -S uv run
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

import os
from pathlib import Path
from typing import TypedDict
import boto3
from botocore.exceptions import ClientError
from loguru import logger


class S3Credentials(TypedDict):
    """Type for S3 credentials and configuration."""

    bucket: str
    endpoint_url: str | None
    path_style: bool
    role_arn: str | None
    aws_access_key_id: str | None
    aws_secret_access_key: str | None
    aws_session_token: str | None


def get_credentials() -> S3Credentials | None:
    """
    Get S3 credentials from environment variables.
    This function only checks environment variables and returns them,
    without importing or initializing any external dependencies.

    Returns:
        Optional[S3Credentials]: Credentials if all required ones are present, None otherwise
    """
    # Check required bucket name
    bucket = os.getenv("AWS_S3_BUCKET")
    if not bucket:
        logger.debug("Required AWS_S3_BUCKET environment variable not set")
        return None

    # Build credentials dict
    creds: S3Credentials = {
        "bucket": bucket,
        "endpoint_url": os.getenv("AWS_ENDPOINT_URL"),
        "path_style": os.getenv("AWS_S3_PATH_STYLE", "").lower() == "true",
        "role_arn": os.getenv("AWS_ROLE_ARN"),
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "aws_session_token": os.getenv("AWS_SESSION_TOKEN"),
    }

    return creds


def get_provider(credentials: S3Credentials | None = None):
    """
    Initialize and return the S3 provider client.
    This function handles importing dependencies and creating the client.

    Args:
        credentials: Optional credentials to use. If None, will call get_credentials()

    Returns:
        tuple[boto3.client, str]: Tuple of (s3_client, bucket_name) if successful, None otherwise
    """
    if credentials is None:
        credentials = get_credentials()

    if not credentials:
        return None

    try:
        # Build client kwargs
        client_kwargs = {}

        if credentials["endpoint_url"]:
            client_kwargs["endpoint_url"] = credentials["endpoint_url"]

        # Configure credentials if explicitly provided
        if credentials["aws_access_key_id"] and credentials["aws_secret_access_key"]:
            client_kwargs["aws_access_key_id"] = credentials["aws_access_key_id"]
            client_kwargs["aws_secret_access_key"] = credentials[
                "aws_secret_access_key"
            ]
            if credentials["aws_session_token"]:
                client_kwargs["aws_session_token"] = credentials["aws_session_token"]

        # Path-style endpoints
        if credentials["path_style"]:
            client_kwargs["config"] = boto3.client("s3").get_config_variable("s3", {})
            client_kwargs["config"]["s3"] = {"addressing_style": "path"}

        # Handle role assumption if specified
        if credentials["role_arn"]:
            sts = boto3.client("sts")
            assumed_role = sts.assume_role(
                RoleArn=credentials["role_arn"], RoleSessionName="twat_fs_upload"
            )
            client_kwargs["aws_access_key_id"] = assumed_role["Credentials"][
                "AccessKeyId"
            ]
            client_kwargs["aws_secret_access_key"] = assumed_role["Credentials"][
                "SecretAccessKey"
            ]
            client_kwargs["aws_session_token"] = assumed_role["Credentials"][
                "SessionToken"
            ]

        # Create the client
        s3_client = boto3.client("s3", **client_kwargs)

        # Test the client with a simple operation
        s3_client.list_buckets()

        return s3_client, credentials["bucket"]

    except Exception as e:
        logger.warning(f"Failed to initialize S3 provider: {e}")
        return None


def upload_file(local_path: str | Path, remote_path: str | Path | None = None) -> str:
    """
    Upload a file to AWS S3 and return its URL.

    Args:
        local_path: Local file path
        remote_path: Optional remote path (defaults to filename)

    Returns:
        str: URL of the uploaded file

    Raises:
        ValueError: If AWS credentials are not properly configured
        ClientError: If upload fails
    """
    if not provider_auth():
        msg = "AWS credentials must be properly configured"
        raise ValueError(msg)

    local_path = Path(local_path)
    bucket = os.getenv("AWS_S3_BUCKET")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    # Use the file name as the S3 key, but ensure it's unique by adding a timestamp if needed
    s3_key = local_path.name if remote_path is None else remote_path

    # Get S3 client configuration
    client_kwargs = {}
    if endpoint_url := os.getenv("AWS_ENDPOINT_URL"):
        client_kwargs["endpoint_url"] = endpoint_url

    if os.getenv("AWS_S3_PATH_STYLE", "").lower() == "true":
        client_kwargs["config"] = boto3.client("s3").get_config_variable("s3", {})
        client_kwargs["config"]["s3"] = {"addressing_style": "path"}

    try:
        # Handle role assumption if configured
        if role_arn := os.getenv("AWS_ROLE_ARN"):
            sts = boto3.client("sts")
            assumed_role = sts.assume_role(
                RoleArn=role_arn, RoleSessionName="twat_fs_upload"
            )
            credentials = assumed_role["Credentials"]
            session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
            )
            s3 = session.client("s3", **client_kwargs)
        else:
            s3 = boto3.client("s3", **client_kwargs)

        # Check if file is large enough for multipart upload
        file_size = local_path.stat().st_size
        if file_size > 5 * 1024 * 1024:  # 5MB threshold
            # Initialize multipart upload
            mpu = s3.create_multipart_upload(Bucket=bucket, Key=s3_key)
            upload_id = mpu["UploadId"]

            try:
                parts = []
                chunk_size = 5 * 1024 * 1024  # 5MB chunks
                part_number = 1

                with open(local_path, "rb") as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break

                        # Upload part
                        part = s3.upload_part(
                            Bucket=bucket,
                            Key=s3_key,
                            PartNumber=part_number,
                            UploadId=upload_id,
                            Body=chunk,
                        )
                        parts.append({"PartNumber": part_number, "ETag": part["ETag"]})
                        part_number += 1

                # Complete multipart upload
                s3.complete_multipart_upload(
                    Bucket=bucket,
                    Key=s3_key,
                    UploadId=upload_id,
                    MultipartUpload={"Parts": parts},
                )
            except Exception:
                # Abort multipart upload on failure
                s3.abort_multipart_upload(Bucket=bucket, Key=s3_key, UploadId=upload_id)
                raise
        else:
            # Simple upload for small files
            with open(local_path, "rb") as f:
                s3.upload_fileobj(f, bucket, s3_key)

        # Generate the S3 URL
        if endpoint_url:
            url = f"{endpoint_url}/{bucket}/{s3_key}"
        else:
            url = f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"
        return url

    except ClientError as e:
        logger.error(f"Failed to upload to S3: {e!s}")
        raise
