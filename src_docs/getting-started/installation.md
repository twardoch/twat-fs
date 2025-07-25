---
this_file: src_docs/getting-started/installation.md
---

# Installation

twat-fs can be installed using several methods, depending on your needs and platform.

## Binary Installation (Recommended)

The easiest way to install twat-fs is to download a pre-built binary for your platform. This requires no Python installation and includes all dependencies.

### Automatic Installation

**Linux/macOS:**
```bash
curl -sSfL https://raw.githubusercontent.com/twardoch/twat-fs/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
Invoke-WebRequest -Uri https://raw.githubusercontent.com/twardoch/twat-fs/main/install.ps1 -OutFile install.ps1; .\install.ps1
```

### Manual Binary Download

1. Go to the [releases page](https://github.com/twardoch/twat-fs/releases)
2. Download the binary for your platform:
   - `twat-fs-linux-x64` for Linux
   - `twat-fs-macos-x64` for macOS (Intel)
   - `twat-fs-macos-arm64` for macOS (Apple Silicon)
   - `twat-fs-windows-x64.exe` for Windows
3. Make it executable (Linux/macOS):
   ```bash
   chmod +x twat-fs-*
   ```
4. Move it to a directory in your PATH:
   ```bash
   # Linux/macOS
   sudo mv twat-fs-* /usr/local/bin/twat-fs
   
   # Windows
   # Add the directory containing twat-fs.exe to your PATH
   ```

## Python Package Installation

If you prefer to install twat-fs as a Python package, you can use pip or uv.

### Prerequisites

- Python 3.10 or higher
- pip or uv package manager

### Basic Installation

Install twat-fs with basic providers (no additional dependencies):

```bash
# Using pip
pip install twat-fs

# Using uv (recommended)
uv pip install twat-fs
```

### Installation with Provider Support

Some providers require additional dependencies. You can install these using extras:

```bash
# Dropbox support
uv pip install 'twat-fs[dropbox]'

# AWS S3 support
uv pip install 'twat-fs[s3]'

# Fal.ai support
uv pip install 'twat-fs[fal]'

# All providers
uv pip install 'twat-fs[all]'
```

### Development Installation

If you want to contribute to twat-fs or modify the code:

```bash
# Clone the repository
git clone https://github.com/twardoch/twat-fs.git
cd twat-fs

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode with all dependencies
uv pip install -e '.[all,dev]'
```

## Verifying Installation

After installation, verify that twat-fs is working:

```bash
# Check version
twat-fs --version

# Show help
twat-fs --help

# List available providers
twat-fs upload_provider list
```

## Upgrading

### Binary Upgrade

Re-run the installation script or download the latest binary from the releases page.

### Python Package Upgrade

```bash
# Using pip
pip install --upgrade twat-fs

# Using uv
uv pip install --upgrade twat-fs
```

## Uninstalling

### Binary Uninstall

Simply remove the binary from your system:

```bash
# Linux/macOS
sudo rm /usr/local/bin/twat-fs

# Windows
# Remove twat-fs.exe from its installation directory
```

### Python Package Uninstall

```bash
# Using pip
pip uninstall twat-fs

# Using uv
uv pip uninstall twat-fs
```

## Platform-Specific Notes

### Linux

- The binary is statically linked and should work on most Linux distributions
- Tested on Ubuntu 20.04+, Debian 10+, CentOS 8+, Fedora 32+

### macOS

- Binaries are provided for both Intel (x64) and Apple Silicon (arm64)
- The installer script automatically detects your architecture
- You may need to allow the binary in System Preferences > Security & Privacy

### Windows

- The Windows binary is a standalone .exe file
- Windows Defender may flag it as an unknown app - click "More info" and "Run anyway"
- Add the installation directory to your PATH for command-line access

## Troubleshooting

### Permission Denied

If you get a "permission denied" error when running the binary:

```bash
chmod +x twat-fs
```

### Command Not Found

If the system can't find twat-fs:

1. Check that the binary is in your PATH:
   ```bash
   echo $PATH
   ```
2. Add the directory containing twat-fs to your PATH
3. Or use the full path to the binary

### SSL Certificate Errors

If you encounter SSL errors when uploading:

```bash
# Install certificates (macOS)
pip install --upgrade certifi

# Set certificate bundle (Linux)
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
```

### Python Version Issues

twat-fs requires Python 3.10+. Check your version:

```bash
python --version
```

If you have an older version, consider using the binary installation instead.

## Next Steps

- [Quick Start Guide](quickstart.md) - Get started with your first upload
- [Configuration](configuration.md) - Configure providers and settings
- [CLI Reference](../user-guide/cli-reference.md) - Detailed command documentation