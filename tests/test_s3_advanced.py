#!/usr/bin/env python3
# this_file: tests/test_s3_advanced.py

"""
Advanced tests for S3 provider functionality.
Tests AWS credential providers, S3 configurations, and multipart uploads.
"""

import os
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

from twat_fs.upload import upload_file
from twat_fs.upload_providers import s3

# Test data
TEST_DIR = Path(__file__).parent / "data"
TEST_FILE = TEST_DIR / "test.txt"


class TestAwsCredentialProviders:
    """Test different AWS credential providers."""

    def test_environment_credentials(self, monkeypatch):
        """Test using environment credentials."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")

        creds = s3.get_credentials()
        assert creds is not None
        assert creds["bucket"] == "test-bucket"
        assert creds["aws_access_key_id"] == "test_key"
        assert creds["aws_secret_access_key"] == "test_secret"

        with patch("boto3.client") as mock_client:
            mock_s3 = mock_client.return_value
            mock_s3.list_buckets.return_value = {"Buckets": []}
            provider = s3.get_provider(creds)
            assert provider is not None

    def test_shared_credentials_file(self, tmp_path, monkeypatch):
        """Test using shared credentials file."""
        creds_file = tmp_path / ".aws" / "credentials"
        creds_file.parent.mkdir(exist_ok=True)
        creds_file.write_text(
            "[default]\n"
            "aws_access_key_id = test_key\n"
            "aws_secret_access_key = test_secret\n"
        )
        monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(creds_file))
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")

        creds = s3.get_credentials()
        assert creds is not None
        assert creds["bucket"] == "test-bucket"

        with patch("boto3.client") as mock_client:
            mock_s3 = mock_client.return_value
            mock_s3.list_buckets.return_value = {"Buckets": []}
            provider = s3.get_provider(creds)
            assert provider is not None

    def test_assume_role(self, monkeypatch):
        """Test using assumed role credentials."""
        monkeypatch.setenv("AWS_ROLE_ARN", "arn:aws:iam::123456789012:role/test-role")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")

        creds = s3.get_credentials()
        assert creds is not None
        assert creds["role_arn"] == "arn:aws:iam::123456789012:role/test-role"
        assert creds["bucket"] == "test-bucket"

        with patch("boto3.client") as mock_client:
            mock_sts = MagicMock()
            mock_client.side_effect = [
                mock_sts,  # First call creates STS client
                MagicMock(),  # Second call creates S3 client
            ]
            mock_sts.assume_role.return_value = {
                "Credentials": {
                    "AccessKeyId": "test_key",
                    "SecretAccessKey": "test_secret",
                    "SessionToken": "test_token",
                }
            }
            provider = s3.get_provider(creds)
            assert provider is not None


class TestS3Configurations:
    """Test different S3 configurations."""

    def test_custom_endpoint(self, monkeypatch):
        """Test using a custom S3 endpoint."""
        monkeypatch.setenv("AWS_ENDPOINT_URL", "https://custom-s3.example.com")
        monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")

        creds = s3.get_credentials()
        assert creds is not None
        assert creds["endpoint_url"] == "https://custom-s3.example.com"

        with patch("boto3.client") as mock_client:
            mock_s3 = mock_client.return_value
            mock_s3.list_buckets.return_value = {"Buckets": []}
            provider = s3.get_provider(creds)
            assert provider is not None
            mock_client.assert_called_with(
                "s3",
                endpoint_url="https://custom-s3.example.com",
            )

    def test_path_style_endpoint(self, monkeypatch):
        """Test using path-style S3 endpoint."""
        monkeypatch.setenv("AWS_S3_PATH_STYLE", "true")
        monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")

        creds = s3.get_credentials()
        assert creds is not None
        assert creds["path_style"] is True

        with patch("boto3.client") as mock_client:
            mock_s3 = mock_client.return_value
            mock_s3.list_buckets.return_value = {"Buckets": []}
            provider = s3.get_provider(creds)
            assert provider is not None
            mock_client.assert_called_with(
                "s3",
                config=pytest.approx({"s3": {"addressing_style": "path"}}),
            )

    def test_custom_region_endpoint(self, monkeypatch):
        """Test using a custom region endpoint."""
        monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-central-1")
        monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")

        creds = s3.get_credentials()
        assert creds is not None

        with patch("boto3.client") as mock_client:
            mock_s3 = mock_client.return_value
            mock_s3.list_buckets.return_value = {"Buckets": []}
            provider = s3.get_provider(creds)
            assert provider is not None
            mock_client.assert_called_with("s3", region_name="eu-central-1")


class TestS3MultipartUploads:
    """Test S3 multipart upload functionality."""

    @pytest.fixture
    def large_file(self, tmp_path):
        """Create a large test file."""
        file_path = tmp_path / "large_test.bin"
        size = 10 * 1024 * 1024  # 10MB
        with file_path.open("wb") as f:
            f.write(os.urandom(size))
        return file_path

    def test_multipart_upload(self, large_file, monkeypatch):
        """Test multipart upload of a large file."""
        monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")

        with patch("boto3.client") as mock_client:
            mock_s3 = mock_client.return_value
            mock_s3.create_multipart_upload.return_value = {
                "UploadId": "test_upload_id"
            }
            mock_s3.upload_part.return_value = {"ETag": "test_etag"}
            mock_s3.complete_multipart_upload.return_value = {}
            mock_s3.list_buckets.return_value = {"Buckets": []}

            url = upload_file(large_file, provider="s3")

            assert url.startswith("https://")
            mock_s3.create_multipart_upload.assert_called_once()
            assert mock_s3.upload_part.call_count > 1
            mock_s3.complete_multipart_upload.assert_called_once()

    def test_multipart_upload_failure(self, large_file, monkeypatch):
        """Test handling of multipart upload failure."""
        monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")

        with patch("boto3.client") as mock_client:
            mock_s3 = mock_client.return_value
            mock_s3.create_multipart_upload.return_value = {
                "UploadId": "test_upload_id"
            }
            mock_s3.list_buckets.return_value = {"Buckets": []}
            mock_s3.upload_part.side_effect = ClientError(
                {"Error": {"Code": "InternalError", "Message": "Internal error"}},
                "UploadPart",
            )

            with pytest.raises(
                ValueError, match="No provider available or all providers failed"
            ):
                upload_file(large_file, provider="s3")

            mock_s3.abort_multipart_upload.assert_called_once()
