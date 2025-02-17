# twat-fs

File system utilities for twat, focusing on robust and extensible file upload capabilities with multiple provider support.

## Rationale

`twat-fs` provides a unified interface for uploading files to various storage providers while addressing common challenges:

* **Provider Flexibility**: Seamlessly switch between storage providers without code changes
* **Fault Tolerance**: Graceful fallback between providers if primary provider fails
* **Progressive Enhancement**: Start simple with zero configuration (simple providers), scale up to advanced providers (S3, Dropbox) as needed
* **Developer Experience**: Clear interfaces, comprehensive type hints, and runtime checks
* **Extensibility**: Well-defined provider protocol for adding new storage backends

## Quick Start

### Installation

Basic installation with simple providers:

```bash
uv pip install twat-fs
```

Install with all providers and development tools:

```bash
uv pip install 'twat-fs[all,dev]'
```

### Basic Usage

```python
from twat_fs import upload_file

# Simple upload (uses www0x0.st by default)
url = upload_file("path/to/file.txt")

# Specify provider
url = upload_file("path/to/file.txt", provider="s3")

# Try specific providers in order
url = upload_file("path/to/file.txt", provider=["s3", "dropbox", "www0x0"])
```

### Command Line Interface

```bash
# Simple upload
python -m twat_fs upload_file path/to/file.txt

# Specify provider
python -m twat_fs upload_file path/to/file.txt --provider s3

# Check provider setup
python -m twat_fs setup provider s3
python -m twat_fs setup all
```

## Provider Configuration

### Simple Providers (No Configuration Required)

The following providers work out of the box with no configuration:

* **www0x0.st**: General file uploads (default)
* **uguu.se**: Temporary file uploads
* **bashupload.com**: General file uploads
* **termbin.com**: Text-only uploads via netcat

### Dropbox

```bash
export DROPBOX_ACCESS_TOKEN="your_token_here"
# Optional OAuth2 configuration
export DROPBOX_REFRESH_TOKEN="refresh_token"
export DROPBOX_APP_KEY="app_key"
export DROPBOX_APP_SECRET="app_secret"
```

### AWS S3

```bash
# Required
export AWS_S3_BUCKET="your_bucket"
export AWS_DEFAULT_REGION="us-east-1"

# Authentication (choose one)
export AWS_ACCESS_KEY_ID="key_id"
export AWS_SECRET_ACCESS_KEY="secret_key"
# Or use AWS CLI: aws configure
# Or use IAM roles in AWS infrastructure

# Optional
export AWS_ENDPOINT_URL="custom_endpoint"  # For S3-compatible services
export AWS_S3_PATH_STYLE="true"  # For path-style endpoints
export AWS_ROLE_ARN="role_to_assume"
```

### FAL.ai

```bash
export FAL_KEY="your_key_here"
```

## Architecture

### Provider System

The package uses a provider-based architecture with three key components:

1. **Provider Registry**: Central registry of available providers
   * Maintains provider preference order
   * Handles lazy loading of provider modules
   * Provides runtime protocol checking

2. **Provider Protocol**: Formal interface that all providers must implement
   * Credentials management
   * Client initialization
   * File upload functionality
   * Help and setup information

3. **Provider Client**: The actual implementation that handles uploads
   * Provider-specific upload logic
   * Error handling and retries
   * Progress tracking (where supported)

### Type System

Strong typing throughout with runtime checks:

* Type hints for all public APIs
* Runtime protocol verification
* Custom types for provider-specific data

## Implementing a New Provider

To add a new storage provider, create a module in `twat_fs/upload_providers/` that implements the Provider protocol:

```python
from pathlib import Path
from typing import Any, TypedDict
from twat_fs.upload_providers import ProviderClient, Provider

# Provider-specific help messages
PROVIDER_HELP = {
    "setup": """Setup instructions for users...""",
    "deps": """Additional dependencies needed..."""
}

def get_credentials() -> dict[str, Any] | None:
    """
    Get provider credentials from environment.
    Return None if not configured.
    """
    # Implement credential checking
    ...

def get_provider() -> ProviderClient | None:
    """
    Initialize and return the provider client.
    Only import provider-specific dependencies here.
    """
    creds = get_credentials()
    if not creds:
        return None
    
    try:
        # Initialize your provider client
        client = YourProviderClient(creds)
        return client
    except Exception:
        return None

def upload_file(local_path: str | Path, remote_path: str | Path | None = None) -> str:
    """
    Upload a file and return its public URL.
    This is a convenience wrapper around get_provider().
    """
    client = get_provider()
    if not client:
        raise ValueError("Provider not configured")
    return client.upload_file(local_path, remote_path)

# Your provider client implementation
class YourProviderClient:
    def upload_file(
        self, 
        local_path: str | Path, 
        remote_path: str | Path | None = None
    ) -> str:
        """Implement the actual upload logic."""
        ...
```

Then add your provider to `PROVIDERS_PREFERENCE` in `upload_providers/__init__.py`.

## Development

### Setup Environment

```bash
# Install development tools
uv pip install uv

# Create and activate environment
uv venv
source .venv/bin/activate

# Install in development mode with all extras
uv pip install -e '.[dev,all,test]'
```

### Code Quality

```bash
# Format code
python -m ruff format src tests
python -m ruff check --fix --unsafe-fixes src tests

# Run type checks
python -m mypy src tests

# Run tests
python -m pytest tests
python -m pytest --cov=src/twat_fs tests  # with coverage

# Quick development cycle
./cleanup.py install  # Set up environment
./cleanup.py status  # Run all checks
```

### Publish

Make sure to have in your env: 

```bash
export UV_PUBLISH_TOKEN="${PYPI_TOKEN}"
```

Build and publish: 

```bash
VER="v1.7.9" && echo "$VER" > VERSION.txt && git commit -am "$VER" && git tag "$VER"
uv build && uv publish
```

### Testing

The test suite includes:

* Unit tests for each provider
* Integration tests with real services
* Performance tests for large files
* Error condition tests
* Type checking tests

When adding a new provider:

1. Add unit tests in `tests/test_providers/`
2. Add integration tests in `tests/test_integration.py`
3. Add performance tests if relevant
4. Update provider discovery tests

## Error Handling & Troubleshooting

### Error Types

The package uses a structured error hierarchy:

```python
from twat_fs.errors import (
    UploadError,              # Base class for all upload errors
    ProviderError,            # Base class for provider-specific errors
    ConfigurationError,       # Missing or invalid configuration
    AuthenticationError,      # Authentication/credential issues
    UploadFailedError,       # Upload failed after max retries
    ProviderNotFoundError,   # Provider module not found/importable
)
```

### Common Issues

1. **Provider Not Available**

```python
try:
    url = upload_file("file.txt", provider="s3")
except ProviderNotFoundError as e:
    # Provider module not found
    print(f"Provider not available: {e}")
    print(e.setup_instructions)  # Gets provider-specific setup guide
```

2. **Authentication Failures**

```python
try:
    url = upload_file("file.txt")
except AuthenticationError as e:
    # Credentials missing or invalid
    print(f"Auth failed: {e}")
    print(e.provider)      # Which provider failed
    print(e.credentials)   # Which credentials are missing/invalid
```

3. **Upload Failures**

```python
try:
    url = upload_file("file.txt")
except UploadFailedError as e:
    print(f"Upload failed: {e}")
    print(e.provider)      # Which provider failed
    print(e.attempts)      # Number of attempts made
    print(e.last_error)    # Underlying error from provider
```

### Provider Status Checking

Use the setup commands to diagnose provider issues:

```bash
# Check specific provider
python -m twat_fs setup provider s3

# Check all providers
python -m twat_fs setup all
```

### Logging

The package uses `loguru` for structured logging:

```python
from loguru import logger

# Set log level
logger.level("DEBUG")

# Add file handler
logger.add("twat_fs.log", rotation="1 day")

# Log format includes provider info
logger.add(sys.stderr, format="{time} {level} [{extra[provider]}] {message}")
```

### Debugging Provider Issues

When implementing a new provider:

1. Enable debug logging:

```python
import logging
logging.getLogger("twat_fs").setLevel(logging.DEBUG)
```

2. Use the provider test helper:

```python
from twat_fs.testing import ProviderTestHelper

helper = ProviderTestHelper("your_provider")
helper.test_provider_implementation()  # Checks protocol compliance
helper.test_provider_functionality()   # Tests basic operations
```

3. Check provider initialization:

```python
from twat_fs.upload_providers import get_provider_module

provider = get_provider_module("your_provider")
print(provider.get_credentials())  # Check credential loading
print(provider.get_provider())     # Check client initialization
```

## License

MIT License
 
.
