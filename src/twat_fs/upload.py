# this_file: src/twat_fs/upload.py

"""
Main upload module that provides a unified interface for uploading files
using different providers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TYPE_CHECKING, cast  # Added cast
from dataclasses import dataclass
from enum import Enum, auto
import hashlib
import requests
import time

from loguru import logger

from twat_fs.upload_providers import (
    PROVIDERS_PREFERENCE,
    get_provider_help,
    get_provider_module,
    Provider,
    RetryableError,
    NonRetryableError,
    UploadResult,
    ProviderFactory,
    ProviderHelp,  # Added import
)
from twat_fs.upload_providers.core import with_retry, RetryStrategy

if TYPE_CHECKING:
    from collections.abc import Sequence

# Type for provider specification - can be a single provider name or a list of providers
ProviderType = str | list[str] | None


@dataclass
class UploadOptions:
    """Options for file upload operations."""

    remote_path: str | Path | None = None
    unique: bool = False
    force: bool = False
    upload_path: str | None = None  # Note: CLI calls this remote_path in some contexts
    fragile: bool = False


class ProviderStatus(Enum):
    """Status of a provider's setup."""

    READY = auto()
    NEEDS_CONFIG = auto()
    NOT_AVAILABLE = auto()


@dataclass
class ProviderInfo:
    """Information about a provider's setup status."""

    success: bool
    explanation: str
    help_info: dict[str, str]
    timing: dict[str, float] | None = None


# Removed stub for _test_provider_online, full definition is later.


def _perform_test_upload_and_validation(
    client: Any,
    test_file: Path,
    _provider_name: str,  # Prefixed as unused in this specific helper after refactor
    original_hash: str,
    timing_metrics: dict[str, float],  # Base timing with start_time and read_duration
) -> tuple[bool, str, dict[str, float]]:
    """Helper to perform the upload, validation, and download verification part of the online test."""
    upload_start_time = 0.0
    upload_duration = 0.0
    validation_duration = 0.0
    url = ""

    try:
        upload_start_time = time.time()
        result = client.upload_file(test_file)
        upload_duration = time.time() - upload_start_time
        timing_metrics["upload_duration"] = upload_duration

        if not result:
            timing_metrics["end_time"] = time.time()
            timing_metrics["total_duration"] = timing_metrics["end_time"] - timing_metrics["start_time"]
            return False, "Upload failed", timing_metrics

        if isinstance(result, UploadResult):
            url = result.url
            # Potentially merge more detailed timing from provider if available
            if result.metadata.get("timing"):
                timing_metrics.update(result.metadata["timing"])
        else:
            url = result

        time.sleep(1.0)  # Propagation delay

        validation_start_time = time.time()
        response = requests.head(
            url,
            timeout=30,
            allow_redirects=True,
            headers={"User-Agent": "twat-fs/1.0"},
        )
        validation_duration = time.time() - validation_start_time
        timing_metrics["validation_duration"] = validation_duration

        if response.status_code not in (200, 201, 202, 203, 204):
            timing_metrics["end_time"] = time.time()
            timing_metrics["total_duration"] = timing_metrics["end_time"] - timing_metrics["start_time"]
            return (
                False,
                f"URL validation failed: status {response.status_code}",
                timing_metrics,
            )

    except ValueError as e:
        timing_metrics["upload_duration"] = time.time() - upload_start_time if upload_start_time else 0.0
        timing_metrics["end_time"] = time.time()
        timing_metrics["total_duration"] = timing_metrics["end_time"] - timing_metrics["start_time"]
        if "401" in str(e) or "authentication" in str(e).lower():
            return False, f"Authentication required: {e}", timing_metrics
        return False, f"Upload failed: {e}", timing_metrics
    except requests.RequestException as e:
        timing_metrics["validation_duration"] = (
            time.time() - validation_start_time if "validation_start_time" in locals() else 0.0
        )
        timing_metrics["end_time"] = time.time()
        timing_metrics["total_duration"] = timing_metrics["end_time"] - timing_metrics["start_time"]
        return False, f"URL validation failed: {e}", timing_metrics
    except Exception as e:  # Catch any other upload related error
        timing_metrics["upload_duration"] = time.time() - upload_start_time if upload_start_time else 0.0
        timing_metrics["end_time"] = time.time()
        timing_metrics["total_duration"] = timing_metrics["end_time"] - timing_metrics["start_time"]
        return False, f"Unexpected upload error: {e}", timing_metrics

    # Download and verify
    max_retries = 3
    retry_delay = 2.0
    last_error_message = "Download failed after retries"

    for attempt in range(max_retries):
        try:
            dl_response = requests.get(url, timeout=30)
            if dl_response.status_code == 200:
                downloaded_hash = hashlib.sha256(dl_response.content).hexdigest()
                if original_hash == downloaded_hash:
                    timing_metrics["end_time"] = time.time()
                    timing_metrics["total_duration"] = timing_metrics["end_time"] - timing_metrics["start_time"]
                    return True, "Online test passed successfully", timing_metrics
                else:
                    last_error_message = (
                        f"Content verification failed: original {original_hash}, downloaded {downloaded_hash}"
                    )
            else:
                last_error_message = f"Download failed with status {dl_response.status_code}"

            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
        except Exception as e:
            last_error_message = f"Download attempt {attempt + 1} failed: {e}"
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2

    timing_metrics["end_time"] = time.time()
    timing_metrics["total_duration"] = timing_metrics["end_time"] - timing_metrics["start_time"]
    return False, last_error_message, timing_metrics


def _verify_downloaded_file_hash(
    url: str, original_hash: str, timing_metrics: dict[str, float]
) -> tuple[bool, str, dict[str, float]]:
    """Downloads file from URL and verifies its hash against original_hash."""
    max_retries = 3
    retry_delay = 2.0
    last_error_message = "Download failed after retries"

    for attempt in range(max_retries):
        try:
            dl_response = requests.get(url, timeout=30)
            if dl_response.status_code == 200:
                downloaded_hash = hashlib.sha256(dl_response.content).hexdigest()
                if original_hash == downloaded_hash:
                    timing_metrics["end_time"] = time.time()  # Final end time
                    timing_metrics["total_duration"] = timing_metrics["end_time"] - timing_metrics["start_time"]
                    return True, "Online test passed successfully (download verified)", timing_metrics
                else:
                    last_error_message = (
                        f"Content verification failed: original {original_hash}, downloaded {downloaded_hash}"
                    )
            else:
                last_error_message = f"Download failed with status {dl_response.status_code}"

            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
        except Exception as e:
            last_error_message = f"Download attempt {attempt + 1} failed: {e}"
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2

    timing_metrics["end_time"] = time.time()  # Final end time if all retries fail
    timing_metrics["total_duration"] = timing_metrics["end_time"] - timing_metrics["start_time"]
    return False, last_error_message, timing_metrics


def _test_provider_online(
    provider_name: str,
) -> tuple[bool, str, dict[str, float] | None]:
    """
    Test a provider by uploading and downloading a small file.

    Args:
        provider_name: Name of the provider to test

    Returns:
        Tuple[bool, str, dict[str, float] | None]: (success, message, timing_metrics)
    """
    test_file = Path(__file__).parent / "data" / "test.jpg"
    if not test_file.exists():
        return False, f"Test file not found: {test_file}", None

    start_time = time.time()

    try:
        # Calculate original file hash
        with open(test_file, "rb") as f:
            original_hash = hashlib.sha256(f.read()).hexdigest()

        # Get the provider module and client using the factory
        provider_module = ProviderFactory.get_provider_module(provider_name)
        if not provider_module:
            return False, f"Provider module {provider_name} not found", None

        client = ProviderFactory.create_provider(provider_name)
        if not client:
            return False, f"Provider {provider_name} not configured", None

        # Track timing
        start_time = time.time()
        read_start = time.time()

        # Track file read time
        read_start_time = time.time()
        with open(test_file, "rb") as f:
            _ = f.read()  # Read file to measure read time
        read_duration = time.time() - read_start_time

        base_timing_metrics = {
            "start_time": start_time,  # Overall start time
            "read_duration": read_duration,
            "upload_duration": 0.0,
            "validation_duration": 0.0,
            "provider": float(hash(provider_name)),  # Keep provider hash for consistency if needed
            "end_time": 0.0,  # Will be set by helper or outer catch
            "total_duration": 0.0,  # Will be set by helper or outer catch
        }

        return _perform_test_upload_and_validation(client, test_file, provider_name, original_hash, base_timing_metrics)

    except Exception as e:
        # This catches errors during provider instantiation or initial file hashing
        current_time = time.time()
        final_timing_metrics: dict[str, float] = {
            "start_time": start_time,
            "end_time": current_time,
            "total_duration": current_time - start_time,
            "read_duration": 0.0,  # Could be set if read happened before error
            "upload_duration": 0.0,
            "validation_duration": 0.0,
            "provider": float(hash(provider_name)),
        }
        # Update read_duration if it was measured before exception
        if "read_duration" in locals() and "final_timing_metrics" in locals():
            final_timing_metrics["read_duration"] = read_duration

        return False, f"Unexpected error during test setup: {e}", final_timing_metrics


def _check_provider_client_readiness(  # Changed help_info type
    client: Any, provider_name: str, help_info: ProviderHelp | None
) -> ProviderInfo:
    """Checks if a provider client has the necessary upload methods."""
    provider_class = client.__class__
    has_async = hasattr(client, "async_upload_file") and not getattr(
        provider_class.async_upload_file, "__isabstractmethod__", False
    )
    has_sync = hasattr(client, "upload_file") and not getattr(provider_class.upload_file, "__isabstractmethod__", False)

    retention_note = ""
    if help_info:
        setup_info_lower = help_info.get("setup", "").lower()
        # Simplified retention note logic for brevity here, can be expanded if needed
        if "note:" in setup_info_lower:
            retention_note = setup_info_lower[setup_info_lower.find("note:") :].strip()

    explanation_base = f"{provider_name} ({type(client).__name__})" + (f" - {retention_note}" if retention_note else "")

    if (has_async and has_sync) or has_sync:
        actual_help_info: dict[str, str]
        if help_info is None:
            actual_help_info = {}
        else:
            actual_help_info = help_info  # type: ignore[assignment]  # ProviderHelp is a TypedDict subtype of dict[str, str]
        return ProviderInfo(
            success=True,
            explanation=explanation_base,
            help_info=actual_help_info,
            timing=None,
        )
    else:
        setup_info_text = (
            help_info.get("setup", "")
            if help_info
            else "Provider methods (upload_file/async_upload_file) not correctly implemented."
        )
        return ProviderInfo(
            success=False,
            explanation=f"Provider '{provider_name}' needs configuration (method check failed).",
            help_info={"setup": setup_info_text},  # This is dict[str,str]
            timing=None,
        )


def _execute_online_test_for_setup(  # Removed hypothetical unused ignore
    provider_name: str, provider_info_initial: ProviderInfo
) -> ProviderInfo:
    """Executes online test and updates ProviderInfo."""
    online_status, message, timing = _test_provider_online(provider_name)
    if not online_status:
        return ProviderInfo(
            success=False,
            explanation=message,  # This is the error message from _test_provider_online
            help_info=provider_info_initial.help_info,  # Keep original help_info
            timing=timing,
        )
    else:
        # Successfully tested online
        updated_explanation = f"{provider_info_initial.explanation}\nOnline test passed successfully"
        # Ensure timing is a dict, not None, before updating/assigning
        final_timing = timing if timing is not None else provider_info_initial.timing
        return ProviderInfo(
            success=True,
            explanation=updated_explanation,
            help_info=provider_info_initial.help_info,
            timing=final_timing,
        )


def setup_provider(provider: str, *, verbose: bool = False, online: bool = False) -> ProviderInfo:
    """
    Check a provider's setup status and return its information.

    Args:
        provider: Name of the provider to check
        verbose: Whether to include detailed setup instructions (currently unused after refactor, but kept for API)
        online: Whether to perform an online test

    Returns:
        ProviderInfo: Provider status information
    """
    # logger.debug(f"Setting up provider: {provider}, verbose={verbose}, online={online}") # verbose not used by helpers directly

    if provider.lower() == "simple":
        return ProviderInfo(
            success=False,
            explanation=f"Provider '{provider}' is a base class and not directly usable.",
            help_info={},
        )

    provider_module = get_provider_module(provider)
    help_info = get_provider_help(provider)  # Get help_info once

    if not provider_module:
        setup_text = help_info.get("setup", "") if help_info else "Provider module not found."
        return ProviderInfo(
            success=False,
            explanation=f"Provider '{provider}' is not available.",
            help_info={"setup": setup_text},
        )

    try:
        client = provider_module.get_provider()
        if not client:
            setup_text = help_info.get("setup", "") if help_info else "Provider needs configuration."
            return ProviderInfo(
                success=False,
                explanation=f"Provider '{provider}' needs configuration.",
                help_info={"setup": setup_text},
            )

        provider_info = _check_provider_client_readiness(client, provider, help_info)

        if online and provider_info.success:
            provider_info = _execute_online_test_for_setup(provider, provider_info)

        return provider_info

    except Exception as e:
        logger.error(f"Error during setup of provider {provider}: {e}")
        setup_text = help_info.get("setup", "") if help_info else "Setup failed due to an error."
        return ProviderInfo(
            success=False,
            explanation=f"Provider '{provider}' setup failed: {e}",
            help_info={"setup": setup_text},
        )


def setup_providers(*, verbose: bool = False, online: bool = False) -> dict[str, ProviderInfo]:
    """
    Check setup status for all providers.

    Args:
        verbose: If True, print detailed status information
        online: If True, test providers by uploading a test file

    Returns:
        dict[str, ProviderInfo]: Dictionary mapping provider names to their setup status
    """
    results: dict[str, ProviderInfo] = {}

    for provider in PROVIDERS_PREFERENCE:
        result = setup_provider(provider, verbose=verbose, online=online)
        results[provider] = result

    return results


def _get_provider_module(provider: str) -> Provider | None:
    """Get a provider module with error handling."""
    try:
        return ProviderFactory.get_provider_module(provider)
    except Exception as e:
        logger.error(f"Error getting provider module {provider}: {e}")
        return None


def _try_upload_with_provider(
    provider_name: str,
    file_path: str | Path,
    options: UploadOptions,
) -> UploadResult:
    """Try to upload a file with a specific provider."""
    # Initialize timing variables
    start_time = time.time()
    read_start = time.time()
    read_duration = 0.0
    upload_start = 0.0
    upload_duration = 0.0
    validation_start = 0.0
    validation_duration = 0.0

    try:
        # Get the provider module
        provider_module = _get_provider_module(provider_name)
        if not provider_module:
            return UploadResult(
                url="",
                metadata={
                    "provider": provider_name,
                    "success": False,
                    "error": f"Provider {provider_name} not found",
                },
            )

        # Create the provider using the factory
        provider = ProviderFactory.create_provider(provider_name)
        if not provider:
            return UploadResult(
                url="",
                metadata={
                    "provider": provider_name,
                    "success": False,
                    "error": f"Provider {provider_name} not configured",
                },
            )

        # Track file read time
        path = Path(str(file_path))
        if path.exists():
            with open(path, "rb") as f:
                _ = f.read()  # Read file to measure read time
        read_duration = time.time() - read_start

        # Track upload time
        upload_start = time.time()
        upload_result = provider.upload_file(
            file_path,
            options.remote_path,
            unique=options.unique,
            force=options.force,
            upload_path=options.upload_path,
        )
        upload_duration = time.time() - upload_start

        # Track validation time
        validation_start = time.time()
        url = upload_result.url if isinstance(upload_result, UploadResult) else upload_result
        try:
            response = requests.head(
                url,
                timeout=30,
                allow_redirects=True,
                headers={"User-Agent": "twat-fs/1.0"},
            )
            if response.status_code not in (200, 201, 202, 203, 204):
                logger.warning(f"URL validation failed: status {response.status_code}")
        except Exception as e:
            logger.warning(f"URL validation failed: {e}")
        validation_duration = time.time() - validation_start

        end_time = time.time()
        total_duration = end_time - start_time

        # Create timing metrics
        timing = {
            "start_time": start_time,
            "end_time": end_time,
            "total_duration": total_duration,
            "read_duration": read_duration,
            "upload_duration": upload_duration,
            "validation_duration": validation_duration,
            "provider": provider_name,
        }

        # Convert string result to UploadResult if needed
        result = (
            UploadResult(url=upload_result, metadata={"provider": provider_name})
            if isinstance(upload_result, str)
            else upload_result
        )

        # Add timing information
        result.metadata["timing"] = timing

        # Log timing information
        logger.info(
            f"Upload timing for {provider_name}: "
            f"total={total_duration:.2f}s, "
            f"read={read_duration:.2f}s, "
            f"upload={upload_duration:.2f}s, "
            f"validation={validation_duration:.2f}s"
        )

        return result
    except Exception as e:
        end_time = time.time()
        total_duration = end_time - start_time

        return UploadResult(
            url="",
            metadata={
                "provider": provider_name,
                "success": False,
                "error": f"Upload failed: {e}",
                "timing": {
                    "start_time": start_time,
                    "end_time": end_time,
                    "total_duration": total_duration,
                    "read_duration": read_duration,
                    "upload_duration": upload_duration,
                    "validation_duration": validation_duration,
                    "provider": provider_name,
                },
            },
        )


def _try_next_provider(  # Greatly simplified argument list
    remaining_providers: Sequence[str],
    file_path: str | Path,
    options: UploadOptions,
    tried_providers: set[str] | None = None,
) -> str:
    """
    Try to upload a file using the next available provider.

    Args:
        remaining_providers: List of providers to try
        file_path: Path to the file to upload
        remote_path: Optional remote path
        unique: If True, ensures unique filename
        force: If True, overwrites existing file
        upload_path: Custom upload path
        fragile: If True, don't try other providers on failure
        tried_providers: Set of providers that have been tried

    Returns:
        str: URL of the uploaded file

    Raises:
        ValueError: If no providers are available or all uploads fail
    """
    if not remaining_providers:
        msg = "No providers available"
        raise ValueError(msg)

    # Keep track of tried providers to avoid loops
    tried = tried_providers or set()

    # Try each provider in sequence
    for provider in remaining_providers:
        if provider in tried:
            continue

        tried.add(provider)
        try:
            result = _try_upload_with_provider(
                provider,
                file_path,
                options,
            )
            return result.url

        except ValueError as e:
            if options.fragile:
                raise
            logger.warning(f"Provider {provider} failed: {e}")
            continue

    msg = f"All providers failed: {', '.join(tried)}"
    raise ValueError(msg)


@with_retry(
    max_attempts=2,  # One retry before falling back to next provider
    strategy=RetryStrategy.EXPONENTIAL,
    exceptions=(RetryableError,),  # Only retry on RetryableError
)
def upload_file(
    file_path: str | Path,
    provider: str | Sequence[str] | None = None,
    options: UploadOptions | None = None,  # Replaces individual options
) -> str:
    """
    Upload a file using the specified provider(s) with fallback.

    Args:
        file_path: Path to the file to upload
        provider: Provider name or list of providers to try in order
        remote_path: Optional remote path to use
        unique: Whether to ensure unique filenames
        force: Whether to overwrite existing files
        upload_path: Base path for uploads
        fragile: If True, fail immediately without trying fallback providers

    Returns:
        str: URL to the uploaded file

    Raises:
        NonRetryableError: If all providers fail
        FileNotFoundError: If the file doesn't exist
        ValueError: If no valid providers are available
    """
    # Validate file exists
    path = Path(file_path)
    if not path.exists():
        msg = f"File not found: {path}"
        raise FileNotFoundError(msg)
    if not path.is_file():
        msg = f"{path} is a directory"
        raise ValueError(msg)

    current_options = options or UploadOptions()

    # Determine provider list
    providers = []
    if provider:
        providers = [provider] if isinstance(provider, str) else list(provider)
    else:
        providers = PROVIDERS_PREFERENCE

    # Validate providers
    if not providers:
        msg = "No providers specified"
        raise ValueError(msg)
    for p in providers:
        if p not in PROVIDERS_PREFERENCE:
            msg = f"Invalid provider: {p}"
            raise ValueError(msg)

    try:
        # Try first provider with retry
        return _try_upload_with_provider(
            providers[0],
            file_path,
            current_options,
        ).url
    except (RetryableError, NonRetryableError) as e:
        if current_options.fragile or len(providers) == 1:
            msg = f"Provider {providers[0]} failed: {e}"
            raise NonRetryableError(msg, providers[0]) from e

        # Try remaining providers with circular fallback
        logger.info(f"Provider {providers[0]} failed, trying alternatives")
        return _try_next_provider(
            providers[1:],
            file_path,
            current_options,
            tried_providers={providers[0]},
        )


# Removed _try_upload_with_fallback as it appears to be an orphaned/redundant
# fallback mechanism after refactoring the main upload_file flow to use UploadOptions
# and _try_next_provider. If this function is still needed, its usage and
# argument passing (especially **kwargs in relation to UploadOptions) would
# need to be re-evaluated.
