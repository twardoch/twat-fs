#!/usr/bin/env python3
# this_file: tests/test_upload.py

"""
Tests for the upload functionality.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from botocore.exceptions import ClientError

from twat_fs.upload import (
    PROVIDERS_PREFERENCE,
    setup_provider,
    setup_providers,
    upload_file,
)
from twat_fs.upload_providers import (
    dropbox,
    fal,
    s3,
    catbox,
    litterbox,
    UploadResult,
)
from twat_fs.upload_providers.core import RetryableError, NonRetryableError

# Test data
TEST_FILE = Path(__file__).parent / "data" / "test.txt"
TEST_URL = "https://example.com/test.txt"


@pytest.fixture
def test_file(tmp_path: Path) -> Path:
    """Create a temporary test file."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")
    return file_path


@pytest.fixture
def mock_fal_provider() -> MagicMock:
    """Mock FAL provider."""
    with patch("twat_fs.upload_providers.fal.get_credentials") as mock_creds:
        with patch("twat_fs.upload_providers.fal.get_provider") as mock_provider:
            mock_creds.return_value = "test_key"
            client = MagicMock()
            client.upload_file.return_value = TEST_URL
            mock_provider.return_value = client
            yield client.upload_file


@pytest.fixture
def mock_dropbox_provider() -> MagicMock:
    """Mock Dropbox provider."""
    with patch("twat_fs.upload_providers.dropbox.upload_file") as mock_upload:
        with patch("twat_fs.upload_providers.dropbox.get_credentials") as mock_creds:
            with patch(
                "twat_fs.upload_providers.dropbox.get_provider"
            ) as mock_provider:
                mock_upload.return_value = TEST_URL
                mock_creds.return_value = {"access_token": "test_token"}
                mock_provider.return_value = MagicMock()
                yield mock_upload


@pytest.fixture
def mock_s3_provider() -> MagicMock:
    """Mock S3 provider."""
    with patch("twat_fs.upload_providers.s3.get_credentials") as mock_creds:
        with patch("twat_fs.upload_providers.s3.get_provider") as mock_provider:
            mock_creds.return_value = {
                "bucket": "test-bucket",
                "endpoint_url": None,
                "path_style": False,
                "role_arn": None,
                "aws_access_key_id": "test_key",
                "aws_secret_access_key": "test_secret",
                "aws_session_token": None,
            }
            client = MagicMock()
            client.upload_file.return_value = TEST_URL
            mock_provider.return_value = client
            yield client.upload_file


class TestProviderSetup:
    """Test provider setup functionality."""

    def test_setup_working_provider(self, mock_s3_provider: MagicMock) -> None:
        """Test setup check for a working provider."""
        assert mock_s3_provider is not None  # Verify fixture is used
        success, explanation = setup_provider("s3")
        assert success is True
        assert "You can upload files to: s3" in explanation

    def test_setup_missing_credentials(self) -> None:
        """Test setup check when credentials are missing."""
        with patch("twat_fs.upload_providers.s3.get_credentials") as mock_creds:
            mock_creds.return_value = None
            success, explanation = setup_provider("s3")
            assert success is False
            assert "not configured" in explanation
            assert "AWS_S3_BUCKET" in explanation
            assert "AWS_ACCESS_KEY_ID" in explanation

    def test_setup_missing_dependencies(self) -> None:
        """Test setup check when dependencies are missing."""
        with patch("twat_fs.upload_providers.s3.get_credentials") as mock_creds:
            with patch("twat_fs.upload_providers.s3.get_provider") as mock_provider:
                mock_creds.return_value = {
                    "bucket": "test-bucket",
                    "aws_access_key_id": "test_key",
                    "aws_secret_access_key": "test_secret",
                }
                mock_provider.return_value = None
                success, explanation = setup_provider("s3")
                assert success is False
                assert "additional setup is needed" in explanation
                assert "boto3" in explanation

    def test_setup_invalid_provider(self) -> None:
        """Test setup check for an invalid provider."""
        with pytest.raises(KeyError):
            setup_provider("invalid")

    def test_setup_all_providers(
        self,
        mock_s3_provider: MagicMock,
        mock_dropbox_provider: MagicMock,
        mock_fal_provider: MagicMock,
    ) -> None:
        """Test checking setup status for all providers."""
        assert all(
            provider is not None
            for provider in [mock_s3_provider, mock_dropbox_provider, mock_fal_provider]
        )
        results = setup_providers()
        assert len(results) == len(PROVIDERS_PREFERENCE)

        # Check S3 result
        assert results["s3"][0] is True  # success
        assert "You can upload files to: s3" in results["s3"][1]  # explanation

        # Check Dropbox result
        assert results["dropbox"][0] is True
        assert "You can upload files to: dropbox" in results["dropbox"][1]

        # Check FAL result
        assert results["fal"][0] is True
        assert "You can upload files to: fal" in results["fal"][1]

    def test_setup_all_providers_with_failures(self) -> None:
        """Test checking setup status when some providers fail."""
        with (
            patch("twat_fs.upload_providers.s3.get_credentials") as mock_s3_creds,
            patch(
                "twat_fs.upload_providers.dropbox.get_credentials"
            ) as mock_dropbox_creds,
            patch("twat_fs.upload_providers.fal.get_provider") as mock_fal_provider,
        ):
            # S3: Missing credentials
            mock_s3_creds.return_value = None

            # Dropbox: Has credentials but missing dependencies
            mock_dropbox_creds.return_value = {"access_token": "test"}

            # FAL: Has credentials and working
            mock_fal_provider.return_value = MagicMock()

            results = setup_providers()

            # Check S3 result (missing credentials)
            assert results["s3"][0] is False
            assert "not configured" in results["s3"][1]

            # Check Dropbox result (missing dependencies)
            assert results["dropbox"][0] is False
            assert "Additional setup needed" in results["dropbox"][1]

            # Check FAL result (working)
            assert results["fal"][0] is True
            assert "client: MagicMock" in results["fal"][1]


class TestProviderAuth:
    """Test provider authentication functions."""

    def test_fal_auth_with_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test FAL auth when key is present."""
        monkeypatch.setenv("FAL_KEY", "test_key")
        assert fal.get_credentials() is not None
        with patch("fal_client.status") as mock_status:
            mock_status.return_value = True
            assert fal.get_provider() is not None

    def test_fal_auth_without_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test FAL auth when key is missing."""
        monkeypatch.delenv("FAL_KEY", raising=False)
        assert fal.get_credentials() is None
        assert fal.get_provider() is None

    def test_dropbox_auth_with_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Dropbox auth when token is present."""
        monkeypatch.setenv("DROPBOX_ACCESS_TOKEN", "test_token")
        assert dropbox.get_credentials() is not None
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_instance = mock_dropbox.return_value
            mock_instance.users_get_current_account.return_value = True
            assert dropbox.get_provider() is not None

    def test_dropbox_auth_without_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Dropbox auth when token is missing."""
        monkeypatch.delenv("DROPBOX_ACCESS_TOKEN", raising=False)
        assert dropbox.get_credentials() is None
        with pytest.raises(ValueError, match="Dropbox credentials not found"):
            dropbox.upload_file("test.txt")

    def test_s3_auth_with_credentials(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test S3 auth when credentials are present."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret")
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

    def test_s3_auth_without_credentials(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test S3 auth when credentials are missing."""
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
        monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
        monkeypatch.delenv("AWS_S3_BUCKET", raising=False)
        assert s3.get_credentials() is None
        assert s3.get_provider() is None

    def test_s3_auth_with_invalid_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test S3 auth when credentials are invalid."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "invalid_key")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "invalid_secret")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")

        creds = s3.get_credentials()
        assert creds is not None

        with patch("boto3.client") as mock_client:
            mock_s3 = mock_client.return_value
            mock_s3.list_buckets.side_effect = ClientError(
                {"Error": {"Code": "InvalidAccessKeyId", "Message": "Invalid key"}},
                "ListBuckets",
            )
            provider = s3.get_provider(creds)
            assert provider is None


class TestUploadFile:
    """Test file upload functionality."""

    def test_upload_with_default_provider(
        self, test_file: Path, mock_s3_provider: MagicMock
    ) -> None:
        """Test upload with default provider."""
        url = upload_file(test_file)
        assert url == TEST_URL
        mock_s3_provider.assert_called_once_with(
            test_file,
            remote_path=None,
            unique=False,
            force=False,
            upload_path=None,
        )

    def test_upload_with_specific_provider(
        self, test_file: Path, mock_s3_provider: MagicMock
    ) -> None:
        """Test upload with specific provider."""
        url = upload_file(test_file, provider="s3")
        assert url == TEST_URL
        mock_s3_provider.assert_called_once_with(
            test_file,
            remote_path=None,
            unique=False,
            force=False,
            upload_path=None,
        )

    def test_upload_with_provider_list(
        self, test_file: Path, mock_s3_provider: MagicMock
    ) -> None:
        """Test upload with provider list."""
        url = upload_file(test_file, provider=["s3", "dropbox"])
        assert url == TEST_URL
        mock_s3_provider.assert_called_once_with(
            test_file,
            remote_path=None,
            unique=False,
            force=False,
            upload_path=None,
        )

    def test_upload_fallback_on_auth_failure(
        self,
        test_file: Path,
        mock_s3_provider: MagicMock,
        mock_dropbox_provider: MagicMock,
    ) -> None:
        """Test fallback to next provider on auth failure."""
        with (
            patch("twat_fs.upload_providers.s3.get_provider") as mock_s3_get_provider,
            patch(
                "twat_fs.upload_providers.dropbox.get_provider"
            ) as mock_dropbox_get_provider,
        ):
            # S3 provider fails to initialize
            mock_s3_get_provider.return_value = None

            # Dropbox provider works
            mock_dropbox_client = MagicMock()
            mock_dropbox_client.upload_file.return_value = TEST_URL
            mock_dropbox_get_provider.return_value = mock_dropbox_client

            url = upload_file(test_file, provider=["s3", "dropbox"])
            assert url == TEST_URL

            # S3 provider should not be called since it failed to initialize
            mock_s3_provider.assert_not_called()

            # Dropbox provider should be called
            mock_dropbox_client.upload_file.assert_called_once_with(
                local_path=test_file,
                remote_path=None,
                unique=False,
                force=False,
                upload_path=None,
            )

    def test_upload_fallback_on_upload_failure(
        self,
        test_file: Path,
        mock_s3_provider: MagicMock,
        mock_dropbox_provider: MagicMock,
    ) -> None:
        """Test fallback to next provider on upload failure."""
        mock_s3_provider.side_effect = Exception("Upload failed")
        mock_dropbox_provider.return_value = TEST_URL

        with (
            patch("twat_fs.upload_providers.s3.get_provider") as mock_s3_get_provider,
            patch(
                "twat_fs.upload_providers.dropbox.get_provider"
            ) as mock_dropbox_get_provider,
        ):
            mock_s3_client = MagicMock()
            mock_s3_client.upload_file.side_effect = Exception("Upload failed")
            mock_s3_get_provider.return_value = mock_s3_client

            mock_dropbox_client = MagicMock()
            mock_dropbox_client.upload_file.return_value = TEST_URL
            mock_dropbox_get_provider.return_value = mock_dropbox_client

            url = upload_file(test_file, provider=["s3", "dropbox"])
            assert url == TEST_URL

            # S3 provider should be called and fail
            mock_s3_client.upload_file.assert_called_once_with(
                local_path=test_file,
                remote_path=None,
                unique=False,
                force=False,
                upload_path=None,
            )

            # Dropbox provider should be called and succeed
            mock_dropbox_client.upload_file.assert_called_once_with(
                local_path=test_file,
                remote_path=None,
                unique=False,
                force=False,
                upload_path=None,
            )

    def test_all_providers_fail(self, test_file: Path) -> None:
        """Test error when all providers fail."""
        with (
            patch("twat_fs.upload_providers.fal.get_provider") as mock_fal,
            patch("twat_fs.upload_providers.dropbox.get_provider") as mock_dropbox,
            patch("twat_fs.upload_providers.s3.get_provider") as mock_s3,
            patch("twat_fs.upload_providers.termbin.get_provider") as mock_termbin,
            patch("twat_fs.upload_providers.www0x0.get_provider") as mock_www0x0,
            patch("twat_fs.upload_providers.uguu.get_provider") as mock_uguu,
            patch(
                "twat_fs.upload_providers.bashupload.get_provider"
            ) as mock_bashupload,
        ):
            # Make all providers fail
            mock_fal.return_value = None
            mock_dropbox.return_value = None
            mock_s3.return_value = None
            mock_termbin.return_value = None
            mock_www0x0.return_value = None
            mock_uguu.return_value = None
            mock_bashupload.return_value = None

            with pytest.raises(
                ValueError, match="No provider available or all providers failed"
            ):
                upload_file(test_file)

    def test_invalid_provider(self, test_file: Path) -> None:
        """Test error when provider is invalid."""
        with pytest.raises(ValueError, match="Invalid provider"):
            upload_file(test_file, provider="invalid")

    def test_upload_with_s3_provider(
        self, test_file: Path, mock_s3_provider: MagicMock
    ) -> None:
        """Test upload with S3 provider."""
        url = upload_file(test_file, provider="s3")
        assert url == TEST_URL
        mock_s3_provider.assert_called_once_with(
            local_path=test_file,
            remote_path=None,
            unique=False,
            force=False,
            upload_path=None,
        )

    def test_s3_upload_failure(
        self, test_file: Path, mock_s3_provider: MagicMock
    ) -> None:
        """Test S3 upload failure."""
        mock_s3_provider.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "Bucket does not exist"}},
            "PutObject",
        )
        with pytest.raises(
            ValueError, match="An error occurred .* Bucket does not exist"
        ):
            upload_file(test_file, provider="s3")


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test uploading an empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.touch()

        with patch("twat_fs.upload_providers.s3.get_provider") as mock_provider:
            client = MagicMock()
            client.upload_file.return_value = TEST_URL
            mock_provider.return_value = client

            url = upload_file(test_file, provider="s3")
            assert url == TEST_URL

            client.upload_file.assert_called_once_with(
                local_path=test_file,
                remote_path=None,
                unique=False,
                force=False,
                upload_path=None,
            )

    def test_special_characters_in_filename(self, tmp_path: Path) -> None:
        """Test uploading a file with special characters in the name."""
        test_file = tmp_path / "test!@#$%^&*.txt"
        test_file.write_text("test content")

        with patch("twat_fs.upload_providers.s3.get_provider") as mock_provider:
            client = MagicMock()
            client.upload_file.return_value = TEST_URL
            mock_provider.return_value = client

            url = upload_file(test_file, provider="s3")
            assert url == TEST_URL

            client.upload_file.assert_called_once_with(
                local_path=test_file,
                remote_path=None,
                unique=False,
                force=False,
                upload_path=None,
            )

    def test_unicode_filename(self, tmp_path: Path) -> None:
        """Test uploading a file with Unicode characters in the name."""
        test_file = tmp_path / "test_文件.txt"
        test_file.write_text("test content")

        with patch("twat_fs.upload_providers.s3.get_provider") as mock_provider:
            client = MagicMock()
            client.upload_file.return_value = TEST_URL
            mock_provider.return_value = client

            url = upload_file(test_file, provider="s3")
            assert url == TEST_URL

            client.upload_file.assert_called_once_with(
                local_path=test_file,
                remote_path=None,
                unique=False,
                force=False,
                upload_path=None,
            )

    def test_very_long_filename(self, tmp_path: Path) -> None:
        """Test uploading a file with a very long name."""
        long_name = "a" * 255 + ".txt"  # Max filename length on most filesystems
        test_file = tmp_path / long_name
        test_file.write_text("test content")

        with patch("twat_fs.upload_providers.s3.get_provider") as mock_provider:
            client = MagicMock()
            client.upload_file.return_value = TEST_URL
            mock_provider.return_value = client

            url = upload_file(test_file, provider="s3")
            assert url == TEST_URL

            client.upload_file.assert_called_once_with(
                local_path=test_file,
                remote_path=None,
                unique=False,
                force=False,
                upload_path=None,
            )

    def test_nonexistent_file(self) -> None:
        """Test uploading a nonexistent file."""
        with pytest.raises(FileNotFoundError):
            upload_file("nonexistent.txt")

    def test_directory_upload(self, tmp_path: Path) -> None:
        """Test attempting to upload a directory."""
        with pytest.raises(ValueError, match="is a directory"):
            upload_file(tmp_path)

    def test_no_read_permission(self, tmp_path: Path) -> None:
        """Test uploading a file without read permission."""
        test_file = tmp_path / "noperm.txt"
        test_file.write_text("test content")
        test_file.chmod(0o000)  # Remove all permissions

        with pytest.raises(PermissionError):
            upload_file(test_file)

    @pytest.mark.parametrize("size_mb", [1, 5, 10])
    def test_different_file_sizes(self, tmp_path: Path, size_mb: int) -> None:
        """Test uploading files of different sizes."""
        test_file = tmp_path / f"test_{size_mb}mb.txt"
        with test_file.open("wb") as f:
            f.write(b"0" * (size_mb * 1024 * 1024))

        with patch("twat_fs.upload_providers.s3.get_provider") as mock_provider:
            client = MagicMock()
            client.upload_file.return_value = TEST_URL
            mock_provider.return_value = client

            url = upload_file(test_file, provider="s3")
            assert url == TEST_URL

            client.upload_file.assert_called_once_with(
                local_path=test_file,
                remote_path=None,
                unique=False,
                force=False,
                upload_path=None,
            )


class TestCatboxProvider:
    """Test Catbox provider functionality."""

    def test_catbox_auth_with_userhash(self):
        """Test Catbox provider with userhash."""
        provider = catbox.CatboxProvider({"userhash": "test_hash"})
        assert provider.userhash == "test_hash"

    def test_catbox_auth_without_userhash(self):
        """Test Catbox provider without userhash."""
        provider = catbox.CatboxProvider()
        assert provider.userhash is None

    @pytest.mark.asyncio
    async def test_catbox_upload_file(self, tmp_path):
        """Test file upload to Catbox."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value="https://files.catbox.moe/abc123.txt"
        )

        mock_session = AsyncMock()
        mock_session.post = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch("aiohttp.ClientSession", return_value=mock_session):
            provider = catbox.CatboxProvider()
            result = await provider.async_upload_file(
                test_file,
                remote_path=None,
                unique=False,
                force=False,
                upload_path=None,
            )
            assert isinstance(result, UploadResult)
            assert result.url == "https://files.catbox.moe/abc123.txt"

    @pytest.mark.asyncio
    async def test_catbox_upload_url(self):
        """Test URL upload to Catbox."""
        test_url = "https://example.com/image.jpg"

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value="https://files.catbox.moe/xyz789.jpg"
        )

        mock_session = AsyncMock()
        mock_session.post = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch("aiohttp.ClientSession", return_value=mock_session):
            provider = catbox.CatboxProvider({"userhash": "test_hash"})
            result = await provider.async_upload_url(
                test_url,
                unique=False,
                force=False,
            )
            assert isinstance(result, UploadResult)
            assert result.url == "https://files.catbox.moe/xyz789.jpg"


class TestLitterboxProvider:
    """Test Litterbox provider functionality."""

    def test_litterbox_default_expiration(self):
        """Test default expiration time."""
        provider = litterbox.LitterboxProvider()
        assert provider.default_expiration == litterbox.ExpirationTime.HOURS_12

    def test_litterbox_custom_expiration(self):
        """Test custom expiration time."""
        provider = litterbox.LitterboxProvider(
            default_expiration=litterbox.ExpirationTime.HOURS_24
        )
        assert provider.default_expiration == litterbox.ExpirationTime.HOURS_24

    def test_litterbox_invalid_expiration(self):
        """Test invalid expiration time."""
        with pytest.raises(ValueError):
            litterbox.LitterboxProvider(default_expiration="invalid")

    @pytest.mark.asyncio
    async def test_litterbox_upload_file(self, tmp_path):
        """Test file upload to Litterbox."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value="https://litterbox.catbox.moe/abc123.txt"
        )

        mock_session = AsyncMock()
        mock_session.post = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch("aiohttp.ClientSession", return_value=mock_session):
            provider = litterbox.LitterboxProvider()
            result = await provider.async_upload_file(
                test_file,
                remote_path=None,
                unique=False,
                force=False,
                upload_path=None,
                expiration=litterbox.ExpirationTime.HOURS_12,
            )
            assert isinstance(result, UploadResult)
            assert result.url == "https://litterbox.catbox.moe/abc123.txt"


def test_circular_fallback(
    test_file: Path,
    mock_s3_provider: MagicMock,
    mock_dropbox_provider: MagicMock,
    mock_catbox_provider: MagicMock,
) -> None:
    """Test circular fallback when providers fail."""
    # Make all providers fail once
    mock_s3_provider.upload_file.side_effect = RetryableError("S3 failed", "s3")
    mock_dropbox_provider.upload_file.side_effect = RetryableError(
        "Dropbox failed", "dropbox"
    )
    mock_catbox_provider.upload_file.side_effect = [
        RetryableError("Catbox failed first", "catbox"),  # First try fails
        "https://catbox.moe/success.txt",  # Second try succeeds
    ]

    # Try upload starting with S3
    url = upload_file(test_file, provider="s3")
    assert url == "https://catbox.moe/success.txt"

    # Verify the circular fallback order
    assert mock_s3_provider.upload_file.call_count == 1
    assert mock_dropbox_provider.upload_file.call_count == 1
    assert mock_catbox_provider.upload_file.call_count == 2


def test_fragile_mode(
    test_file: Path,
    mock_s3_provider: MagicMock,
) -> None:
    """Test that fragile mode fails immediately without fallback."""
    # Make S3 provider fail
    mock_s3_provider.upload_file.side_effect = RetryableError("S3 failed", "s3")

    # Should raise immediately in fragile mode
    with pytest.raises(NonRetryableError) as exc_info:
        upload_file(test_file, provider="s3", fragile=True)

    assert "S3 failed" in str(exc_info.value)
    assert mock_s3_provider.upload_file.call_count == 1


def test_custom_provider_list_circular_fallback(
    test_file: Path,
    mock_s3_provider: MagicMock,
    mock_dropbox_provider: MagicMock,
    mock_catbox_provider: MagicMock,
) -> None:
    """Test circular fallback with custom provider list."""
    # Make providers fail in sequence
    mock_catbox_provider.upload_file.side_effect = RetryableError(
        "Catbox failed", "catbox"
    )
    mock_s3_provider.upload_file.side_effect = RetryableError("S3 failed", "s3")
    mock_dropbox_provider.upload_file.side_effect = [
        RetryableError("Dropbox failed first", "dropbox"),  # First try fails
        "https://dropbox.com/success.txt",  # Second try succeeds
    ]

    # Try upload with custom provider list: ["catbox", "s3", "dropbox"]
    url = upload_file(test_file, provider=["catbox", "s3", "dropbox"])
    assert url == "https://dropbox.com/success.txt"

    # Verify the circular fallback order
    assert mock_catbox_provider.upload_file.call_count == 1
    assert mock_s3_provider.upload_file.call_count == 1
    assert mock_dropbox_provider.upload_file.call_count == 2
