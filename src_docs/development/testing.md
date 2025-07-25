---
this_file: src_docs/development/testing.md
---

# Testing Guide

This guide covers testing strategies, tools, and best practices for twat-fs.

## Testing Philosophy

twat-fs follows these testing principles:

1. **Comprehensive Coverage**: Aim for >95% code coverage
2. **Fast Feedback**: Unit tests should run quickly
3. **Isolation**: Mock external dependencies
4. **Real-World Testing**: Integration tests with actual providers
5. **Continuous Testing**: Tests run on every commit

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── data/                    # Test files
│   ├── test.txt
│   └── test.jpg
├── test_upload.py           # Core upload tests
├── test_utils.py            # Utility tests
├── test_async_utils.py      # Async utility tests
├── test_cli.py              # CLI tests
├── test_integration.py      # Integration tests
├── test_<provider>.py       # Provider-specific tests
└── test_performance.py      # Performance benchmarks
```

## Running Tests

### Quick Test Run

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_upload.py

# Run specific test
python -m pytest tests/test_upload.py::test_upload_file_success

# Run with coverage
python -m pytest --cov=src/twat_fs --cov-report=html
```

### Using Test Scripts

```bash
# Run tests with coverage and formatting
python scripts/test.py

# Run tests in watch mode
python scripts/dev.py test --watch

# Run only unit tests
python scripts/test.py --unit

# Run only integration tests
python scripts/test.py --integration
```

## Writing Tests

### Basic Test Structure

```python
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from twat_fs import upload_file
from twat_fs.upload_providers.core import NonRetryableError

class TestUploadFile:
    """Test cases for upload_file function."""
    
    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create a temporary test file."""
        file = tmp_path / "test.txt"
        file.write_text("test content")
        return file
    
    def test_upload_success(self, temp_file):
        """Test successful file upload."""
        with patch('twat_fs.upload._try_upload_with_provider') as mock_upload:
            mock_upload.return_value.url = "https://example.com/file.txt"
            
            url = upload_file(str(temp_file))
            
            assert url == "https://example.com/file.txt"
            mock_upload.assert_called_once()
    
    def test_upload_file_not_found(self):
        """Test upload with non-existent file."""
        with pytest.raises(FileNotFoundError):
            upload_file("nonexistent.txt")
```

### Testing Providers

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
import responses

from twat_fs.upload_providers import catbox

class TestCatboxProvider:
    """Test cases for Catbox provider."""
    
    @pytest.fixture
    def provider(self):
        """Create provider instance."""
        return catbox.CatboxProvider()
    
    @responses.activate
    def test_upload_success(self, provider, tmp_path):
        """Test successful upload to Catbox."""
        # Mock HTTP response
        responses.add(
            responses.POST,
            "https://catbox.moe/user/api.php",
            body="https://files.catbox.moe/abc123.jpg",
            status=200
        )
        
        # Create test file
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake image data")
        
        # Upload file
        result = provider.upload_file(str(test_file))
        
        # Verify result
        assert result.url == "https://files.catbox.moe/abc123.jpg"
        assert result.metadata["provider"] == "catbox"
    
    def test_upload_file_too_large(self, provider):
        """Test upload of file exceeding size limit."""
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value.st_size = 300 * 1024 * 1024  # 300MB
            
            with pytest.raises(NonRetryableError) as exc_info:
                provider.upload_file("large.zip")
            
            assert "too large" in str(exc_info.value).lower()
```

### Testing Async Code

```python
import pytest
import asyncio
from twat_fs.upload_providers.async_utils import gather_with_concurrency

class TestAsyncUtils:
    """Test cases for async utilities."""
    
    @pytest.mark.asyncio
    async def test_gather_with_concurrency(self):
        """Test concurrent execution with limit."""
        results = []
        
        async def task(i):
            await asyncio.sleep(0.1)
            results.append(i)
            return i * 2
        
        tasks = [task(i) for i in range(5)]
        outputs = await gather_with_concurrency(2, *tasks)
        
        # Verify all tasks completed
        assert len(results) == 5
        assert outputs == [0, 2, 4, 6, 8]
    
    @pytest.mark.asyncio
    async def test_gather_with_exceptions(self):
        """Test exception handling in concurrent execution."""
        async def failing_task():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            await gather_with_concurrency(1, failing_task())
```

### Mock Fixtures

Create reusable mocks in `conftest.py`:

```python
# tests/conftest.py
import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path

@pytest.fixture
def mock_provider():
    """Create a mock provider."""
    provider = Mock()
    provider.provider_name = "mock"
    provider.upload_file.return_value = Mock(
        url="https://mock.example.com/file.jpg",
        metadata={"provider": "mock"}
    )
    return provider

@pytest.fixture
def mock_factory(mock_provider):
    """Mock the provider factory."""
    with patch('twat_fs.upload_providers.ProviderFactory') as factory:
        factory.create_provider.return_value = mock_provider
        yield factory

@pytest.fixture
def test_image():
    """Path to test image file."""
    return Path(__file__).parent / "data" / "test.jpg"

@pytest.fixture
def env_setup(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("DROPBOX_ACCESS_TOKEN", "test-token")
```

## Test Categories

### Unit Tests

Fast, isolated tests for individual components:

```python
@pytest.mark.unit
class TestUploadOptions:
    """Unit tests for UploadOptions."""
    
    def test_default_values(self):
        """Test default option values."""
        options = UploadOptions()
        assert options.unique is False
        assert options.fragile is False
        assert options.remote_path is None
    
    def test_custom_values(self):
        """Test custom option values."""
        options = UploadOptions(
            unique=True,
            remote_path="uploads/"
        )
        assert options.unique is True
        assert options.remote_path == "uploads/"
```

### Integration Tests

Test interaction between components:

```python
@pytest.mark.integration
class TestProviderIntegration:
    """Integration tests for providers."""
    
    @pytest.mark.skipif(
        not os.getenv("RUN_INTEGRATION_TESTS"),
        reason="Integration tests disabled"
    )
    def test_s3_upload_integration(self, test_image):
        """Test actual S3 upload."""
        # This test requires real AWS credentials
        url = upload_file(test_image, provider="s3")
        
        # Verify file is accessible
        response = requests.head(url)
        assert response.status_code in (200, 403)  # 403 if private
```

### Performance Tests

Benchmark critical operations:

```python
@pytest.mark.benchmark
def test_upload_performance(benchmark, temp_file, mock_provider):
    """Benchmark upload performance."""
    with patch('twat_fs.upload_providers.ProviderFactory.create_provider',
               return_value=mock_provider):
        result = benchmark(upload_file, str(temp_file))
        assert result.startswith("https://")

@pytest.mark.benchmark
def test_provider_creation_performance(benchmark):
    """Benchmark provider creation."""
    def create_providers():
        for name in PROVIDERS_PREFERENCE:
            ProviderFactory.create_provider(name)
    
    benchmark(create_providers)
```

### CLI Tests

Test command-line interface:

```python
from click.testing import CliRunner
from twat_fs.cli import cli

class TestCLI:
    """Test cases for CLI."""
    
    def test_upload_command(self, temp_file):
        """Test upload command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['upload', str(temp_file)])
        
        assert result.exit_code == 0
        assert "https://" in result.output
    
    def test_version_command(self):
        """Test version command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['version'])
        
        assert result.exit_code == 0
        assert "twat-fs" in result.output
```

## Mocking Strategies

### Mock External Services

```python
# Mock HTTP requests
@responses.activate
def test_http_upload():
    responses.add(
        responses.POST,
        "https://api.example.com/upload",
        json={"url": "https://example.com/file.jpg"},
        status=200
    )
    # Test code here

# Mock file system
@patch('pathlib.Path.exists', return_value=True)
@patch('pathlib.Path.stat')
def test_file_operations(mock_stat, mock_exists):
    mock_stat.return_value.st_size = 1024
    # Test code here

# Mock time-based operations
@patch('time.time', return_value=1234567890)
def test_timing(mock_time):
    # Test code here
```

### Mock Provider Modules

```python
@patch.dict('sys.modules', {
    'twat_fs.upload_providers.custom': Mock(
        get_provider=Mock(return_value=mock_provider),
        PROVIDER_HELP={"setup": "Test", "deps": ""}
    )
})
def test_custom_provider():
    # Test code here
```

## Test Data Management

### Creating Test Files

```python
@pytest.fixture
def create_test_files(tmp_path):
    """Create various test files."""
    files = {}
    
    # Text file
    files['text'] = tmp_path / "test.txt"
    files['text'].write_text("Hello, World!")
    
    # Binary file
    files['binary'] = tmp_path / "test.bin"
    files['binary'].write_bytes(b'\x00\x01\x02\x03')
    
    # Large file
    files['large'] = tmp_path / "large.bin"
    files['large'].write_bytes(b'0' * (10 * 1024 * 1024))  # 10MB
    
    return files
```

### Test Data Constants

```python
# tests/constants.py
TEST_URLS = {
    'catbox': 'https://files.catbox.moe/test123.jpg',
    'litterbox': 'https://litter.catbox.moe/test456.jpg',
    's3': 'https://bucket.s3.region.amazonaws.com/test.jpg',
}

TEST_PROVIDERS = ['catbox', 'litterbox', 'www0x0']

TEST_FILES = {
    'small': 1024,  # 1KB
    'medium': 1024 * 1024,  # 1MB  
    'large': 100 * 1024 * 1024,  # 100MB
}
```

## Coverage Configuration

Configure coverage in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src/twat_fs"]
omit = [
    "*/tests/*",
    "*/__main__.py",
    "*/templates/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "@abstractmethod",
]
precision = 2
show_missing = true

[tool.coverage.html]
directory = "htmlcov"
```

## Continuous Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.10', '3.11', '3.12']
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -e '.[all,dev]'
    
    - name: Run tests
      run: |
        pytest --cov=src/twat_fs --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Best Practices

### 1. Test Naming

Use descriptive test names:

```python
# Good
def test_upload_file_with_nonexistent_path_raises_file_not_found():
def test_s3_provider_with_invalid_credentials_raises_auth_error():

# Bad  
def test_upload():
def test_error():
```

### 2. Test Independence

Tests should not depend on each other:

```python
# Good - each test sets up its own data
def test_one(tmp_path):
    file = tmp_path / "test1.txt"
    file.write_text("data")
    # test logic

def test_two(tmp_path):
    file = tmp_path / "test2.txt"
    file.write_text("data")
    # test logic

# Bad - tests share state
class TestShared:
    file = None
    
    def test_create(self):
        self.file = "test.txt"
    
    def test_use(self):
        # Depends on test_create running first
        upload_file(self.file)
```

### 3. Mock Responsibly

Only mock what you own:

```python
# Good - mock our provider interface
mock_provider = Mock(spec=ProviderClient)

# Questionable - mock third-party library internals
with patch('requests.Session._request'):
    # Might break with library updates
```

### 4. Test Error Cases

Always test error conditions:

```python
def test_upload_errors():
    """Test various error conditions."""
    # File not found
    with pytest.raises(FileNotFoundError):
        upload_file("nonexistent.txt")
    
    # Directory instead of file
    with pytest.raises(ValueError):
        upload_file("/tmp")
    
    # Provider failure
    with patch('twat_fs.upload._try_upload_with_provider',
               side_effect=NonRetryableError("Failed", "test")):
        with pytest.raises(NonRetryableError):
            upload_file("file.txt")
```

### 5. Use Parametrized Tests

Test multiple scenarios efficiently:

```python
@pytest.mark.parametrize("provider,expected_url", [
    ("catbox", "https://files.catbox.moe/"),
    ("litterbox", "https://litter.catbox.moe/"),
    ("www0x0", "https://0x0.st/"),
])
def test_provider_urls(provider, expected_url, temp_file):
    """Test that each provider returns correct URL format."""
    with patch(f'twat_fs.upload_providers.{provider}.upload_file') as mock:
        mock.return_value.url = f"{expected_url}test.jpg"
        
        url = upload_file(temp_file, provider=provider)
        assert url.startswith(expected_url)
```

## Debugging Tests

### Run with verbose output

```bash
pytest -vvs tests/test_upload.py::test_specific
```

### Use debugger

```python
def test_complex_logic():
    import pdb; pdb.set_trace()  # Debugger breakpoint
    # Test code
```

### Print debug info

```python
def test_with_logging(caplog):
    """Test with captured logs."""
    with caplog.at_level(logging.DEBUG):
        upload_file("test.txt")
    
    # Check logs
    assert "Starting upload" in caplog.text
```

## Next Steps

- [Contributing Guide](contributing.md) - How to contribute
- [Architecture](architecture.md) - System design
- [Provider Development](provider-development.md) - Create providers