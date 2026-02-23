---
this_file: README.md
---

# twat-fs: Robust File Uploads for the `twat` Ecosystem

**`twat-fs` is a Python library providing flexible and resilient file upload capabilities, designed as part of the [twat](https://pypi.org/project/twat/) collection of utilities. It offers a unified interface for uploading files to various storage providers, complete with smart error handling, fallback mechanisms, and extensive configuration options.**

## Overview

**What is `twat-fs`?**

`twat-fs` simplifies the process of uploading files from your Python applications or command line to a multitude of cloud storage services and simple hosting providers. It acts as an abstraction layer, allowing you to write code once and seamlessly switch between different backends.

**Who is it for?**

*   **Python Developers:** Anyone needing to integrate file uploads into their applications without worrying about the specifics of each provider's API.
*   **CLI Users:** Individuals looking for a quick and reliable way to upload files from the terminal.
*   **Users of the `twat` ecosystem:** `twat-fs` integrates smoothly with other `twat` tools, providing a consistent experience.

**Why is it useful?**

Dealing with file uploads can be complex. Different providers have different APIs, authentication methods, and error responses. `twat-fs` handles these complexities for you, offering:

*   **Simplicity:** Easy-to-use API and CLI.
*   **Reliability:** Automatic retries for temporary issues and fallback to alternative providers for permanent failures.
*   **Flexibility:** Support for a range of providers, from simple anonymous hosts to robust services like AWS S3 and Dropbox.
*   **Extensibility:** A clear protocol for adding new storage providers.
*   **Transparency:** Clear error messages and logging for easier debugging.

## Features

*   **Multiple Provider Support:** Upload to various services like Catbox, Litterbox, 0x0.st, x0.at, Uguu.se, Filebin, Pixeldrain, Dropbox, AWS S3, and Fal.ai.
*   **Unified Interface:** Consistent API and CLI commands regardless of the chosen provider.
*   **Smart Fallback System:**
    *   Automatically retries uploads on temporary errors with exponential backoff.
    *   Falls back to the next configured provider in case of non-retryable errors.
    *   Circular fallback ensures all preferred providers are attempted.
    *   "Fragile" mode to disable fallback and fail immediately if a specific provider fails.
*   **URL Validation:** Attempts to verify that the URL returned by a provider is accessible before confirming success.
*   **Progressive Enhancement:** Start with zero-configuration simple providers and scale up to authenticated, feature-rich providers as needed.
*   **Developer-Friendly:**
    *   Clear interfaces and comprehensive type hints.
    *   Well-defined error types (`RetryableError`, `NonRetryableError`) for granular error handling.
    *   Factory pattern for easy and consistent provider instantiation.
*   **Extensible Design:** Providers follow a defined protocol, making it straightforward to add support for new services. Templates are available for simple and authenticated providers.
*   **Configuration Checks:** CLI tools to check if providers are correctly configured and operational, including online tests.
*   **Async/Sync Harmony:** Utilities to convert between asynchronous and synchronous functions, allowing providers to be implemented in either style while maintaining a consistent user-facing API.

## Installation

You can install `twat-fs` using several methods:

### Binary Installation (Recommended)

Download pre-built binaries from the [releases page](https://github.com/twardoch/twat-fs/releases) or use the installation scripts:

**Linux/macOS:**
```bash
curl -sSfL https://raw.githubusercontent.com/twardoch/twat-fs/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/twardoch/twat-fs/main/install.ps1 -OutFile install.ps1; .\install.ps1
```

**Manual download:**
1. Go to the [releases page](https://github.com/twardoch/twat-fs/releases)
2. Download the binary for your platform (linux, macos, or windows)
3. Make it executable and add to your PATH

### Python Package Installation

**Basic Installation (includes simple providers):**

```bash
uv pip install twat-fs
```

**Full Installation (includes all providers and development tools):**

To include support for providers like Dropbox and S3, which have additional dependencies, you can install extras:

```bash
# Install with Dropbox support
uv pip install 'twat-fs[dropbox]'

# Install with AWS S3 support
uv pip install 'twat-fs[s3]'

# Install with Fal.ai support
uv pip install 'twat-fs[fal]'

# Install all available providers
uv pip install 'twat-fs[all]'

# Install for development (includes all providers, test, and linting tools)
uv pip install 'twat-fs[all,dev]'
# Or, if cloning the repository:
# uv pip install -e '.[all,dev]'
```
*Refer to `pyproject.toml` for the full list of available extras.*

## Basic Usage

### Programmatic Usage

The core function for uploading files is `upload_file`.

```python
from twat_fs import upload_file
from twat_fs.upload_providers.core import RetryableError, NonRetryableError
from twat_fs.upload import UploadOptions # For more control
from pathlib import Path

# Simple upload (uses default provider preference: catbox.moe, then others)
try:
    file_to_upload = "path/to/your/file.txt"
    # Create a dummy file for example
    Path(file_to_upload).write_text("Hello, twat-fs!")

    url = upload_file(file_to_upload)
    print(f"File uploaded to: {url}")

    # Specify a single provider
    url_s3 = upload_file(file_to_upload, provider="s3") # Assumes S3 is configured
    print(f"Uploaded to S3: {url_s3}")

    # Specify a list of providers for fallback
    # If s3 fails, it will try dropbox, then catbox
    url_fallback = upload_file(file_to_upload, provider=["s3", "dropbox", "catbox"])
    print(f"Uploaded with fallback: {url_fallback}")

    # Using UploadOptions for more control
    options = UploadOptions(
        unique=True,      # Add a timestamp to the filename to ensure uniqueness
        fragile=False,    # Allow fallback to other providers
        # remote_path="custom/folder/" # Provider-specific remote path/prefix
    )
    url_options = upload_file(file_to_upload, provider="catbox", options=options)
    print(f"Uploaded with options: {url_options}")

except FileNotFoundError:
    print(f"Error: The file {file_to_upload} was not found.")
except RetryableError as e:
    print(f"A temporary error occurred with {e.provider}: {e}. You might want to retry.")
except NonRetryableError as e:
    print(f"A permanent error occurred with {e.provider}: {e}. Try a different provider or check configuration.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    # Clean up dummy file
    if Path(file_to_upload).exists():
        Path(file_to_upload).unlink()
```

### Command Line Interface (CLI)

`twat-fs` can be invoked directly from the command line. The main entry point is `python -m twat_fs` or the `twat-fs` script if your PATH is configured.

**Upload a file:**

```bash
# Simple upload (uses default provider preference)
python -m twat_fs upload path/to/your/file.jpg

# Specify a provider
python -m twat_fs upload path/to/your/file.jpg --provider s3

# Specify multiple providers for fallback (comma-separated, no spaces, in brackets)
python -m twat_fs upload path/to/your/file.jpg --provider "[s3,dropbox,catbox]"

# Disable fallback (fail immediately if the first provider fails)
python -m twat_fs upload path/to/your/file.jpg --provider s3 --fragile

# Upload with a unique name (adds timestamp)
python -m twat_fs upload path/to/your/file.jpg --unique

# Specify a remote path or prefix (behavior is provider-specific)
python -m twat_fs upload path/to/your/file.jpg --provider s3 --remote_path "my_uploads/"
```

**Check provider setup:**

```bash
# Check status of a specific provider (e.g., s3)
python -m twat_fs upload_provider status s3

# Check status and run an online test for a specific provider
python -m twat_fs upload_provider status s3 --online

# Check status of all configured providers
python -m twat_fs upload_provider status

# Check status and run online tests for all providers
python -m twat_fs upload_provider status --online

# List available (ready) providers
python -m twat_fs upload_provider list
```

## Provider Configuration

### Provider Fallback System

`twat-fs` implements a robust provider fallback system:

1.  **Default Preference:** If no provider is specified, `twat-fs` uses a default list (`PROVIDERS_PREFERENCE` in `twat_fs.upload_providers.__init__.py`), trying each in order.
2.  **Custom Preference:** You can specify a single provider or an ordered list of providers.
3.  **Retry and Fallback:**
    *   For a given provider, if a `RetryableError` occurs (e.g., temporary network issue), the upload is retried (default 1 retry with exponential backoff).
    *   If a `NonRetryableError` occurs (e.g., authentication failure, file too large) or retries are exhausted, `twat-fs` moves to the next provider in your list (or the default list).
4.  **Circular Fallback:** If you provide a list like `["C", "A", "B"]` and start with provider `C`, if `C` fails, it tries `A`. If `A` fails, it tries `B`. If all specified providers fail, the operation fails. If you start with the default list and, for example, provider "E" is chosen/fails, it will try "F", "G", and then cycle through "A", "B", "C", "D" if necessary, ensuring each provider is tried once.
5.  **Fragile Mode:** If `fragile=True` (programmatically) or `--fragile` (CLI) is used, `twat-fs` will not attempt any fallback. If the specified provider fails, the upload operation fails immediately.

### Simple Providers (No Configuration Required)

These providers generally work out-of-the-box for anonymous uploads:

*   **`catbox`**: catbox.moe (Default first choice)
*   **`litterbox`**: litter.catbox.moe (Temporary file uploads with expiration)
*   **`www0x0`**: 0x0.st
*   **`x0at`**: x0.at
*   **`uguu`**: uguu.se (Temporary file uploads)
*   **`tmpfilelink`**: tmpfile.link
*   **`tmpfilesorg`**: tmpfiles.org
*   **`senditsh`**: sendit.sh
*   **`filebin`**: filebin.net (Temporary, typically 6-day expiration)
*   **`pixeldrain`**: pixeldrain.com

*Note: Availability and terms of service for these providers can change. Some may have file size or type restrictions.*

### Authenticated Providers

#### Dropbox (`dropbox`)

Requires an access token. Set the following environment variable:

```bash
export DROPBOX_ACCESS_TOKEN="your_dropbox_access_token"
```

For more advanced OAuth2 setups (optional, if you need to refresh tokens):

```bash
export DROPBOX_REFRESH_TOKEN="your_dropbox_refresh_token"
export DROPBOX_APP_KEY="your_dropbox_app_key"
export DROPBOX_APP_SECRET="your_dropbox_app_secret"
```

#### AWS S3 (`s3`)

Requires AWS credentials and a bucket name. Set the following environment variables:

```bash
# Required
export AWS_S3_BUCKET="your_s3_bucket_name"
export AWS_DEFAULT_REGION="your_aws_region" # e.g., us-east-1

# Authentication (choose one method):
# 1. Access Key ID and Secret Access Key
export AWS_ACCESS_KEY_ID="your_aws_access_key_id"
export AWS_SECRET_ACCESS_KEY="your_aws_secret_access_key"
# 2. Or, configure via AWS CLI (`aws configure`) which stores credentials in ~/.aws/credentials
# 3. Or, if running in an AWS environment (like EC2, Lambda), use IAM roles.

# Optional (for S3-compatible services like MinIO, DigitalOcean Spaces):
export AWS_ENDPOINT_URL="your_custom_s3_endpoint_url"
```

#### Fal.ai (`fal`)

Requires Fal.ai credentials. Set the following environment variable:

```bash
export FAL_KEY="your_fal_key_id:your_fal_key_secret"
```

## Technical Deep Dive

### Architecture Overview

`twat-fs` is structured into several key components:

*   **`upload.py`**: Contains the main user-facing functions like `upload_file` and `setup_provider`. It orchestrates the upload process, handles provider selection, fallback logic, and retries.
*   **`cli.py`**: Implements the command-line interface using `python-fire`. It parses arguments and calls functions from `upload.py`.
*   **`upload_providers/` directory**:
    *   **`__init__.py`**: Defines the `PROVIDERS_PREFERENCE` list (default order of providers).
    *   **`factory.py` (`ProviderFactory`)**: Responsible for discovering and instantiating provider modules and their clients.
    *   **`core.py`**: Defines base classes (`BaseProvider`), core error types (`RetryableError`, `NonRetryableError`), the `@with_retry` decorator, and common utility functions.
    *   **`protocols.py`**: Defines `typing.Protocol` classes that provider modules and clients should adhere to.
    *   **Individual provider modules (e.g., `s3.py`, `catbox.py`)**: Each module implements the logic for a specific upload service. They typically define a provider client class (e.g., `S3Provider`) and necessary helper functions.
    *   **`async_utils.py`**: Provides utilities (`to_sync`, `to_async`, `run_async`) for converting between asynchronous and synchronous code, allowing provider implementations to use `async/await` while still being callable from synchronous code.

### Provider System

1.  **Discovery and Instantiation (`ProviderFactory`)**:
    *   When a provider is requested, `ProviderFactory.get_provider_module(provider_name)` attempts to import the corresponding module (e.g., `twat_fs.upload_providers.s3`).
    *   `ProviderFactory.create_provider(provider_name)` then uses the loaded module to get an instance of the provider client.
2.  **Provider Module Requirements**: Each provider module (e.g., `s3.py`) is expected to:
    *   Implement a `get_provider() -> ProviderClient | None` function that returns an instance of its client class if configured, or `None` otherwise.
    *   Implement a `get_credentials()` function (often called by `get_provider`) that retrieves necessary credentials (e.g., from environment variables).
    *   Define `PROVIDER_HELP: ProviderHelp` (a TypedDict) with `setup` and `deps` information.
    *   The client class (e.g., `S3Provider`) must implement an `upload_file(...)` method (and optionally `async_upload_file(...)`).
3.  **Credentials**: Providers typically fetch credentials from environment variables (e.g., `os.getenv("AWS_S3_BUCKET")`).

### Core Upload Logic (`upload.py`)

*   **`upload_file(...)` function**:
    *   Takes the `file_path`, an optional `provider` (string or list), and an `UploadOptions` object.
    *   If no provider is specified, it uses `PROVIDERS_PREFERENCE`.
    *   It iterates through the specified providers, attempting to upload the file.
*   **`UploadOptions`**: A dataclass holding options like `remote_path`, `unique` (add timestamp to filename), `force` (overwrite), `upload_path` (custom remote prefix), and `fragile` (disable fallback).
*   **Retry Mechanism (`@with_retry` from `core.py`)**:
    *   The internal upload attempt for each provider is often decorated with `@with_retry`.
    *   This decorator catches specified exceptions (typically `RetryableError`) and retries the operation with strategies like exponential backoff.
*   **Error Handling**:
    *   `RetryableError`: Indicates a temporary issue (e.g., network hiccup, rate limit). The system may retry with the same provider.
    *   `NonRetryableError`: Indicates a permanent issue for that provider (e.g., bad credentials, file too large, permission denied). The system will then fall back to the next provider in the list unless in `fragile` mode.

### Online Provider Testing (`setup_provider(online=True)`)

*   The `setup_provider` function (callable via CLI `upload_provider status --online`) can perform an online test.
*   The `_test_provider_online` function in `upload.py` is responsible for this:
    1.  It uses a small test file: `src/twat_fs/data/test.jpg`.
    2.  Calculates the SHA256 hash of this local file.
    3.  Attempts to upload the test file using the specified provider.
    4.  If successful, it attempts to download the file from the returned URL.
    5.  Calculates the SHA256 hash of the downloaded content.
    6.  Compares the hash of the downloaded file with the original hash.
    7.  The test passes if the upload is successful, the URL is valid, the download works, and the hashes match.
    8.  Timing metrics for read, upload, and validation are also captured.

### Async/Sync Utilities (`async_utils.py`)

To allow flexibility in provider implementation (some APIs are naturally async, others sync), `twat-fs` includes helpers:

*   **`@to_sync`**: A decorator to wrap an `async` function, making it callable from synchronous code. It runs the async function in a new event loop.
*   **`@to_async`**: A decorator to wrap a synchronous function, making it awaitable (runs the sync function in a thread pool executor).
*   **`run_async(coroutine)`**: A utility to run an async coroutine from sync code and wait for its result.

These utilities help maintain a consistent synchronous public API for `upload_file` while allowing internal provider logic to leverage asynchronous operations where beneficial.

## Development

### Setting up the Environment

1.  Clone the repository:
    ```bash
    git clone https://github.com/twardoch/twat-fs.git
    cd twat-fs
    ```
2.  Install dependencies, including development tools and all provider extras. It's recommended to use a virtual environment:
    ```bash
    # Using uv
    uv venv
    source .venv/bin/activate # Or .venv\Scripts\activate on Windows
    uv pip install -e '.[all,dev]'
    ```

### Development Scripts

The project includes convenient development scripts:

```bash
# Build the package
python scripts/build.py

# Run tests with coverage
python scripts/test.py

# Run linting checks
python scripts/lint.py

# Fix linting issues
python scripts/dev.py fix

# Build binary executable
python scripts/build_binary.py

# Prepare for release
python scripts/release.py

# Run all checks (lint, test, build)
python scripts/dev.py all
```

You can also use the Makefile:

```bash
make build    # Build the package
make test     # Run tests
make lint     # Run linting
make fix      # Fix linting issues
make all      # Run all checks
make clean    # Clean build artifacts
```

### Running Tests

The project uses `pytest`.

```bash
python scripts/test.py
# Or directly:
python -m pytest
```

### Running Linters and Formatters

The project uses `ruff` for linting and formatting.

```bash
# Check for linting issues and apply fixes
ruff check --fix --unsafe-fixes .

# Format code
ruff format .

# Combined (similar to pre-commit hooks or hatch scripts)
ruff check --output-format=github --fix --unsafe-fixes . && ruff format --respect-gitignore --target-version py310 .

# Or, using hatch if configured:
# hatch run fix
# hatch run lint
```
*Refer to `pyproject.toml` for specific hatch script definitions and pre-commit configurations.*

## Contributing

Contributions are welcome! Here's how you can help:

1.  **Check for open issues or tasks:** Look at the [Issues tab](https://github.com/twardoch/twat-fs/issues) on GitHub and the `TODO.md` file in the repository for current priorities and known bugs.
2.  **Discuss:** For new features or significant changes, please open an issue to discuss your ideas first.
3.  **Fork and Branch:** Fork the repository and create a new branch for your changes.
4.  **Develop:** Make your changes, ensuring you add or update tests as appropriate.
5.  **Test and Lint:** Run tests and linters to ensure your changes pass all checks.
6.  **Document:** Update any relevant documentation, including docstrings and the `README.md` if necessary.
7.  **Pull Request:** Submit a pull request with a clear description of your changes.

When adding new upload providers:
*   Look at existing provider modules in `src/twat_fs/upload_providers/` for examples.
*   Use the templates in the `templates/` directory (`simple_provider_template.py`, `authenticated_provider_template.py`) as a starting point.
*   Ensure your provider implements the required functions/methods and `PROVIDER_HELP`.
*   Add your new provider to `PROVIDERS_PREFERENCE` in `src/twat_fs/upload_providers/__init__.py`.
*   Add any new dependencies to `pyproject.toml` under an appropriate extra (e.g., `[project.optional-dependencies.newprovider]`).

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
