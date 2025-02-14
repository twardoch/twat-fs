# twat-fs

File system utilities for twat.

## Features

- File upload functionality with multiple providers (FAL, Dropbox)
- Modern Python packaging with PEP 621 compliance
- Type hints and runtime type checking
- Comprehensive test suite and documentation
- CI/CD ready configuration

## Installation

```bash
pip install twat-fs
```

## Usage

### Python API

```python
from twat_fs import upload_file

# Upload using default provider (FAL)
url = upload_file("path/to/file.txt")

# Upload using Dropbox provider
url = upload_file("path/to/file.txt", provider="dropbox")
```

### Command Line Interface

```bash
# Upload using default provider (FAL)
python -m twat_fs upload_file --file_path path/to/file.txt

# Upload using Dropbox provider
python -m twat_fs upload_file --file_path path/to/file.txt --provider dropbox
```

### Provider Configuration

#### FAL Provider
No configuration needed.

#### Dropbox Provider
Set your Dropbox API token in the environment:
```bash
export DROPBOX_APP_TOKEN="your_token_here"
```

## Development

This project uses [Hatch](https://hatch.pypa.io/) for development workflow management.

### Setup Development Environment

```bash
# Install hatch if you haven't already
pip install hatch

# Create and activate development environment
hatch shell

# Run tests
hatch run test

# Run tests with coverage
hatch run test-cov

# Run linting
hatch run lint

# Format code
hatch run format
```

## License

MIT License 