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

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict
from urllib import parse

import dropbox  # type: ignore
from dropbox.exceptions import AuthError
from dotenv import load_dotenv
from loguru import logger

# Provider-specific help messages
PROVIDER_HELP = {
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
    "deps": """Setup requirements:
1. Install the Dropbox SDK: pip install dropbox
2. If using OAuth2:
   - Set up your redirect URI in the app console
   - Implement the OAuth2 flow to get refresh tokens""",
}

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


class DropboxClient:
    """Wrapper around Dropbox client that implements our ProviderClient protocol."""

    def __init__(self, credentials: DropboxCredentials) -> None:
        """Initialize the Dropbox client."""
        self.credentials = credentials
        self.dbx = self._create_client()

    def _create_client(self) -> dropbox.Dropbox:
        """Create and return a Dropbox client instance."""
        return dropbox.Dropbox(
            oauth2_access_token=self.credentials["access_token"],
            oauth2_refresh_token=self.credentials["refresh_token"],
            app_key=self.credentials["app_key"],
        )

    def _refresh_token_if_needed(self) -> None:
        """Refresh the access token if needed and possible."""
        try:
            # Check current token
            self.dbx.users_get_current_account()
        except AuthError as e:
            if "expired_access_token" in str(e):
                if not (
                    self.credentials["refresh_token"] and self.credentials["app_key"]
                ):
                    logger.debug(
                        "\n".join(
                            [
                                "Cannot refresh token:",
                                "- Missing refresh token or app key",
                                "- Set DROPBOX_REFRESH_TOKEN and DROPBOX_APP_KEY to enable automatic refresh",
                            ]
                        )
                    )
                    return
                logger.debug("Access token expired, attempting refresh")
                try:
                    self.dbx.refresh_access_token()
                except Exception as refresh_err:
                    logger.debug(f"Unable to refresh access token: {refresh_err}")
            else:
                logger.debug(f"Authentication error: {e}")

    def upload_file(
        self,
        file_path: str | Path,
        remote_path: str | Path | None = None,
        *,
        force: bool = False,
        unique: bool = False,
        upload_path: str = DEFAULT_UPLOAD_PATH,
    ) -> str:
        """Upload a file to Dropbox and return its URL."""
        logger.debug(f"Starting upload process for {file_path}")

        path = Path(file_path)
        if not path.exists():
            msg = f"File {path} does not exist"
            raise FileNotFoundError(msg)

        if not os.access(path, os.R_OK):
            msg = f"File {path} cannot be read"
            raise PermissionError(msg)

        try:
            # Check and refresh token if needed
            self._refresh_token_if_needed()

            # Normalize paths
            upload_path = _normalize_path(upload_path)

            # Use original filename if no remote path specified
            remote_path = path.name if remote_path is None else str(remote_path)

            # Add timestamp for unique filenames
            if unique:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                name, ext = os.path.splitext(remote_path)
                remote_path = f"{name}_{timestamp}{ext}"

            # Construct full Dropbox path
            db_path = _normalize_path(os.path.join(upload_path, remote_path))
            logger.debug(f"Target Dropbox path: {db_path}")

            # Ensure upload directory exists
            _ensure_upload_directory(self.dbx, upload_path)

            # Check if file exists
            exists, remote_metadata = _check_file_exists(self.dbx, db_path)
            if exists and not force:
                msg = f"File already exists at {db_path}"
                raise DropboxFileExistsError(msg)

            # Upload file based on size
            file_size = os.path.getsize(path)
            if file_size <= SMALL_FILE_THRESHOLD:
                _upload_small_file(self.dbx, path, db_path)
            else:
                _upload_large_file(self.dbx, path, db_path, SMALL_FILE_THRESHOLD)

            # Get shareable URL
            url = _get_share_url(self.dbx, db_path)
            if not url:
                msg = "Failed to get share URL"
                raise DropboxUploadError(msg)

            logger.info(f"Successfully uploaded to Dropbox: {url}")
            return url

        except DropboxFileExistsError:
            raise
        except Exception as e:
            logger.error(f"Failed to upload to Dropbox: {e}")
            msg = f"Upload failed: {e}"
            raise DropboxUploadError(msg) from e

    def get_account_info(self) -> None:
        """Get account information from Dropbox."""
        try:
            self.dbx.users_get_current_account()
        except AuthError as e:
            logger.error(f"Failed to get account info: {e}")
            raise


def get_credentials() -> DropboxCredentials | None:
    """Get Dropbox credentials from environment variables."""
    access_token = os.getenv("DROPBOX_ACCESS_TOKEN")
    if not access_token:
        logger.debug("DROPBOX_ACCESS_TOKEN environment variable not set")
        return None

    creds: DropboxCredentials = {
        "access_token": access_token,
        "refresh_token": os.getenv("DROPBOX_REFRESH_TOKEN"),
        "app_key": os.getenv("DROPBOX_APP_KEY"),
        "app_secret": os.getenv("DROPBOX_APP_SECRET"),
    }
    return creds


def get_provider() -> DropboxClient | None:
    """Initialize and return a Dropbox client if credentials are available."""
    try:
        credentials = get_credentials()
        if not credentials:
            return None

        client = DropboxClient(credentials)
        # Test the client by trying to get account info
        try:
            client.get_account_info()
            return client
        except AuthError as e:
            if "expired_access_token" in str(e):
                if not (credentials["refresh_token"] and credentials["app_key"]):
                    logger.warning(
                        "\n".join(
                            [
                                "Dropbox token has expired and cannot be refreshed automatically.",
                                "To enable automatic token refresh:",
                                "1. Set DROPBOX_REFRESH_TOKEN environment variable",
                                "2. Set DROPBOX_APP_KEY environment variable",
                                "For now, please generate a new access token.",
                            ]
                        )
                    )
                else:
                    logger.error(
                        "Dropbox access token has expired. Please generate a new token."
                    )
            else:
                logger.error(f"Dropbox authentication failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Dropbox client: {e}")
            return None

    except Exception as e:
        logger.error(f"Error initializing Dropbox client: {e}")
        return None


def upload_file(
    file_path: str | Path,
    remote_path: str | Path | None = None,
    *,
    force: bool = False,
    unique: bool = False,
    upload_path: str = DEFAULT_UPLOAD_PATH,
) -> str:
    """
    Upload a file to Dropbox and return its URL.

    Args:
        file_path: Path to the file to upload
        remote_path: Optional remote path to use
        force: Whether to overwrite existing files
        unique: Whether to ensure unique filenames
        upload_path: Custom base upload path

    Returns:
        str: URL to the uploaded file

    Raises:
        ValueError: If upload fails or credentials are invalid
    """
    client = get_provider()
    if not client:
        help_info = PROVIDER_HELP["setup"]
        msg = f"Dropbox credentials not found. {help_info}"
        raise ValueError(msg)

    # Use the original filename if no remote path specified
    if remote_path is None:
        remote_path = Path(file_path).name

    try:
        return client.upload_file(
            file_path,
            remote_path,
            force=force,
            unique=unique,
            upload_path=upload_path,
        )
    except DropboxFileExistsError as e:
        # Provide a more helpful error message
        msg = (
            f"File already exists in Dropbox. Use --force to overwrite, "
            f"or use --unique to create a unique filename. Error: {e}"
        )
        raise ValueError(msg) from e
    except DropboxUploadError as e:
        if "expired_access_token" in str(e):
            msg = "Failed to initialize Dropbox client: expired_access_token"
        else:
            msg = f"Failed to initialize Dropbox client: {e}"
        raise ValueError(msg) from e
    except Exception as e:
        msg = f"Failed to upload file: {e}"
        raise ValueError(msg) from e


class DropboxUploadError(Exception):
    """Base class for Dropbox upload errors."""


class PathConflictError(DropboxUploadError):
    """Raised when a path conflict occurs in safe mode."""


class DropboxFileExistsError(Exception):
    """Raised when a file already exists in Dropbox."""

    def __init__(self, message: str, url: str | None = None):
        super().__init__(message)
        self.url = url


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
    """
    Convert a Dropbox share URL to a direct download URL.
    Preserves existing query parameters and adds dl=1 for direct download.

    Args:
        url: The Dropbox share URL to convert

    Returns:
        str | None: Direct download URL if successful, None otherwise
    """
    try:
        parsed = parse.urlparse(url)
        # Get existing query parameters
        query = dict(parse.parse_qsl(parsed.query))
        # Add or update dl parameter
        query["dl"] = "1"
        # Reconstruct URL with updated query
        return parsed._replace(
            netloc="dl.dropboxusercontent.com", query=parse.urlencode(query)
        ).geturl()
    except Exception as e:
        logger.error(f"Failed to generate download URL: {e}")
        return None


def _get_share_url(dbx: dropbox.Dropbox, db_path: str) -> str:
    """Get a shareable link for the uploaded file."""
    from tenacity import retry, stop_after_attempt, wait_exponential

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    def get_url() -> str:
        try:
            shared_link = dbx.sharing_create_shared_link_with_settings(db_path)
            # Convert to direct download URL
            url = shared_link.url.replace("?dl=0", "?dl=1")
            logger.debug(f"Created share URL: {url}")
            return url
        except Exception as e:
            logger.error(f"Failed to create share URL: {e}")
            raise

    return get_url()


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

    logger.debug(f"Ensuring upload directory exists: {upload_path}")

    try:
        # Try to create directory and ancestors
        try:
            logger.debug(f"Attempting to create directory: {upload_path}")
            dbx.files_create_folder_v2(upload_path)
            logger.debug(f"Successfully created directory: {upload_path}")
        except dropbox.exceptions.ApiError as e:
            # Handle folder already exists case
            if (
                isinstance(e.error, dropbox.files.CreateFolderError)
                and e.error.get_path().is_conflict()
            ):
                logger.debug(f"Directory already exists: {upload_path}")
                return
            # For other API errors, raise
            logger.error(f"Failed to create directory: {e}")
            raise
    except Exception as e:
        msg = f"Failed to create upload directory: {e}"
        raise DropboxUploadError(msg) from e


def _get_file_metadata(dbx: Any, db_path: str) -> dict | None:
    """
    Get metadata for a file in Dropbox.

    Args:
        dbx: Dropbox client instance
        db_path: Path to the file in Dropbox

    Returns:
        dict | None: File metadata including size if file exists, None otherwise
    """
    import dropbox

    try:
        metadata = dbx.files_get_metadata(db_path)
        return {
            "size": metadata.size,
            "path": metadata.path_display,
            "id": metadata.id,
        }
    except dropbox.exceptions.ApiError as e:
        if e.error.is_path() and e.error.get_path().is_not_found():
            return None
        raise


def _check_file_exists(dbx: Any, db_path: str) -> tuple[bool, dict | None]:
    """
    Check if a file exists in Dropbox and return its metadata.

    Args:
        dbx: Dropbox client instance
        db_path: Path to the file in Dropbox

    Returns:
        tuple[bool, dict | None]: (exists, metadata)
        - exists: True if file exists
        - metadata: File metadata if exists, None otherwise
    """
    try:
        if metadata := _get_file_metadata(dbx, db_path):
            return True, metadata
        return False, None
    except Exception as e:
        logger.warning(f"Error checking file existence: {e}")
        return False, None


def _upload_small_file(dbx: dropbox.Dropbox, file_path: Path, db_path: str) -> None:
    """Upload a small file to Dropbox."""
    logger.debug(f"Uploading small file: {file_path} -> {db_path}")
    try:
        with open(file_path, "rb") as f:
            dbx.files_upload(f.read(), db_path, mode=dropbox.files.WriteMode.overwrite)
        logger.debug(f"Successfully uploaded small file: {db_path}")
    except Exception as e:
        logger.error(f"Failed to upload small file: {e}")
        msg = f"Failed to upload file: {e}"
        raise DropboxUploadError(msg) from e


def _upload_large_file(
    dbx: dropbox.Dropbox, file_path: Path, db_path: str, chunk_size: int
) -> None:
    """Upload a large file to Dropbox using chunked upload."""
    logger.debug(f"Starting chunked upload: {file_path} -> {db_path}")
    file_size = os.path.getsize(file_path)
    try:
        with open(file_path, "rb") as f:
            upload_session_start_result = dbx.files_upload_session_start(
                f.read(chunk_size)
            )
            logger.debug("Upload session started")

            cursor = dropbox.files.UploadSessionCursor(
                session_id=upload_session_start_result.session_id,
                offset=f.tell(),
            )
            commit = dropbox.files.CommitInfo(
                path=db_path, mode=dropbox.files.WriteMode.overwrite
            )

            while f.tell() < file_size:
                if (file_size - f.tell()) <= chunk_size:
                    logger.debug("Uploading final chunk")
                    dbx.files_upload_session_finish(f.read(chunk_size), cursor, commit)
                else:
                    logger.debug(f"Uploading chunk at offset {cursor.offset}")
                    dbx.files_upload_session_append_v2(f.read(chunk_size), cursor)
                    cursor.offset = f.tell()

        logger.debug(f"Successfully uploaded large file: {db_path}")
    except Exception as e:
        logger.error(f"Failed to upload large file: {e}")
        msg = f"Failed to upload file: {e}"
        raise DropboxUploadError(msg) from e


def _normalize_path(path: str) -> str:
    """
    Normalize a path for Dropbox (use forward slashes, no leading slash).

    Args:
        path: Path to normalize

    Returns:
        str: Normalized path
    """
    # Convert backslashes to forward slashes
    normalized = path.replace("\\", "/")
    # Remove leading slash if present
    normalized = normalized.lstrip("/")
    # Add leading slash back (Dropbox paths must start with slash)
    return f"/{normalized}"


def _handle_api_error(e: Any, operation: str) -> None:
    """
    Handle Dropbox API errors with proper error messages and logging.

    Args:
        e: The API error
        operation: Description of the operation that failed

    Raises:
        DropboxUploadError: With appropriate error message
    """
    import dropbox

    if isinstance(e, AuthError):
        logger.error(f"Authentication error during {operation}: {e}")
        msg = "Authentication failed. Please check your access token or refresh your credentials."
        raise DropboxUploadError(msg) from e
    elif isinstance(e, dropbox.exceptions.ApiError):
        if e.error.is_path():
            path_error = e.error.get_path()
            if path_error.is_not_found():
                logger.error(f"Path not found during {operation}: {e}")
                msg = f"Path not found: {path_error}"
                raise DropboxUploadError(msg) from e
            elif path_error.is_not_file():
                logger.error(f"Not a file error during {operation}: {e}")
                msg = f"Not a file: {path_error}"
                raise DropboxUploadError(msg) from e
            elif path_error.is_conflict():
                logger.error(f"Path conflict during {operation}: {e}")
                msg = f"Path conflict: {path_error}"
                raise DropboxUploadError(msg) from e
        logger.error(f"API error during {operation}: {e}")
        msg = f"Dropbox API error: {e}"
        raise DropboxUploadError(msg) from e
    else:
        logger.error(f"Unexpected error during {operation}: {e}")
        msg = f"Unexpected error: {e}"
        raise DropboxUploadError(msg) from e


def _validate_credentials(credentials: DropboxCredentials) -> None:
    """Validate Dropbox credentials."""
    # ... existing code ...


def _get_client(credentials: DropboxCredentials) -> Any:
    """Get Dropbox client instance."""
    # ... existing code ...


def _refresh_token(credentials: DropboxCredentials) -> DropboxCredentials | None:
    """Attempt to refresh the access token."""
    # ... existing code ...
