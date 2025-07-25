---
this_file: src_docs/development/contributing.md
---

# Contributing Guide

Thank you for your interest in contributing to twat-fs! This guide will help you get started.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- Basic understanding of Python and async programming
- Familiarity with pytest for testing

### Development Setup

1. **Fork and Clone**

   ```bash
   # Fork the repository on GitHub, then:
   git clone https://github.com/YOUR_USERNAME/twat-fs.git
   cd twat-fs
   ```

2. **Create Virtual Environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Development Dependencies**

   ```bash
   # Install with all providers and dev tools
   pip install -e '.[all,dev]'
   
   # Or using uv (recommended)
   uv pip install -e '.[all,dev]'
   ```

4. **Install Pre-commit Hooks**

   ```bash
   pre-commit install
   ```

5. **Verify Setup**

   ```bash
   # Run tests
   python scripts/test.py
   
   # Run linting
   python scripts/lint.py
   
   # Check installation
   twat-fs version
   ```

## Development Workflow

### 1. Create a Branch

```bash
# For features
git checkout -b feature/your-feature-name

# For bug fixes
git checkout -b fix/issue-description

# For documentation
git checkout -b docs/what-you-are-documenting
```

### 2. Make Your Changes

Follow the coding standards and ensure:
- Code is properly formatted
- Tests are added/updated
- Documentation is updated
- Commits are logical and well-described

### 3. Test Your Changes

```bash
# Run all tests
python scripts/test.py

# Run specific tests
pytest tests/test_upload.py::test_specific_function

# Run with coverage
pytest --cov=src/twat_fs --cov-report=html

# Run linting
python scripts/lint.py
```

### 4. Commit Your Changes

Write clear, concise commit messages:

```bash
# Good commit messages
git commit -m "Add retry logic to S3 provider"
git commit -m "Fix timeout issue in large file uploads"
git commit -m "Update installation docs for Windows users"

# Bad commit messages
git commit -m "Fix bug"
git commit -m "Update code"
git commit -m "Changes"
```

### 5. Push and Create Pull Request

```bash
git push origin your-branch-name
```

Then create a pull request on GitHub with:
- Clear description of changes
- Reference to any related issues
- Screenshots/examples if applicable

## Coding Standards

### Python Style

We use `ruff` for linting and formatting. The configuration is in `pyproject.toml`.

```python
# Good - follows PEP 8 and project conventions
from pathlib import Path
from typing import Optional

def upload_file(
    file_path: str | Path,
    provider: str | None = None,
) -> str:
    """Upload a file to the specified provider.
    
    Args:
        file_path: Path to the file to upload
        provider: Name of the provider to use
        
    Returns:
        URL of the uploaded file
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    # Implementation here
    return upload_url
```

### Type Hints

Always use type hints:

```python
from typing import Any, Optional
from pathlib import Path

# Good - fully typed
def process_file(
    file_path: str | Path,
    options: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    ...

# Bad - missing type hints
def process_file(file_path, options=None):
    ...
```

### Error Handling

Use appropriate exception types:

```python
from twat_fs.upload_providers.core import RetryableError, NonRetryableError

# Good - specific exceptions
if response.status_code == 429:
    raise RetryableError("Rate limited", provider_name)
elif response.status_code == 401:
    raise NonRetryableError("Invalid credentials", provider_name)

# Bad - generic exceptions
if response.status_code != 200:
    raise Exception("Upload failed")
```

### Logging

Use loguru for logging:

```python
from loguru import logger

# Good - appropriate log levels
logger.debug(f"Starting upload of {file_path}")
logger.info(f"Successfully uploaded to {url}")
logger.warning(f"Retrying after error: {error}")
logger.error(f"Upload failed: {error}")

# Bad - print statements
print(f"Uploading {file_path}")
```

### Documentation

All public functions need docstrings:

```python
def upload_file(
    file_path: str | Path,
    provider: str | None = None,
    options: UploadOptions | None = None,
) -> str:
    """
    Upload a file using the specified provider(s) with automatic fallback.
    
    This function handles the complete upload process including:
    - File validation
    - Provider selection and fallback
    - Retry logic for temporary failures
    - URL validation
    
    Args:
        file_path: Path to the file to upload. Can be absolute or relative.
        provider: Provider name or list of providers to try in order.
                 If None, uses the default preference list.
        options: Upload options including remote path, unique naming, etc.
    
    Returns:
        URL where the uploaded file can be accessed.
        
    Raises:
        FileNotFoundError: If the specified file doesn't exist.
        ValueError: If the path points to a directory or no valid providers.
        NonRetryableError: If all providers fail with permanent errors.
        
    Example:
        >>> url = upload_file("document.pdf", provider="s3")
        >>> print(f"File available at: {url}")
        File available at: https://bucket.s3.amazonaws.com/document.pdf
    """
```

## Testing Guidelines

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch

class TestFeatureName:
    """Test cases for FeatureName."""
    
    @pytest.fixture
    def setup_data(self):
        """Fixture providing test data."""
        return {"key": "value"}
    
    def test_normal_operation(self, setup_data):
        """Test the happy path."""
        # Arrange
        expected = "expected_result"
        
        # Act
        result = function_under_test(setup_data)
        
        # Assert
        assert result == expected
    
    def test_error_condition(self):
        """Test error handling."""
        with pytest.raises(ValueError) as exc_info:
            function_under_test(invalid_data)
        
        assert "specific error message" in str(exc_info.value)
```

### Test Coverage

Aim for >95% test coverage:

```bash
# Check coverage
pytest --cov=src/twat_fs --cov-report=term-missing

# Generate HTML report
pytest --cov=src/twat_fs --cov-report=html
open htmlcov/index.html
```

### Mock External Dependencies

```python
@patch('requests.post')
def test_external_api_call(mock_post):
    """Test function that calls external API."""
    # Configure mock
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"url": "https://example.com"}
    
    # Test code
    result = upload_to_api("file.txt")
    
    # Verify
    assert result == "https://example.com"
    mock_post.assert_called_once_with(
        "https://api.example.com/upload",
        files=ANY,
        timeout=300
    )
```

## Adding New Features

### 1. New Provider

See the [Provider Development Guide](provider-development.md) for detailed instructions.

Quick checklist:
- [ ] Create provider module in `src/twat_fs/upload_providers/`
- [ ] Implement required functions and classes
- [ ] Add to `PROVIDERS_PREFERENCE` list
- [ ] Create tests in `tests/test_<provider>.py`
- [ ] Update documentation
- [ ] Add to provider comparison table

### 2. New Core Feature

1. **Discuss First**: Open an issue to discuss the feature
2. **Design**: Consider the API and implementation
3. **Implement**: Add the feature with tests
4. **Document**: Update relevant documentation
5. **Example**: Provide usage examples

### 3. Bug Fixes

1. **Reproduce**: Create a failing test that demonstrates the bug
2. **Fix**: Implement the minimal fix
3. **Test**: Ensure the test now passes
4. **Verify**: Run full test suite
5. **Document**: Add to CHANGELOG.md

## Documentation

### Documentation Structure

```
src_docs/
├── index.md                    # Home page
├── getting-started/            # Installation, setup
├── user-guide/                 # Usage documentation
├── development/                # Developer docs
└── about/                      # Project info
```

### Writing Documentation

- Use clear, concise language
- Include code examples
- Add diagrams where helpful
- Test all code examples
- Keep it up-to-date

### Building Documentation

```bash
# Serve locally
mkdocs serve

# Build static site
mkdocs build

# Deploy to GitHub Pages
mkdocs gh-deploy
```

## Pull Request Process

### Before Submitting

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated
- [ ] Commit messages are clear
- [ ] Branch is up-to-date with main

### PR Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Related Issues
Fixes #123

## Screenshots (if applicable)
```

### Review Process

1. **Automated Checks**: CI runs tests, linting, and coverage
2. **Code Review**: Maintainers review code quality
3. **Testing**: Reviewers may test locally
4. **Feedback**: Address any requested changes
5. **Merge**: Once approved, PR is merged

## Release Process

### Version Numbering

We use semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking API changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Release Steps

1. **Update Version**: Update version in `pyproject.toml`
2. **Update CHANGELOG**: Document all changes
3. **Create Tag**: `git tag v1.2.3`
4. **Push Tag**: `git push origin v1.2.3`
5. **CI Publishes**: Automated publish to PyPI

## Community

### Code of Conduct

We follow the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/). 

Key points:
- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the community

### Getting Help

- **Discord/Slack**: Join our chat (if available)
- **Issues**: Open a GitHub issue
- **Discussions**: Use GitHub Discussions
- **Email**: Contact maintainers

### Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

## Common Tasks

### Update Dependencies

```bash
# Update all dependencies
pip install --upgrade -r requirements-dev.txt

# Update specific dependency
pip install --upgrade pytest

# Lock dependencies
pip freeze > requirements.lock
```

### Run Formatting

```bash
# Format code
ruff format src/ tests/

# Sort imports
ruff check --select I --fix src/ tests/
```

### Build Package

```bash
# Build distribution
python scripts/build.py

# Test installation
pip install dist/twat_fs-*.whl
```

### Debug Issues

```bash
# Run with debug logging
LOGURU_LEVEL=DEBUG twat-fs upload test.txt

# Run tests with debugging
pytest -xvs tests/test_specific.py::test_function --pdb
```

## Thank You!

Your contributions make twat-fs better for everyone. We appreciate your time and effort!

## Next Steps

- [Architecture Overview](architecture.md) - Understand the codebase
- [Provider Development](provider-development.md) - Add new providers
- [Testing Guide](testing.md) - Write effective tests
- [API Reference](api-reference.md) - Detailed API docs