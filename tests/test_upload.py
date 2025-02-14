#!/usr/bin/env python3
# this_file: tests/test_upload.py

"""
Tests for the upload functionality.
"""

import os
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from twat_fs.upload import upload_file, PROVIDERS_PREFERENCE
from twat_fs.upload_providers import fal, dropbox

# Test data
TEST_FILE = Path(__file__).parent / "data" / "test.txt"
TEST_URL = "https://example.com/test.txt"


@pytest.fixture
def test_file(tmp_path):
    """Create a temporary test file."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")
    return file_path


@pytest.fixture
def mock_fal_provider():
    """Mock FAL provider."""
    with patch("twat_fs.upload_providers.fal.upload_file") as mock_upload:
        with patch("twat_fs.upload_providers.fal.provider_auth") as mock_auth:
            mock_upload.return_value = TEST_URL
            mock_auth.return_value = True
            yield mock_upload


@pytest.fixture
def mock_dropbox_provider():
    """Mock Dropbox provider."""
    with patch("twat_fs.upload_providers.dropbox.upload_file") as mock_upload:
        with patch("twat_fs.upload_providers.dropbox.provider_auth") as mock_auth:
            mock_upload.return_value = TEST_URL
            mock_auth.return_value = True
            yield mock_upload


class TestProviderAuth:
    """Test provider authentication functions."""

    def test_fal_auth_with_key(self, monkeypatch):
        """Test FAL auth when key is present."""
        monkeypatch.setenv("FAL_KEY", "test_key")
        assert fal.provider_auth() is True

    def test_fal_auth_without_key(self, monkeypatch):
        """Test FAL auth when key is missing."""
        monkeypatch.delenv("FAL_KEY", raising=False)
        assert fal.provider_auth() is False

    def test_dropbox_auth_with_token(self, monkeypatch):
        """Test Dropbox auth when token is present."""
        monkeypatch.setenv("DROPBOX_APP_TOKEN", "test_token")
        assert dropbox.provider_auth() is True

    def test_dropbox_auth_without_token(self, monkeypatch):
        """Test Dropbox auth when token is missing."""
        monkeypatch.delenv("DROPBOX_APP_TOKEN", raising=False)
        assert dropbox.provider_auth() is False


class TestUploadFile:
    """Test the main upload_file function."""

    def test_upload_with_default_provider(self, test_file, mock_fal_provider):
        """Test upload with default provider (FAL)."""
        url = upload_file(test_file)
        assert url == TEST_URL
        mock_fal_provider.assert_called_once_with(test_file)

    def test_upload_with_specific_provider(self, test_file, mock_dropbox_provider):
        """Test upload with specific provider."""
        url = upload_file(test_file, provider="dropbox")
        assert url == TEST_URL
        mock_dropbox_provider.assert_called_once_with(test_file)

    def test_upload_with_provider_list(
        self, test_file, mock_fal_provider, mock_dropbox_provider
    ):
        """Test upload with list of providers."""
        url = upload_file(test_file, provider=["fal", "dropbox"])
        assert url == TEST_URL
        mock_fal_provider.assert_called_once_with(test_file)
        mock_dropbox_provider.assert_not_called()

    def test_upload_fallback_on_auth_failure(
        self, test_file, mock_fal_provider, mock_dropbox_provider
    ):
        """Test fallback to next provider when auth fails."""
        with patch("twat_fs.upload_providers.fal.provider_auth", return_value=False):
            url = upload_file(test_file, provider=PROVIDERS_PREFERENCE)
            assert url == TEST_URL
            mock_fal_provider.assert_not_called()
            mock_dropbox_provider.assert_called_once_with(test_file)

    def test_upload_fallback_on_upload_failure(
        self, test_file, mock_fal_provider, mock_dropbox_provider
    ):
        """Test fallback to next provider when upload fails."""
        mock_fal_provider.side_effect = Exception("Upload failed")
        url = upload_file(test_file, provider=PROVIDERS_PREFERENCE)
        assert url == TEST_URL
        mock_fal_provider.assert_called_once_with(test_file)
        mock_dropbox_provider.assert_called_once_with(test_file)

    def test_all_providers_fail(self, test_file):
        """Test error when all providers fail."""
        with pytest.raises(ValueError) as exc_info:
            with patch(
                "twat_fs.upload_providers.fal.provider_auth", return_value=False
            ):
                with patch(
                    "twat_fs.upload_providers.dropbox.provider_auth", return_value=False
                ):
                    upload_file(test_file)
        assert "All providers failed" in str(exc_info.value)

    def test_invalid_provider(self, test_file):
        """Test error with invalid provider."""
        with pytest.raises(ValueError) as exc_info:
            upload_file(test_file, provider="invalid")
        assert "Unsupported provider" in str(exc_info.value)
