#!/usr/bin/env python3
# this_file: tests/test_s3_advanced.py

"""
Advanced tests for S3 provider functionality.
Tests AWS credential providers, S3 configurations, and multipart uploads.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from typing import Any # Removed Union, ModuleType not needed if s3 is Any

# Check for S3 and botocore availability
s3: Any # Simplified type for the s3 variable used in tests
HAS_BOTOCORE = False
HAS_S3 = False
ClientError: Any = Exception # Default placeholder

try:
    import botocore.exceptions
    ClientError = botocore.exceptions.ClientError
    HAS_BOTOCORE = True
except ImportError:
    HAS_BOTOCORE = False
    # ClientError remains placeholder

try:
    from twat_fs.upload_providers import s3 as s3_real_module
    s3 = s3_real_module # s3 is now the real module
    HAS_S3 = True
except ImportError:
    HAS_S3 = False
    # Create a mock s3 module
    class MockS3Provider:
        """Mock S3 provider for tests when S3 is not available."""

        client = None
        bucket = None

        @classmethod
        def get_credentials(cls) -> dict[str, Any]:
            """Mock get_credentials method."""
            return {}
        def __init__(self, *args: Any, **kwargs: Any): # Basic init for S3Provider() calls
            pass

    # Define a mock s3 module
    class MockS3Module:
        """Mock s3 module for tests when S3 is not available."""

        S3Provider = MockS3Provider

        @staticmethod
        def get_provider(*_args: Any, **_kwargs: Any) -> MockS3Provider:
            """Mock get_provider function."""
            return MockS3Provider()

        @staticmethod
        def get_credentials() -> dict[str, Any]:
            """Mock get_credentials function."""
            return {}

        @staticmethod
        def upload_file(*_args: Any, **_kwargs: Any) -> str:
            """Mock upload_file function."""
            return "https://mock-s3-url.com/test.txt"

    # Assign the mock module to s3
    s3 = MockS3Module()


# Test constants - using uppercase to indicate these are test values
TEST_BUCKET = "test-bucket"
TEST_ACCESS_KEY = "test_key"
TEST_SECRET_KEY = "test_secret"  # noqa: S105 - This is dummy data for testing

# Test data
TEST_DIR = Path(__file__).parent / "data"
TEST_FILE = TEST_DIR / "test.txt"


@pytest.mark.skipif(
    not HAS_BOTOCORE or not HAS_S3, reason="Botocore or S3 dependencies not installed"
)
class TestAwsCredentialProviders:
    """Test different AWS credential providers."""

    def test_environment_credentials(self, monkeypatch):
        """Test credentials from environment variables."""
        # Setup environment variables
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", TEST_ACCESS_KEY)
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", TEST_SECRET_KEY)
        monkeypatch.setenv("AWS_S3_BUCKET", TEST_BUCKET)

        # Create S3 provider using the module's get_provider function
        provider = s3.get_provider()

        # Check that credentials were loaded correctly
        assert provider is not None
        assert provider.client is not None
        # assert provider.bucket == TEST_BUCKET # .bucket is not on ProviderClient protocol

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
            # s3.get_provider() should use the env vars set for credentials
            provider = s3.get_provider()
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
            # s3.get_provider() should use the env vars set for credentials
            provider = s3.get_provider()
            assert provider is not None


@pytest.mark.skipif(
    not HAS_S3 or not HAS_BOTOCORE, reason="S3 dependencies not installed"
)
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
            # s3.get_provider() should use the env vars set for credentials
            provider = s3.get_provider()
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
            # s3.get_provider() should use the env vars set for credentials
            provider = s3.get_provider()
            assert provider is not None

            # Get the actual config object from the call
            call_args = mock_client.call_args
            assert call_args is not None
            _, kwargs = call_args
            assert "config" in kwargs
            config = kwargs["config"]
            assert hasattr(config, "s3")
            assert config.s3 == {"addressing_style": "path"}

    def test_custom_region_endpoint(self, monkeypatch):
        """Test using a custom region endpoint."""
        monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-central-1")
        monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")

        creds = s3.get_credentials()
        assert creds is not None

        with patch("boto3.client") as mock_client:
            mock_s3 = mock_client.return_value
            mock_s3.list_buckets.return_value = {"Buckets": []}
            # s3.get_provider() should use the env vars set for credentials
            provider = s3.get_provider()
            assert provider is not None
            mock_client.assert_called_with("s3", region_name="eu-central-1")


@pytest.mark.skipif(
    not HAS_S3 or not HAS_BOTOCORE, reason="S3 dependencies not installed"
)
class TestS3MultipartUploads:
    """Test multipart uploads to S3."""

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
        # Set up environment variables
        monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")

        # Create a mock S3 client
        mock_s3 = MagicMock()
        mock_s3.list_buckets.return_value = {"Buckets": []}
        mock_s3.upload_fileobj.return_value = None  # Successful upload returns None

        # Mock both boto3 module and client
        with patch("twat_fs.upload_providers.s3.boto3.client", return_value=mock_s3):
            result = s3.upload_file(large_file) # Returns UploadResult

            # Verify the URL format
            assert result.url.startswith("https://s3.amazonaws.com/test-bucket/")
            assert result.url.endswith(large_file.name)

            # Verify the upload was called correctly
            assert mock_s3.upload_fileobj.call_count == 1
            args, kwargs = mock_s3.upload_fileobj.call_args
            assert len(args) == 3  # Should have file object, bucket, and key
            assert args[1] == "test-bucket"  # Check bucket name
            assert hasattr(args[0], "read")  # Check if it's a file-like object

    def test_multipart_upload_failure(self, large_file, monkeypatch):
        """Test handling of multipart upload failure."""
        # Set up environment variables
        monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")

        # Create a mock S3 client that fails on upload
        mock_s3 = MagicMock()
        mock_s3.list_buckets.return_value = {"Buckets": []}
        mock_s3.upload_fileobj.side_effect = ClientError(
            {"Error": {"Code": "InternalError", "Message": "Internal error"}},
            "UploadFileObj",
        )

        # Mock both boto3 module and client
        with patch("twat_fs.upload_providers.s3.boto3.client", return_value=mock_s3):
            with pytest.raises(ValueError, match="S3 upload failed"):
                s3.upload_file(large_file)

            # Verify the upload was attempted
            assert mock_s3.upload_fileobj.call_count == 1
            args, kwargs = mock_s3.upload_fileobj.call_args
            assert len(args) == 3  # Should have file object, bucket, and key
            assert args[1] == "test-bucket"  # Check bucket name
            assert hasattr(args[0], "read")  # Check if it's a file-like object
