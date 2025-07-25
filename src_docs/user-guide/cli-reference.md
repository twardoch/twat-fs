---
this_file: src_docs/user-guide/cli-reference.md
---

# CLI Reference

Complete reference for all twat-fs command-line interface commands and options.

## Global Options

These options can be used with any twat-fs command:

```bash
twat-fs [global_options] <command> [command_options]
```

| Option | Description |
|--------|-------------|
| `--help`, `-h` | Show help message and exit |
| `--version` | Show version information |
| `--verbose`, `-v` | Enable verbose output |
| `--quiet`, `-q` | Suppress non-error output |

## Commands

### twat-fs upload

Upload a file to a storage provider.

**Syntax:**
```bash
twat-fs upload <file_path> [options]
```

**Arguments:**
- `file_path` - Path to the file to upload (required)

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--provider` | str\|list | auto | Provider(s) to use. Can be a single provider or comma-separated list in brackets |
| `--remote_path` | str | None | Remote path/prefix for the uploaded file (provider-dependent) |
| `--unique` | flag | False | Add timestamp to filename to ensure uniqueness |
| `--force` | flag | False | Force overwrite if file exists (provider-dependent) |
| `--fragile` | flag | False | Fail immediately without fallback if provider fails |

**Examples:**

```bash
# Simple upload
twat-fs upload photo.jpg

# Upload to specific provider
twat-fs upload document.pdf --provider s3

# Upload with fallback providers
twat-fs upload important.zip --provider "[s3,dropbox,catbox]"

# Upload with unique filename
twat-fs upload report.csv --unique

# Upload to specific S3 path
twat-fs upload backup.tar.gz --provider s3 --remote_path "backups/2024/"

# Fail fast without fallback
twat-fs upload critical.doc --provider s3 --fragile
```

**Exit Codes:**
- `0` - Upload successful
- `1` - General error
- `2` - File not found
- `3` - Provider not configured
- `4` - Upload failed
- `5` - Network error

### twat-fs upload_provider

Manage upload providers.

**Subcommands:**
- `list` - List available providers
- `status` - Check provider status

#### upload_provider list

List all available (configured) providers.

**Syntax:**
```bash
twat-fs upload_provider list
```

**Example:**
```bash
$ twat-fs upload_provider list
Available providers:
- catbox
- litterbox  
- www0x0
- s3
- dropbox
```

#### upload_provider status

Check the status of one or all providers.

**Syntax:**
```bash
twat-fs upload_provider status [provider_name] [options]
```

**Arguments:**
- `provider_name` - Name of the provider to check (optional)

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--online` | flag | False | Perform online test by uploading a test file |
| `--verbose` | flag | False | Show detailed setup instructions |

**Examples:**

```bash
# Check all providers
twat-fs upload_provider status

# Check specific provider
twat-fs upload_provider status s3

# Check with online test
twat-fs upload_provider status dropbox --online

# Check all providers with online test
twat-fs upload_provider status --online
```

**Output Format:**
```
Provider: s3
Status: ✓ Ready
Setup: Configured via environment variables
Test: Upload 1.2s, Download 0.5s (when --online used)
```

### twat-fs version

Show version information.

**Syntax:**
```bash
twat-fs version
```

**Example:**
```bash
$ twat-fs version
twat-fs 2.5.4
```

## Provider Names

Valid provider names for use with `--provider`:

| Provider | Name | Type |
|----------|------|------|
| Catbox | `catbox` | Simple |
| Litterbox | `litterbox` | Simple |
| 0x0.st | `www0x0` | Simple |
| Uguu | `uguu` | Simple |
| Bashupload | `bashupload` | Simple |
| Filebin | `filebin` | Simple |
| Pixeldrain | `pixeldrain` | Simple |
| Dropbox | `dropbox` | Authenticated |
| AWS S3 | `s3` | Authenticated |
| Fal.ai | `fal` | Authenticated |

## Environment Variables

Configure twat-fs behavior and providers:

### General Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `LOGURU_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `TWAT_FS_TIMEOUT` | Upload timeout in seconds | 300 |
| `TWAT_FS_DEFAULT_PROVIDER` | Default provider if none specified | catbox |

### Provider Credentials

**Dropbox:**
- `DROPBOX_ACCESS_TOKEN` - Dropbox API access token (required)
- `DROPBOX_REFRESH_TOKEN` - OAuth2 refresh token (optional)
- `DROPBOX_APP_KEY` - Dropbox app key (optional)
- `DROPBOX_APP_SECRET` - Dropbox app secret (optional)

**AWS S3:**
- `AWS_S3_BUCKET` - S3 bucket name (required)
- `AWS_DEFAULT_REGION` - AWS region (required)
- `AWS_ACCESS_KEY_ID` - AWS access key (required*)
- `AWS_SECRET_ACCESS_KEY` - AWS secret key (required*)
- `AWS_ENDPOINT_URL` - Custom S3 endpoint (optional)

\* Not required if using IAM roles or AWS CLI configuration

**Fal.ai:**
- `FAL_KEY` - Fal.ai API key in format "key_id:key_secret" (required)

## Configuration Files

While twat-fs doesn't directly read configuration files, you can use shell features:

**.env file:**
```bash
# .env
DROPBOX_ACCESS_TOKEN=xxx
AWS_S3_BUCKET=my-bucket
AWS_DEFAULT_REGION=us-east-1
```

**Loading:**
```bash
# Bash/Zsh
export $(cat .env | xargs)

# Or use direnv
echo "dotenv" > .envrc
direnv allow
```

## Advanced Usage

### Provider Lists

Specify multiple providers for fallback:

```bash
# List format
twat-fs upload file.jpg --provider "[s3,dropbox,catbox]"

# The system will try:
# 1. s3 first
# 2. dropbox if s3 fails  
# 3. catbox if dropbox fails
```

### Shell Integration

**Bash Completion:**
```bash
# Add to ~/.bashrc
complete -W "upload upload_provider version" twat-fs
complete -W "list status" twat-fs_upload_provider
```

**Aliases:**
```bash
# Add to ~/.bashrc or ~/.zshrc
alias tfu='twat-fs upload'
alias tfp='twat-fs upload_provider'
alias tfs='twat-fs upload --provider s3'
```

### Scripting Examples

**Upload with error handling:**
```bash
#!/bin/bash
file="$1"
if [ -z "$file" ]; then
    echo "Usage: $0 <file>"
    exit 1
fi

url=$(twat-fs upload "$file" 2>&1)
if [ $? -eq 0 ]; then
    echo "Success: $url"
    echo "$url" | pbcopy  # Copy to clipboard (macOS)
else
    echo "Failed: $url"
    exit 1
fi
```

**Batch upload with logging:**
```bash
#!/bin/bash
log_file="uploads_$(date +%Y%m%d_%H%M%S).log"

for file in *.pdf; do
    echo -n "Uploading $file... " | tee -a "$log_file"
    if url=$(twat-fs upload "$file" 2>/dev/null); then
        echo "OK: $url" | tee -a "$log_file"
    else
        echo "FAILED" | tee -a "$log_file"
    fi
done
```

**Provider fallback with custom order:**
```bash
#!/bin/bash
# Try fast providers first, then reliable ones
providers="[uguu,catbox,s3,dropbox]"
twat-fs upload "$1" --provider "$providers"
```

## Output Formats

### Standard Output

Default output shows only the URL:
```bash
$ twat-fs upload file.jpg
https://files.catbox.moe/abc123.jpg
```

### Verbose Output

With `-v` or `--verbose`:
```
[2024-01-15 14:30:22] INFO: Starting upload of file.jpg
[2024-01-15 14:30:22] INFO: File size: 2.5 MB
[2024-01-15 14:30:22] INFO: Using provider: catbox
[2024-01-15 14:30:22] INFO: Uploading...
[2024-01-15 14:30:23] INFO: Upload complete
[2024-01-15 14:30:23] INFO: Validating URL...
[2024-01-15 14:30:23] INFO: Success: https://files.catbox.moe/abc123.jpg
[2024-01-15 14:30:23] INFO: Total time: 1.2s
```

### Error Output

Errors are printed to stderr:
```bash
$ twat-fs upload missing.jpg
Error: File not found: missing.jpg
```

### Machine-Readable Output

For scripting, parse the URL from stdout:
```bash
url=$(twat-fs upload file.jpg 2>/dev/null)
if [ $? -eq 0 ]; then
    # Use $url
fi
```

## Performance Tips

### Provider Selection
- Use `--fragile` to fail fast when you know the provider should work
- Order providers by reliability and speed in fallback lists
- Use simple providers for small files, authenticated for large

### Optimization
- Pre-configure environment variables in shell profile
- Use provider-specific paths to organize uploads
- Monitor provider performance with `--online` tests

### Debugging
- Use `LOGURU_LEVEL=DEBUG` for detailed logs
- Test providers individually before using in scripts
- Check provider status pages for outages

## Common Patterns

### Development Workflow
```bash
# Quick share of build artifact
twat-fs upload dist/app.zip --provider catbox

# Upload to S3 with organized structure  
twat-fs upload dist/app-v1.2.3.zip \
    --provider s3 \
    --remote_path "releases/v1.2.3/"
```

### Backup Script
```bash
#!/bin/bash
# Daily backup to S3
backup_file="backup_$(date +%Y%m%d).tar.gz"
tar czf "$backup_file" /important/data
twat-fs upload "$backup_file" \
    --provider s3 \
    --remote_path "backups/daily/" \
    --unique
```

### CI/CD Integration
```yaml
# GitHub Actions example
- name: Upload artifacts
  run: |
    twat-fs upload build/output.zip \
      --provider s3 \
      --remote_path "ci/builds/${{ github.sha }}/"
```

## See Also

- [Basic Usage](basic-usage.md) - Usage guide with examples
- [Provider Details](providers.md) - Detailed provider information
- [API Reference](../development/api-reference.md) - Python API documentation