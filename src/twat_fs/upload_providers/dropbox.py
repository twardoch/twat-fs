#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "dropbox",
#   "python-dotenv",
#   "tenacity",
#   "loguru",
# ]
# ///
# this_file: src/twat_fs/upload_providers/dropbox.py

"""
Dropbox provider for file uploads.
This module provides functionality to upload files to Dropbox and get shareable links.
Supports optional force and unique upload modes, chunked uploads for large files, and custom upload paths.
"""

import os
from typing import TypedDict, Any
from urllib import parse
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
from loguru import logger


load_dotenv()

# Constants
DEFAULT_UPLOAD_PATH = "/upload"
MAX_FILE_SIZE = 150 * 1024 * 1024  # 150MB
SMALL_FILE_THRESHOLD = 4 * 1024 * 1024  # 4MB threshold for chunked upload


class DropboxCredentials(TypedDict):
    """Type for Dropbox credentials and configuration."""

    access_token: str
    refresh_token: str | None
    app_key: str | None
    app_secret: str | None


def get_credentials() -> DropboxCredentials | None:
    """
    Get Dropbox credentials from environment variables.
    This function only checks environment variables and returns them,
    without importing or initializing any external dependencies.

    Returns:
        Optional[DropboxCredentials]: Credentials if access token is present, None otherwise
    """
    access_token = os.getenv("DROPBOX_ACCESS_TOKEN")
    if not access_token:
        logger.debug("DROPBOX_ACCESS_TOKEN environment variable not set")
        return None

    return {
        "access_token": access_token,
        "refresh_token": os.getenv("DROPBOX_REFRESH_TOKEN"),
        "app_key": os.getenv("DROPBOX_APP_KEY"),
        "app_secret": os.getenv("DROPBOX_APP_SECRET"),
    }


def get_provider(credentials: DropboxCredentials | None = None) -> Any:
    """
    Initialize and return the Dropbox provider client.
    This function handles importing dependencies and creating the client.

    Args:
        credentials: Optional credentials to use. If None, will call get_credentials()

    Returns:
        Any: Dropbox client if successful, None otherwise
    """
    if credentials is None:
        credentials = get_credentials()

    if not credentials:
        return None

    try:
        import dropbox

        # Initialize client with credentials
        dbx = dropbox.Dropbox(
            oauth2_access_token=credentials["access_token"],
            oauth2_refresh_token=credentials["refresh_token"],
            app_key=credentials["app_key"],
            app_secret=credentials["app_secret"],
        )

        # Test connection
        dbx.users_get_current_account()

        return dbx

    except Exception as e:
        logger.warning(f"Failed to initialize Dropbox provider: {e}")
        return None


class DropboxUploadError(Exception):
    """Base class for Dropbox upload errors."""


class PathConflictError(DropboxUploadError):
    """Raised when a path conflict occurs in safe mode."""


class DropboxFileExistsError(Exception):
    """Raised when a file already exists in Dropbox."""


class FolderExistsError(PathConflictError):
    """Raised when a folder exists where a file should be uploaded."""


def _validate_file(local_path: Path) -> None:
    """
    Validate file exists and can be read.

    Args:
        local_path: Path to the file to validate

    Raises:
        FileNotFoundError: If file does not exist
        PermissionError: If file cannot be read
    """
    if not get_provider():
        msg = "DROPBOX_ACCESS_TOKEN environment variable must be set"
        raise ValueError(msg)

    if not local_path.exists():
        msg = f"File {local_path} does not exist"
        raise FileNotFoundError(msg)

    if not os.access(local_path, os.R_OK):
        msg = f"File {local_path} cannot be read"
        raise PermissionError(msg)


def _get_download_url(url: str) -> str | None:
    """Extract direct download URL from Dropbox share URL."""
    try:
        parsed = parse.urlparse(url)
        if parsed.netloc == "www.dropbox.com":
            return url.replace("www.dropbox.com", "dl.dropboxusercontent.com")
    except Exception:
        pass
    return None


def _get_share_url(dbx: Any, db_path: str) -> str | None:
    """Get a shareable link for the uploaded file."""
    from tenacity import retry, stop_after_attempt, wait_exponential
    import dropbox

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def _share_with_retry():
        try:
            shared = dbx.sharing_create_shared_link_with_settings(db_path)
            return shared.url
        except dropbox.exceptions.ApiError as e:
            if e.error.is_shared_link_already_exists():
                links = dbx.sharing_list_shared_links(db_path).links
                if links:
                    return links[0].url
            raise

    try:
        return _share_with_retry()
    except Exception as e:
        logger.warning(f"Failed to create share link: {e}")
        return None


def _ensure_upload_directory(dbx: Any, upload_path: str) -> None:
    """
    Ensure the upload directory exists.

    Args:
        dbx: Dropbox client
        upload_path: Path to ensure exists

    Raises:
        DropboxUploadError: If directory cannot be created
    """
    import dropbox

    try:
        # Try to create directory and ancestors
        try:
            dbx.files_create_folder_v2(upload_path)
        except dropbox.exceptions.ApiError as e:
            if not e.error.is_path_write():
                raise
    except Exception as e:
        msg = f"Failed to create upload directory: {e}"
        raise DropboxUploadError(msg) from e


def upload_file(
    file_path: str | Path,
    remote_path: str | Path | None = None,
    force: bool = False,
    unique: bool = False,
    upload_path: str = DEFAULT_UPLOAD_PATH,
) -> str:
    """
    Upload a file to Dropbox.

    Args:
        file_path: Path to the file to upload
        remote_path: Optional remote path (relative to upload_path)
        force: Whether to overwrite existing files
        unique: Whether to ensure unique filenames
        upload_path: Base upload path in Dropbox

    Returns:
        str: URL to the uploaded file

    Raises:
        ValueError: If provider is not authenticated
        FileNotFoundError: If file does not exist
        PermissionError: If file cannot be read
        DropboxUploadError: If upload fails
    """
    import dropbox

    path = Path(file_path)
    _validate_file(path)

    # Get provider
    dbx = get_provider()
    if not dbx:
        msg = "Failed to initialize Dropbox provider"
        raise DropboxUploadError(msg)

    try:
        # Ensure upload directory exists
        _ensure_upload_directory(dbx, upload_path)

        # Determine remote path
        remote_name = str(remote_path) if remote_path else path.name

        if unique:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(remote_name)
            remote_name = f"{name}_{timestamp}{ext}"

        db_path = os.path.join(upload_path, remote_name)

        # Check if file exists
        try:
            dbx.files_get_metadata(db_path)
            if not force:
                msg = f"File {db_path} already exists"
                raise DropboxFileExistsError(msg)
        except dropbox.exceptions.ApiError as e:
            if not e.error.is_path_lookup():
                raise

        # Upload file
        chunk_size = MAX_FILE_SIZE
        file_size = os.path.getsize(path)

        with open(path, "rb") as f:
            if file_size <= SMALL_FILE_THRESHOLD:
                dbx.files_upload(
                    f.read(), db_path, mode=dropbox.files.WriteMode.overwrite
                )
            else:
                upload_session_start_result = dbx.files_upload_session_start(
                    f.read(chunk_size)
                )
                cursor = dropbox.files.UploadSessionCursor(
                    session_id=upload_session_start_result.session_id,
                    offset=f.tell(),
                )
                commit = dropbox.files.CommitInfo(
                    path=db_path, mode=dropbox.files.WriteMode.overwrite
                )

                while f.tell() < file_size:
                    if (file_size - f.tell()) <= chunk_size:
                        dbx.files_upload_session_finish(
                            f.read(chunk_size), cursor, commit
                        )
                    else:
                        dbx.files_upload_session_append_v2(f.read(chunk_size), cursor)
                        cursor.offset = f.tell()

        # Get shareable link
        if url := _get_share_url(dbx, db_path):
            if direct_url := _get_download_url(url):
                return direct_url
            return url

        msg = "Failed to get share URL"
        raise DropboxUploadError(msg)

    except Exception as e:
        msg = f"Failed to upload file: {e}"
        raise DropboxUploadError(msg) from e
