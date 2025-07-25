---
this_file: src_docs/development/provider-development.md
---

# Provider Development Guide

This guide explains how to create new upload providers for twat-fs.

## Overview

A provider in twat-fs is a module that handles file uploads to a specific service. Providers can be:

- **Simple**: Anonymous uploads without authentication
- **Authenticated**: Require credentials (API keys, tokens, etc.)
- **Sync or Async**: Choose based on the underlying API

## Quick Start

### 1. Choose a Template

Start with the appropriate template:

```bash
# For simple providers (no auth)
cp templates/simple_provider_template.py src/twat_fs/upload_providers/myprovider.py

# For authenticated providers
cp templates/authenticated_provider_template.py src/twat_fs/upload_providers/myprovider.py
```

### 2. Implement Required Functions

Every provider module must export:

```python
# Provider help information
PROVIDER_HELP: ProviderHelp = {
    "setup": "Instructions for setting up this provider",
    "deps": "Required dependencies (if any)"
}

# Provider factory function
def get_provider() -> ProviderClient | None:
    """Return configured provider instance or None."""
    credentials = get_credentials()
    if not credentials:
        return None
    return MyProvider(**credentials)

# Credential fetching
def get_credentials() -> dict[str, Any] | None:
    """Get credentials from environment or return None."""
    # Implementation depends on provider
```

### 3. Implement Provider Class

Your provider class should inherit from a base class and implement required methods.

## Simple Provider Example

Here's a complete example of a simple provider:

```python
# this_file: src/twat_fs/upload_providers/example.py

"""Example simple upload provider."""

from pathlib import Path
from typing import Any, BinaryIO

import requests
from loguru import logger

from twat_fs.upload_providers.simple import SimpleProvider
from twat_fs.upload_providers.core import (
    NonRetryableError,
    RetryableError,
    convert_to_upload_result,
)
from twat_fs.upload_providers.protocols import ProviderHelp
from twat_fs.upload_providers.provider_types import UploadResult

# Provider help information
PROVIDER_HELP: ProviderHelp = {
    "setup": "No setup required. Example provider for documentation.",
    "deps": "",
}

class ExampleProvider(SimpleProvider):
    """Example provider implementation."""
    
    provider_name = "example"
    base_url = "https://example.com/api/upload"
    max_file_size = 100 * 1024 * 1024  # 100MB
    
    def upload_file_impl(self, file: BinaryIO) -> UploadResult:
        """
        Implement the actual upload logic.
        
        Args:
            file: Open file handle to upload
            
        Returns:
            UploadResult with URL and metadata
            
        Raises:
            RetryableError: For temporary failures
            NonRetryableError: For permanent failures
        """
        try:
            # Check file size
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning
            
            if file_size > self.max_file_size:
                raise NonRetryableError(
                    f"File too large: {file_size} > {self.max_file_size}",
                    self.provider_name
                )
            
            # Prepare upload
            files = {"file": (Path(file.name).name, file, "application/octet-stream")}
            
            # Make request
            response = requests.post(
                self.base_url,
                files=files,
                timeout=300
            )
            
            # Handle response
            if response.status_code == 200:
                data = response.json()
                url = data.get("url")
                if url:
                    return convert_to_upload_result(
                        url,
                        provider=self.provider_name,
                        metadata={"file_size": file_size}
                    )
                else:
                    raise NonRetryableError(
                        "No URL in response",
                        self.provider_name
                    )
            elif response.status_code == 429:
                # Rate limited - should retry
                raise RetryableError(
                    "Rate limited, please try again",
                    self.provider_name
                )
            elif response.status_code >= 500:
                # Server error - should retry
                raise RetryableError(
                    f"Server error: {response.status_code}",
                    self.provider_name
                )
            else:
                # Client error - should not retry
                raise NonRetryableError(
                    f"Upload failed: {response.status_code} {response.text}",
                    self.provider_name
                )
                
        except requests.RequestException as e:
            # Network errors are retryable
            logger.error(f"Network error: {e}")
            raise RetryableError(
                f"Network error: {e}",
                self.provider_name
            ) from e
        except Exception as e:
            # Unexpected errors are not retryable
            logger.error(f"Unexpected error: {e}")
            raise NonRetryableError(
                f"Unexpected error: {e}",
                self.provider_name
            ) from e

def get_credentials() -> dict[str, Any] | None:
    """Simple providers don't need credentials."""
    return {}

def get_provider() -> ExampleProvider | None:
    """Return provider instance."""
    return ExampleProvider()
```

## Authenticated Provider Example

Here's an example with authentication:

```python
# this_file: src/twat_fs/upload_providers/authexample.py

"""Example authenticated upload provider."""

import os
from typing import Any, BinaryIO
from pathlib import Path

import requests
from loguru import logger

from twat_fs.upload_providers.core import (
    BaseProvider,
    NonRetryableError,
    RetryableError,
)
from twat_fs.upload_providers.protocols import ProviderHelp, ProviderClient
from twat_fs.upload_providers.provider_types import UploadResult

# Provider help information
PROVIDER_HELP: ProviderHelp = {
    "setup": """
    To use this provider:
    1. Sign up at https://example.com
    2. Get your API key from the dashboard
    3. Set environment variable: export EXAMPLE_API_KEY="your_key_here"
    """,
    "deps": "",
}

class AuthExampleProvider(BaseProvider):
    """Authenticated example provider."""
    
    provider_name = "authexample"
    base_url = "https://api.example.com/v1"
    
    def __init__(self, api_key: str):
        """Initialize with API key."""
        super().__init__()
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "twat-fs/1.0"
        }
    
    def upload_file_impl(self, file: BinaryIO) -> UploadResult:
        """Upload file with authentication."""
        try:
            # Get upload URL
            init_response = requests.post(
                f"{self.base_url}/upload/init",
                headers=self.headers,
                json={"filename": Path(file.name).name},
                timeout=30
            )
            
            if init_response.status_code == 401:
                raise NonRetryableError(
                    "Invalid API key",
                    self.provider_name
                )
            
            init_response.raise_for_status()
            upload_url = init_response.json()["upload_url"]
            
            # Upload file
            upload_response = requests.put(
                upload_url,
                headers=self.headers,
                data=file,
                timeout=300
            )
            
            upload_response.raise_for_status()
            
            # Get final URL
            file_id = upload_response.json()["file_id"]
            final_url = f"{self.base_url}/files/{file_id}"
            
            return UploadResult(
                url=final_url,
                metadata={
                    "provider": self.provider_name,
                    "file_id": file_id,
                    "authenticated": True
                }
            )
            
        except requests.HTTPError as e:
            if e.response.status_code >= 500:
                raise RetryableError(
                    f"Server error: {e}",
                    self.provider_name
                ) from e
            else:
                raise NonRetryableError(
                    f"HTTP error: {e}",
                    self.provider_name
                ) from e
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise NonRetryableError(
                f"Upload failed: {e}",
                self.provider_name
            ) from e

def get_credentials() -> dict[str, str] | None:
    """Get API key from environment."""
    api_key = os.getenv("EXAMPLE_API_KEY")
    if not api_key:
        logger.debug("EXAMPLE_API_KEY not set")
        return None
    return {"api_key": api_key}

def get_provider() -> ProviderClient | None:
    """Return configured provider or None."""
    credentials = get_credentials()
    if not credentials:
        return None
    return AuthExampleProvider(**credentials)
```

## Async Provider Example

For APIs that benefit from async operations:

```python
# this_file: src/twat_fs/upload_providers/asyncexample.py

"""Example async upload provider."""

import aiohttp
from twat_fs.upload_providers.simple import AsyncBaseProvider
from twat_fs.upload_providers.core import convert_to_upload_result
from twat_fs.upload_providers.provider_types import UploadResult

class AsyncExampleProvider(AsyncBaseProvider):
    """Async provider using aiohttp."""
    
    provider_name = "asyncexample"
    base_url = "https://async.example.com/upload"
    
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
        path = Path(file_path)
        
        async with aiohttp.ClientSession() as session:
            with open(path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename=path.name)
                
                async with session.post(
                    self.base_url,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return convert_to_upload_result(
                            result['url'],
                            provider=self.provider_name
                        )
                    else:
                        text = await response.text()
                        raise NonRetryableError(
                            f"Upload failed: {response.status} {text}",
                            self.provider_name
                        )
```

## Best Practices

### 1. Error Handling

Always distinguish between retryable and non-retryable errors:

```python
# Retryable errors (temporary)
- Network timeouts
- Rate limiting (429)
- Server errors (5xx)
- Temporary service unavailability

# Non-retryable errors (permanent)
- Authentication failures (401, 403)
- File too large (413)
- Invalid file type (415)
- Bad request (400)
```

### 2. Timeout Management

Set appropriate timeouts:

```python
# Short timeout for API calls
response = requests.get(url, timeout=30)

# Longer timeout for file uploads
response = requests.post(url, files=files, timeout=300)

# No timeout for very large files (use streaming)
response = requests.post(url, data=file_stream, timeout=None)
```

### 3. File Handling

Handle files efficiently:

```python
def upload_file_impl(self, file: BinaryIO) -> UploadResult:
    # Get file size without loading into memory
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    
    # Stream large files
    if file_size > 100 * 1024 * 1024:  # 100MB
        return self._stream_upload(file)
    else:
        return self._simple_upload(file)
```

### 4. Logging

Use appropriate log levels:

```python
logger.debug(f"Starting upload to {self.provider_name}")
logger.info(f"Successfully uploaded {file_name}")
logger.warning(f"Retrying upload after error: {e}")
logger.error(f"Upload failed: {e}")
```

### 5. Configuration Validation

Validate configuration early:

```python
def __init__(self, api_key: str, bucket: str = None):
    if not api_key:
        raise ValueError("API key is required")
    
    self.api_key = api_key
    self.bucket = bucket or self._get_default_bucket()
    
    # Test configuration
    if not self._validate_credentials():
        raise NonRetryableError(
            "Invalid credentials",
            self.provider_name
        )
```

## Testing Your Provider

### 1. Unit Tests

Create `tests/test_myprovider.py`:

```python
import pytest
from unittest.mock import Mock, patch
from twat_fs.upload_providers import myprovider

class TestMyProvider:
    """Test cases for MyProvider."""
    
    def test_get_credentials_missing(self, monkeypatch):
        """Test behavior when credentials are missing."""
        monkeypatch.delenv("MY_API_KEY", raising=False)
        assert myprovider.get_credentials() is None
    
    def test_get_credentials_present(self, monkeypatch):
        """Test credential loading."""
        monkeypatch.setenv("MY_API_KEY", "test_key")
        creds = myprovider.get_credentials()
        assert creds == {"api_key": "test_key"}
    
    @patch('requests.post')
    def test_upload_success(self, mock_post):
        """Test successful upload."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "url": "https://example.com/file.jpg"
        }
        
        provider = myprovider.MyProvider()
        result = provider.upload_file("test.jpg")
        
        assert result.url == "https://example.com/file.jpg"
        assert result.metadata["provider"] == "myprovider"
```

### 2. Integration Tests

Test with real service (optional):

```python
@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("MY_API_KEY"),
    reason="MY_API_KEY not set"
)
def test_real_upload():
    """Test actual upload to service."""
    provider = myprovider.get_provider()
    assert provider is not None
    
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"test content")
        f.flush()
        
        result = provider.upload_file(f.name)
        assert result.url.startswith("https://")
        
        # Verify file is accessible
        response = requests.get(result.url)
        assert response.status_code == 200
```

### 3. Mock Provider for Testing

Create a mock provider for testing the framework:

```python
class MockProvider(BaseProvider):
    """Mock provider for testing."""
    
    provider_name = "mock"
    
    def __init__(self, should_fail=False, error_type="non_retryable"):
        self.should_fail = should_fail
        self.error_type = error_type
    
    def upload_file_impl(self, file: BinaryIO) -> UploadResult:
        if self.should_fail:
            if self.error_type == "retryable":
                raise RetryableError("Mock retry error", self.provider_name)
            else:
                raise NonRetryableError("Mock error", self.provider_name)
        
        return UploadResult(
            url="https://mock.example.com/file.jpg",
            metadata={"mock": True}
        )
```

## Advanced Topics

### 1. Chunked Uploads

For large files, implement chunked uploading:

```python
def _chunked_upload(self, file: BinaryIO, chunk_size: int = 5 * 1024 * 1024):
    """Upload file in chunks."""
    # Initialize multipart upload
    upload_id = self._init_multipart_upload(file.name)
    
    # Upload chunks
    parts = []
    chunk_num = 0
    
    while True:
        chunk = file.read(chunk_size)
        if not chunk:
            break
            
        chunk_num += 1
        etag = self._upload_chunk(upload_id, chunk_num, chunk)
        parts.append({"PartNumber": chunk_num, "ETag": etag})
    
    # Complete upload
    return self._complete_multipart_upload(upload_id, parts)
```

### 2. Progress Reporting

Add progress callbacks:

```python
def upload_file_impl(
    self,
    file: BinaryIO,
    progress_callback: Callable[[int, int], None] = None
) -> UploadResult:
    """Upload with progress reporting."""
    file_size = self._get_file_size(file)
    bytes_uploaded = 0
    
    def _upload_callback(chunk):
        nonlocal bytes_uploaded
        bytes_uploaded += len(chunk)
        if progress_callback:
            progress_callback(bytes_uploaded, file_size)
    
    # Use callback during upload
    return self._upload_with_progress(file, _upload_callback)
```

### 3. Provider Capabilities

Advertise provider capabilities:

```python
class MyProvider(BaseProvider):
    """Provider with capability reporting."""
    
    @classmethod
    def get_capabilities(cls) -> dict[str, Any]:
        """Return provider capabilities."""
        return {
            "max_file_size": 5 * 1024 * 1024 * 1024,  # 5GB
            "supported_types": ["*"],  # All types
            "features": {
                "resumable": True,
                "chunked": True,
                "progress": True,
                "folders": True,
                "expiration": False,
            },
            "auth_required": True,
        }
```

### 4. Custom Options

Support provider-specific options:

```python
def upload_file_impl(
    self,
    file: BinaryIO,
    storage_class: str = "STANDARD",
    acl: str = "private",
    **kwargs
) -> UploadResult:
    """Upload with S3-specific options."""
    extra_args = {
        "StorageClass": storage_class,
        "ACL": acl,
    }
    
    # Use options during upload
    self.client.upload_fileobj(
        file,
        self.bucket,
        key,
        ExtraArgs=extra_args
    )
```

## Checklist

Before submitting your provider:

- [ ] Implements all required functions (`get_provider`, `get_credentials`)
- [ ] Provides helpful `PROVIDER_HELP` information
- [ ] Handles errors appropriately (Retryable vs NonRetryable)
- [ ] Includes proper logging
- [ ] Has unit tests with >80% coverage
- [ ] Passes linting (`ruff check`)
- [ ] Includes docstrings
- [ ] Added to `PROVIDERS_PREFERENCE` list
- [ ] Documented in provider list
- [ ] Tested with real service (if possible)

## Getting Help

- Check existing providers for examples
- Read the base classes in `simple.py`
- Look at test cases for patterns
- Open an issue for questions

## Next Steps

- [API Reference](api-reference.md) - Detailed API documentation
- [Testing Guide](testing.md) - How to test your provider
- [Contributing](contributing.md) - Contribution guidelines