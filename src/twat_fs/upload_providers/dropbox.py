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
    "deps": """Additional setup needed:
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

    def __init__(self, dbx: Any):
        """Initialize with a Dropbox client instance."""
        self.dbx = dbx

    def _refresh_token_if_needed(self) -> None:
        """
        Check if token needs refresh and handle it.
        """
        import dropbox

        try:
            # Try a simple API call to test token
            self.dbx.check_user()
        except dropbox.exceptions.AuthError as e:
            logger.warning(f"Auth error, attempting token refresh: {e}")
            try:
                self.dbx.refresh_access_token()
                logger.debug("Successfully refreshed access token")
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                raise DropboxUploadError("Failed to refresh access token") from e

    def upload_file(
        self,
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
        from tenacity import (
            retry,
            stop_after_attempt,
            wait_exponential,
            retry_if_exception_type,
        )

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
            if remote_path is None:
                remote_path = path.name
            else:
                remote_path = str(remote_path)

            # Add timestamp for unique filenames
            if unique:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                name, ext = os.path.splitext(remote_path)
                remote_path = f"{name}_{timestamp}{ext}"

            # Construct full Dropbox path
            db_path = _normalize_path(os.path.join(upload_path, remote_path))
            logger.debug(f"Target Dropbox path: {db_path}")

            # Ensure upload directory exists (with retry)
            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=4, max=10),
                retry=retry_if_exception_type(dropbox.exceptions.ApiError),
            )
            def ensure_dir():
                _ensure_upload_directory(self.dbx, upload_path)

            ensure_dir()

            # Check if file exists and get metadata
            exists, remote_metadata = _check_file_exists(self.dbx, db_path)

            if exists and not force:
                # Get local file size
                local_size = os.path.getsize(path)

                # If sizes match, return existing URL
                if remote_metadata and remote_metadata["size"] == local_size:
                    logger.debug(
                        f"File {db_path} already exists with identical size, reusing URL"
                    )
                    if url := _get_share_url(self.dbx, db_path):
                        if direct_url := _get_download_url(url):
                            return direct_url
                        return url

                # Sizes don't match - we'll replace the file
                logger.debug(
                    f"File {db_path} exists with different size (local: {local_size}, remote: {remote_metadata['size'] if remote_metadata else 'unknown'}), replacing"
                )

            # Upload file based on size
            file_size = os.path.getsize(path)
            if file_size <= SMALL_FILE_THRESHOLD:
                _upload_small_file(self.dbx, path, db_path)
            else:
                _upload_large_file(self.dbx, path, db_path, MAX_FILE_SIZE)

            # Get shareable link (with retry)
            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=4, max=10),
                retry=retry_if_exception_type(dropbox.exceptions.ApiError),
            )
            def get_url():
                logger.debug("Getting share URL")
                if url := _get_share_url(self.dbx, db_path):
                    if direct_url := _get_download_url(url):
                        logger.debug(f"Generated direct download URL: {direct_url}")
                        return direct_url
                    logger.debug(f"Generated share URL: {url}")
                    return url
                return None

            if url := get_url():
                return url

            msg = "Failed to get share URL"
            raise DropboxUploadError(msg)

        except dropbox.exceptions.ApiError as e:
            _handle_api_error(e, "upload")
        except DropboxUploadError:
            raise
        except Exception as e:
            msg = f"Failed to upload file: {e}"
            raise DropboxUploadError(msg) from e


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

    logger.debug("Found Dropbox access token")
    creds = {
        "access_token": access_token,
        "refresh_token": os.getenv("DROPBOX_REFRESH_TOKEN"),
        "app_key": os.getenv("DROPBOX_APP_KEY"),
        "app_secret": os.getenv("DROPBOX_APP_SECRET"),
    }
    logger.debug(
        f"Dropbox credentials: refresh_token={bool(creds['refresh_token'])}, app_key={bool(creds['app_key'])}, app_secret={bool(creds['app_secret'])}"
    )
    return creds


def get_provider(credentials: DropboxCredentials | None = None) -> Any:
    """
    Initialize and return the Dropbox provider client.
    This function handles importing dependencies and creating the client.

    Args:
        credentials: Optional credentials to use. If None, will call get_credentials()

    Returns:
        Any: Dropbox client if successful

    Raises:
        ValueError: If authentication fails or credentials are invalid
    """
    logger.debug("Initializing Dropbox provider")
    if credentials is None:
        credentials = get_credentials()

    if not credentials:
        msg = "Dropbox credentials not found"
        raise ValueError(msg)

    try:
        import dropbox

        logger.debug("Successfully imported dropbox package")

        # Initialize client with credentials
        logger.debug("Creating Dropbox client")
        dbx = dropbox.Dropbox(
            oauth2_access_token=credentials["access_token"],
            oauth2_refresh_token=credentials["refresh_token"],
            app_key=credentials["app_key"],
            app_secret=credentials["app_secret"],
        )

        # Test connection
        try:
            logger.debug("Testing Dropbox connection")
            dbx.users_get_current_account()
            logger.debug("Successfully authenticated with Dropbox")
            return DropboxClient(dbx)  # Return our wrapped client
        except dropbox.exceptions.AuthError as e:
            msg = f"Dropbox authentication failed: {e}"
            logger.error(msg)
            raise ValueError(msg) from e
        except Exception as e:
            msg = f"Failed to connect to Dropbox: {e}"
            logger.error(msg)
            raise ValueError(msg) from e

    except ImportError as e:
        msg = "Failed to import dropbox package. Please install it with: pip install dropbox"
        logger.error(msg)
        raise ValueError(msg) from e
    except Exception as e:
        msg = f"Failed to initialize Dropbox client: {e}"
        logger.error(msg)
        raise ValueError(msg) from e


# Make the module implement the Provider protocol
def upload_file(
    file_path: str | Path,
    remote_path: str | Path | None = None,
    force: bool = False,
    unique: bool = False,
    upload_path: str = DEFAULT_UPLOAD_PATH,
) -> str:
    """
    Upload a file using this provider.

    Args:
        file_path: Path to the file to upload
        remote_path: Optional remote path to use
        force: Whether to overwrite existing files
        unique: Whether to ensure unique filenames
        upload_path: Base upload path in Dropbox

    Returns:
        str: URL to the uploaded file

    Raises:
        ValueError: If upload fails
        FileNotFoundError: If file does not exist
        PermissionError: If file cannot be read
        DropboxFileExistsError: If file already exists and force is False
    """
    client = get_provider()
    if not client:
        msg = "Failed to initialize Dropbox provider"
        raise ValueError(msg)

    # Use the original filename if no remote path specified
    if remote_path is None:
        remote_path = Path(file_path).name

    try:
        return client.upload_file(
            file_path, remote_path, force=force, unique=unique, upload_path=upload_path
        )
    except DropboxFileExistsError as e:
        # Provide a more helpful error message
        msg = (
            f"File already exists in Dropbox. Use --force to overwrite, "
            f"or use --unique to create a unique filename. Error: {e}"
        )
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

    logger.debug(f"Ensuring upload directory exists: {upload_path}")

    try:
        # Try to create directory and ancestors
        try:
            logger.debug(f"Attempting to create directory: {upload_path}")
            dbx.files_create_folder_v2(upload_path)
            logger.debug(f"Successfully created directory: {upload_path}")
        except dropbox.exceptions.ApiError as e:
            # Handle folder already exists case
            if isinstance(e.error, dropbox.files.CreateFolderError):
                if e.error.get_path().is_conflict():
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


def _upload_small_file(dbx: Any, file_path: Path, db_path: str) -> None:
    """
    Upload a small file to Dropbox.

    Args:
        dbx: Dropbox client
        file_path: Local file path
        db_path: Dropbox path

    Raises:
        DropboxUploadError: If upload fails
    """
    import dropbox

    logger.debug(f"Uploading small file: {file_path} -> {db_path}")

    try:
        with open(file_path, "rb") as f:
            dbx.files_upload(f.read(), db_path, mode=dropbox.files.WriteMode.overwrite)
        logger.debug(f"Successfully uploaded small file: {db_path}")
    except Exception as e:
        logger.error(f"Failed to upload small file: {e}")
        raise DropboxUploadError(f"Failed to upload file: {e}") from e


def _upload_large_file(
    dbx: Any, file_path: Path, db_path: str, chunk_size: int
) -> None:
    """
    Upload a large file to Dropbox using chunked upload.

    Args:
        dbx: Dropbox client
        file_path: Local file path
        db_path: Dropbox path
        chunk_size: Size of each chunk in bytes

    Raises:
        DropboxUploadError: If upload fails
    """
    import dropbox

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
        raise DropboxUploadError(f"Failed to upload file: {e}") from e


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

    if isinstance(e, dropbox.exceptions.AuthError):
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
