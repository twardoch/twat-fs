# Manual GitHub Actions Workflow Setup

Due to GitHub App permission restrictions, the workflow files need to be manually added to the repository. Here are the complete workflow files that need to be created:

## 1. Enhanced CI Workflow

**File:** `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ["3.10", "3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Fetch all history for version detection
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install uv
      uses: astral-sh/setup-uv@v3
    
    - name: Create virtual environment
      run: uv venv --python ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: uv pip install -e '.[all,dev,test]'
    
    - name: Run linting
      run: |
        uv pip install ruff mypy
        uv run python -m ruff check src/twat_fs tests --output-format=github
        uv run python -m ruff format --check src/twat_fs tests
    
    - name: Run type checking
      run: |
        uv run python -m mypy src/twat_fs tests --install-types --non-interactive
      continue-on-error: true  # MyPy can be strict, don't fail CI
    
    - name: Run tests
      run: |
        uv run python -m pytest -v --cov=src/twat_fs --cov-report=xml --cov-report=term-missing tests/
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v4
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
        fail_ci_if_error: false

  build:
    needs: test
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    
    - name: Install uv
      uses: astral-sh/setup-uv@v3
    
    - name: Install build dependencies
      run: uv pip install build twine
    
    - name: Build package
      run: uv run python -m build
    
    - name: Check package
      run: uv run python -m twine check dist/*
    
    - name: Upload build artifacts
      uses: actions/upload-artifact@v4
      with:
        name: dist
        path: dist/
```

## 2. Enhanced Release Workflow

**File:** `.github/workflows/release.yml` (UPDATE EXISTING)

The existing release workflow should be updated to include binary building. Here's the complete enhanced version:

```yaml
name: Release

on:
  push:
    tags: ["v*"]

permissions:
  contents: write
  id-token: write

jobs:
  release:
    name: Release to PyPI
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/twat-fs
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install UV
        uses: astral-sh/setup-uv@v5
        with:
          version: "latest"
          python-version: "3.12"
          enable-cache: true

      - name: Install build tools
        run: uv pip install build hatchling hatch-vcs

      - name: Build distributions
        run: uv run python -m build --outdir dist

      - name: Verify distribution files
        run: |
          ls -la dist/
          test -n "$(find dist -name '*.whl')" || (echo "Wheel file missing" && exit 1)
          test -n "$(find dist -name '*.tar.gz')" || (echo "Source distribution missing" && exit 1)

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_TOKEN }}

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*
          generate_release_notes: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  build-binaries:
    name: Build binaries
    needs: release
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        include:
          - os: ubuntu-latest
            platform: linux
            binary_name: twat-fs
          - os: windows-latest
            platform: windows
            binary_name: twat-fs.exe
          - os: macos-latest
            platform: macos
            binary_name: twat-fs
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      with:
        fetch-depth: 0
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    
    - name: Install UV
      uses: astral-sh/setup-uv@v5
      with:
        version: "latest"
        python-version: "3.12"
        enable-cache: true
    
    - name: Install dependencies
      run: uv pip install -e '.[all]' pyinstaller
    
    - name: Build binary
      run: |
        uv run pyinstaller --onefile --name ${{ matrix.binary_name }} \
          --add-data "src/twat_fs/data:twat_fs/data" \
          --hidden-import twat_fs.upload_providers.catbox \
          --hidden-import twat_fs.upload_providers.litterbox \
          --hidden-import twat_fs.upload_providers.www0x0 \
          --hidden-import twat_fs.upload_providers.uguu \
          --hidden-import twat_fs.upload_providers.bashupload \
          --hidden-import twat_fs.upload_providers.filebin \
          --hidden-import twat_fs.upload_providers.pixeldrain \
          --hidden-import twat_fs.upload_providers.dropbox \
          --hidden-import twat_fs.upload_providers.s3 \
          --hidden-import twat_fs.upload_providers.fal \
          src/twat_fs/__main__.py
    
    - name: Test binary
      run: |
        ./dist/${{ matrix.binary_name }} version
      shell: bash
    
    - name: Upload binary to release
      uses: softprops/action-gh-release@v1
      with:
        files: dist/${{ matrix.binary_name }}
        tag_name: ${{ github.ref_name }}
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Setup Instructions

1. **Create the CI workflow:**
   - Navigate to `.github/workflows/` in your repository
   - Create a new file named `ci.yml`
   - Copy the CI workflow content above into the file

2. **Update the release workflow:**
   - Open `.github/workflows/release.yml` in your repository
   - Replace the entire content with the enhanced release workflow above

3. **Verify the setup:**
   - The CI workflow will run on every push to main/develop branches and on pull requests
   - The release workflow will run when you create a new git tag (e.g., `v2.6.0`)

## Testing the Setup

1. **Test CI workflow:**
   - Push changes to a branch and create a pull request
   - The CI workflow should run automatically

2. **Test release workflow:**
   - Create a new git tag: `git tag v2.6.0`
   - Push the tag: `git push origin v2.6.0`
   - The release workflow should build the package, publish to PyPI, and create binaries

## Important Notes

- The binary building requires PyInstaller and may take some time
- The binaries will be automatically uploaded to the GitHub release
- The installation scripts (`install.sh` and `install.ps1`) will work once the binaries are available
- Make sure you have the necessary secrets configured in your repository:
  - `PYPI_TOKEN` for PyPI publishing
  - `GITHUB_TOKEN` (automatically provided by GitHub Actions)