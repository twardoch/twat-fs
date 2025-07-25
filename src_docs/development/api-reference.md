---
this_file: src_docs/development/api-reference.md
---

# API Reference

This document provides detailed API documentation for twat-fs.

## Core Functions

### upload_file

Upload a file using the specified provider(s) with automatic fallback.

```python
def upload_file(
    file_path: str | Path,
    provider: str | Sequence[str] | None = None,
    options: UploadOptions | None = None,
) -> str:
```

**Parameters:**

- `file_path` (str | Path): Path to the file to upload
- `provider` (str | Sequence[str] | None): Provider name or list of providers to try in order. If None, uses default preference list
- `options` (UploadOptions | None): Upload options (see UploadOptions)

**Returns:**

- `str`: URL to the uploaded file

**Raises:**

- `FileNotFoundError`: If the file doesn't exist
- `ValueError`: If the path is a directory or no valid providers are available
- `NonRetryableError`: If all providers fail with permanent errors
- `RetryableError`: If all providers fail with temporary errors (after retries)

**Example:**

```python
from twat_fs import upload_file
from twat_fs.upload import UploadOptions

# Simple upload
url = upload_file("document.pdf")

# Upload with specific provider
url = upload_file("image.jpg", provider="s3")

# Upload with fallback providers
url = upload_file("backup.zip", provider=["s3", "dropbox", "catbox"])

# Upload with options
options = UploadOptions(
    unique=True,
    remote_path="uploads/2024/",
    fragile=False
)
url = upload_file("report.csv", provider="s3", options=options)
```

### setup_provider

Check a provider's setup status and optionally test it.

```python
def setup_provider(
    provider: str,
    *,
    verbose: bool = False,
    online: bool = False
) -> ProviderInfo:
```

**Parameters:**

- `provider` (str): Name of the provider to check
- `verbose` (bool): Whether to include detailed setup instructions (currently unused)
- `online` (bool): Whether to perform an online test by uploading a test file

**Returns:**

- `ProviderInfo`: Provider status information

**Example:**

```python
from twat_fs.upload import setup_provider

# Check provider status
info = setup_provider("s3")
print(f"Ready: {info.success}")
print(f"Status: {info.explanation}")

# Test provider online
info = setup_provider("dropbox", online=True)
if info.timing:
    print(f"Upload time: {info.timing['upload_duration']:.2f}s")
```

### setup_providers

Check setup status for all providers.

```python
def setup_providers(
    *,
    verbose: bool = False,
    online: bool = False
) -> dict[str, ProviderInfo]:
```

**Parameters:**

- `verbose` (bool): If True, print detailed status information
- `online` (bool): If True, test providers by uploading a test file

**Returns:**

- `dict[str, ProviderInfo]`: Dictionary mapping provider names to their setup status

**Example:**

```python
from twat_fs.upload import setup_providers

# Check all providers
all_info = setup_providers()
for name, info in all_info.items():
    print(f"{name}: {'✓' if info.success else '✗'}")

# Test all providers online
all_info = setup_providers(online=True)
```

## Data Classes

### UploadOptions

Options for file upload operations.

```python
@dataclass
class UploadOptions:
    remote_path: str | Path | None = None
    unique: bool = False
    force: bool = False
    upload_path: str | None = None
    fragile: bool = False
```

**Attributes:**

- `remote_path` (str | Path | None): Remote path/prefix for the uploaded file (provider-dependent)
- `unique` (bool): If True, add timestamp to filename to ensure uniqueness
- `force` (bool): If True, overwrite existing files (provider-dependent)
- `upload_path` (str | None): Custom upload path (alternative to remote_path)
- `fragile` (bool): If True, fail immediately without trying fallback providers

### ProviderInfo

Information about a provider's setup status.

```python
@dataclass
class ProviderInfo:
    success: bool
    explanation: str
    help_info: dict[str, str]
    timing: dict[str, float] | None = None
```

**Attributes:**

- `success` (bool): Whether the provider is ready to use
- `explanation` (str): Human-readable status explanation
- `help_info` (dict[str, str]): Setup instructions and dependencies
- `timing` (dict[str, float] | None): Performance metrics from online test

### UploadResult

Result of a file upload operation.

```python
@dataclass
class UploadResult:
    url: str
    metadata: dict[str, Any] | None = None
```

**Attributes:**

- `url` (str): URL where the file can be accessed
- `metadata` (dict[str, Any] | None): Additional provider-specific metadata

## Provider Module Interface

### Provider Module Requirements

Every provider module must implement these functions:

```python
# Provider help information
PROVIDER_HELP: ProviderHelp = {
    "setup": str,  # Setup instructions
    "deps": str,   # Required dependencies
}

def get_provider() -> ProviderClient | None:
    """Return configured provider instance or None if not configured."""
    
def get_credentials() -> dict[str, Any] | None:
    """Get credentials from environment or return None."""
```

### ProviderClient Protocol

All provider clients must implement this interface:

```python
@runtime_checkable
class ProviderClient(Protocol):
    def upload_file(
        self,
        local_path: str | Path,
        remote_path: str | Path | None = None,
        *,
        unique: bool = False,
        force: bool = False,
        upload_path: str | None = None,
        **kwargs: Any,
    ) -> UploadResult:
        """Upload a file and return its URL."""
        ...
```

## Base Classes

### BaseProvider

Abstract base class for all providers.

```python
class BaseProvider(ABC, Provider):
    """Base class for all upload providers."""
    
    @abstractmethod
    def upload_file_impl(self, file: BinaryIO) -> UploadResult:
        """Implement the actual file upload logic."""
        ...
```

### AsyncBaseProvider

Base class for providers with async implementations.

```python
class AsyncBaseProvider(BaseProvider):
    """Base class for async providers."""
    
    async def async_upload_file(
        self,
        file_path: str | Path,
        remote_path: str | Path | None = None,
        *,
        unique: bool = False,
        force: bool = False,
        upload_path: str | None = None,
        **kwargs: Any,
    ) -> UploadResult:
        """Async upload implementation."""
        ...
```

### SyncBaseProvider

Base class for providers with sync implementations.

```python
class SyncBaseProvider(BaseProvider):
    """Base class for sync providers."""
    
    def upload_file(
        self,
        local_path: str | Path,
        remote_path: str | Path | None = None,
        *,
        unique: bool = False,
        force: bool = False,
        upload_path: str | None = None,
        **kwargs: Any,
    ) -> UploadResult:
        """Sync upload implementation."""
        ...
```

## Exceptions

### ProviderError

Base exception for all provider-related errors.

```python
class ProviderError(Exception):
    """Base exception for provider errors."""
    
    def __init__(self, message: str, provider: str):
        self.provider = provider
        super().__init__(message)
```

### RetryableError

Indicates a temporary error that should be retried.

```python
class RetryableError(ProviderError):
    """Temporary error that can be retried."""
```

Common causes:
- Network timeouts
- Rate limiting
- Temporary server errors (5xx)
- Connection failures

### NonRetryableError

Indicates a permanent error that should not be retried.

```python
class NonRetryableError(ProviderError):
    """Permanent error that should not be retried."""
```

Common causes:
- Authentication failures
- File too large
- Invalid file type
- Permission denied
- Configuration errors

## Decorators

### @with_retry

Decorator for adding retry logic to functions.

```python
@with_retry(
    max_attempts: int = 3,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
)
```

**Parameters:**

- `max_attempts`: Maximum number of attempts
- `strategy`: Retry strategy (EXPONENTIAL, LINEAR, CONSTANT)
- `exceptions`: Tuple of exceptions to retry on
- `initial_delay`: Initial delay between retries in seconds
- `max_delay`: Maximum delay between retries
- `exponential_base`: Base for exponential backoff

**Example:**

```python
from twat_fs.upload_providers.core import with_retry, RetryStrategy

@with_retry(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL,
    exceptions=(RetryableError,)
)
def unreliable_upload(file_path: str) -> str:
    # Function that might fail temporarily
    ...
```

### @with_timing

Decorator for adding timing metrics to upload results.

```python
@with_timing
async def upload_file(self, file_path: str) -> UploadResult:
    # Upload implementation
    result = await self._do_upload(file_path)
    # Timing metrics automatically added to result.metadata["timing"]
    return result
```

### @with_url_validation

Decorator for validating uploaded file URLs.

```python
@with_url_validation
def upload_file(self, file_path: str) -> UploadResult:
    # Upload implementation
    result = self._do_upload(file_path)
    # URL automatically validated before returning
    return result
```

## Utility Functions

### convert_to_upload_result

Convert various return types to UploadResult.

```python
def convert_to_upload_result(
    result: str | UploadResult | dict[str, Any],
    provider: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> UploadResult:
```

**Parameters:**

- `result`: URL string, UploadResult, or dict with 'url' key
- `provider`: Provider name to add to metadata
- `metadata`: Additional metadata to include

**Returns:**

- `UploadResult`: Normalized upload result

### run_async

Run an async coroutine in a synchronous context.

```python
def run_async(coro: Coroutine[Any, Any, T]) -> T:
```

**Example:**

```python
from twat_fs.upload_providers.async_utils import run_async

async def async_operation():
    return "result"

# Run from sync code
result = run_async(async_operation())
```

### to_sync

Convert an async function to a sync function.

```python
@to_sync
async def async_upload(file_path: str) -> str:
    # Async implementation
    ...

# Can now be called synchronously
url = async_upload("file.jpg")
```

### to_async

Convert a sync function to an async function.

```python
@to_async
def sync_upload(file_path: str) -> str:
    # Sync implementation
    ...

# Can now be awaited
url = await sync_upload("file.jpg")
```

## Provider Factory

### ProviderFactory

Factory for creating provider instances.

```python
class ProviderFactory:
    @staticmethod
    def get_provider_module(provider_name: str) -> Provider | None:
        """Get provider module by name."""
    
    @staticmethod
    def create_provider(provider_name: str) -> ProviderClient | None:
        """Create provider instance by name."""
```

**Example:**

```python
from twat_fs.upload_providers import ProviderFactory

# Get provider module
module = ProviderFactory.get_provider_module("s3")
if module:
    help_info = module.PROVIDER_HELP

# Create provider instance
provider = ProviderFactory.create_provider("s3")
if provider:
    result = provider.upload_file("file.jpg")
```

## Constants

### PROVIDERS_PREFERENCE

Default provider preference order.

```python
PROVIDERS_PREFERENCE: list[str] = [
    "catbox",
    "litterbox", 
    "www0x0",
    "uguu",
    "bashupload",
    "filebin",
    "pixeldrain",
    "s3",
    "dropbox",
    "fal",
]
```

### ExpirationTime

Enum for Litterbox expiration times.

```python
class ExpirationTime(str, Enum):
    HOUR_1 = "1h"
    HOURS_12 = "12h"
    HOURS_24 = "24h"
    HOURS_72 = "72h"
```

## Type Definitions

### Common Type Aliases

```python
from typing import TypeAlias

# Provider name or list of names
ProviderType: TypeAlias = str | list[str] | None

# File path types
PathType: TypeAlias = str | Path

# Provider help information
ProviderHelp = TypedDict('ProviderHelp', {
    'setup': str,
    'deps': str,
})
```

## Usage Examples

### Basic Upload

```python
from twat_fs import upload_file

# Upload with default provider
url = upload_file("photo.jpg")
print(f"Uploaded to: {url}")
```

### Upload with Error Handling

```python
from twat_fs import upload_file
from twat_fs.upload_providers.core import RetryableError, NonRetryableError

try:
    url = upload_file("large_file.zip", provider="s3")
except FileNotFoundError:
    print("File not found")
except RetryableError as e:
    print(f"Temporary error with {e.provider}: {e}")
except NonRetryableError as e:
    print(f"Permanent error with {e.provider}: {e}")
```

### Custom Provider Usage

```python
from twat_fs.upload_providers import ProviderFactory

# Direct provider usage
provider = ProviderFactory.create_provider("dropbox")
if provider:
    result = provider.upload_file(
        "document.pdf",
        remote_path="/Documents/2024/"
    )
    print(f"URL: {result.url}")
    print(f"Metadata: {result.metadata}")
```

### Async Upload

```python
import asyncio
from twat_fs.upload_providers import ProviderFactory

async def async_upload():
    provider = ProviderFactory.create_provider("catbox")
    if hasattr(provider, 'async_upload_file'):
        result = await provider.async_upload_file("image.png")
        return result.url

# Run async upload
url = asyncio.run(async_upload())
```

## See Also

- [Provider Development](provider-development.md) - Create new providers
- [Architecture](architecture.md) - System design details
- [CLI Reference](../user-guide/cli-reference.md) - Command-line usage