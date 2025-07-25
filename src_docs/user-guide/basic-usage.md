---
this_file: src_docs/user-guide/basic-usage.md
---

# Basic Usage Guide

This guide covers the fundamental operations you can perform with twat-fs.

## Command Structure

The basic command structure for twat-fs is:

```bash
twat-fs <command> [arguments] [options]
```

Main commands:
- `upload` - Upload a file
- `upload_provider` - Manage upload providers
- `version` - Show version information

## Uploading Files

### Simple Upload

The most basic upload command:

```bash
twat-fs upload <file_path>
```

Example:
```bash
twat-fs upload photo.jpg
# Output: https://files.catbox.moe/abc123.jpg
```

### Specifying a Provider

Use the `--provider` flag to choose a specific upload service:

```bash
twat-fs upload <file_path> --provider <provider_name>
```

Examples:
```bash
# Upload to Litterbox (temporary storage)
twat-fs upload document.pdf --provider litterbox

# Upload to AWS S3
twat-fs upload backup.zip --provider s3

# Upload to Dropbox
twat-fs upload photo.jpg --provider dropbox
```

### Multiple Providers (Fallback)

Specify multiple providers for automatic fallback:

```bash
twat-fs upload <file_path> --provider "[provider1,provider2,provider3]"
```

Example:
```bash
# Try S3 first, then Dropbox, then catbox
twat-fs upload important.doc --provider "[s3,dropbox,catbox]"
```

The system will:
1. Try to upload to S3
2. If S3 fails, try Dropbox
3. If Dropbox fails, try catbox
4. Return the URL from the first successful upload

### Upload Options

#### Unique Filenames

Add a timestamp to ensure unique filenames:

```bash
twat-fs upload photo.jpg --unique
# Uploads as: photo_20240115_143022.jpg
```

#### Force Overwrite

Force overwrite existing files (provider-dependent):

```bash
twat-fs upload document.pdf --force
```

#### Custom Remote Path

Specify where to store the file (provider-dependent):

```bash
twat-fs upload report.pdf --remote_path "documents/2024/january/"
```

#### Disable Fallback

Use `--fragile` to fail immediately without trying other providers:

```bash
twat-fs upload critical.zip --provider s3 --fragile
```

## Provider Management

### List Available Providers

See which providers are ready to use:

```bash
twat-fs upload_provider list
```

Output:
```
Available providers:
  ✓ catbox      - Simple file host (200MB limit)
  ✓ litterbox   - Temporary storage (1GB, expires)
  ✓ www0x0      - Anonymous uploads (512MB limit)
  ✓ s3          - AWS S3 (configured)
  ✗ dropbox     - Requires configuration
```

### Check Provider Status

Check if a specific provider is configured:

```bash
twat-fs upload_provider status <provider_name>
```

Example:
```bash
twat-fs upload_provider status s3
# Output: Provider 's3' is ready for use
```

### Test Provider

Perform an online test by uploading a small test file:

```bash
twat-fs upload_provider status <provider_name> --online
```

Example:
```bash
twat-fs upload_provider status dropbox --online
# Output: Provider 'dropbox' test successful (upload: 1.2s, download: 0.5s)
```

### Check All Providers

Check status of all providers:

```bash
# Basic status check
twat-fs upload_provider status

# With online testing
twat-fs upload_provider status --online
```

## Advanced Usage Patterns

### Batch Uploads

Upload multiple files using shell scripting:

```bash
# Upload all images in a directory
for file in *.jpg *.png; do
    echo "Uploading $file..."
    twat-fs upload "$file"
done

# Upload with parallel processing
find . -type f -name "*.pdf" | parallel -j 4 twat-fs upload {}

# Save URLs to a file
for file in *.doc; do
    url=$(twat-fs upload "$file")
    echo "$file: $url" >> uploads.txt
done
```

### Conditional Uploads

Upload based on file properties:

```bash
# Upload only files larger than 10MB to S3
for file in *; do
    if [ $(stat -f%z "$file") -gt 10485760 ]; then
        twat-fs upload "$file" --provider s3
    else
        twat-fs upload "$file" --provider catbox
    fi
done
```

### Upload with Metadata

Store upload information:

```bash
# Create upload log with timestamps
file="document.pdf"
timestamp=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
url=$(twat-fs upload "$file" --provider s3)
echo "[$timestamp] $file -> $url" >> upload_log.txt
```

### Error Handling

Handle upload failures gracefully:

```bash
#!/bin/bash
file="important.zip"

# Try upload with error handling
if url=$(twat-fs upload "$file" --provider s3 2>/dev/null); then
    echo "Success: $url"
else
    echo "Failed to upload to S3, trying backup provider..."
    if url=$(twat-fs upload "$file" --provider dropbox 2>/dev/null); then
        echo "Success (backup): $url"
    else
        echo "All uploads failed!"
        exit 1
    fi
fi
```

## Command Output

### Standard Output

By default, twat-fs outputs only the URL:

```bash
$ twat-fs upload photo.jpg
https://files.catbox.moe/abc123.jpg
```

### Verbose Output

Use `-v` or `--verbose` for detailed information:

```bash
$ twat-fs upload photo.jpg -v
[2024-01-15 14:30:22] INFO: Starting upload of photo.jpg
[2024-01-15 14:30:22] INFO: File size: 2.5 MB
[2024-01-15 14:30:22] INFO: Using provider: catbox
[2024-01-15 14:30:23] INFO: Upload successful
[2024-01-15 14:30:23] INFO: URL: https://files.catbox.moe/abc123.jpg
[2024-01-15 14:30:23] INFO: Total time: 1.2s
```

### Quiet Mode

Suppress all output except errors (useful for scripts):

```bash
url=$(twat-fs upload file.pdf 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "Uploaded to: $url"
fi
```

## Exit Codes

twat-fs uses standard exit codes:

- `0` - Success
- `1` - General error
- `2` - File not found
- `3` - Provider not configured
- `4` - Upload failed
- `5` - Network error

Example usage:

```bash
twat-fs upload file.pdf
case $? in
    0) echo "Upload successful" ;;
    2) echo "File not found" ;;
    3) echo "Provider not configured" ;;
    4) echo "Upload failed" ;;
    *) echo "Unknown error" ;;
esac
```

## Environment Variables

Control twat-fs behavior with environment variables:

```bash
# Set default provider
export TWAT_FS_DEFAULT_PROVIDER=s3

# Enable debug logging
export LOGURU_LEVEL=DEBUG

# Set custom timeout (seconds)
export TWAT_FS_TIMEOUT=120
```

## Tips and Tricks

### 1. Aliases for Common Operations

Add to your shell profile:

```bash
# Quick upload to catbox
alias qup='twat-fs upload'

# Upload to S3 with timestamp
alias s3up='twat-fs upload --provider s3 --unique'

# Upload for temporary sharing
alias tmpup='twat-fs upload --provider litterbox'
```

### 2. Integration with Other Tools

```bash
# Upload screenshot
gnome-screenshot -f /tmp/screenshot.png && twat-fs upload /tmp/screenshot.png

# Upload command output
echo "System info:" > /tmp/info.txt
uname -a >> /tmp/info.txt
twat-fs upload /tmp/info.txt --provider catbox

# Upload compressed directory
tar czf /tmp/backup.tar.gz ~/Documents && twat-fs upload /tmp/backup.tar.gz --provider s3
```

### 3. URL Shortening

Combine with URL shorteners:

```bash
# Upload and shorten URL
url=$(twat-fs upload large_file.zip)
short_url=$(curl -s "https://is.gd/create.php?format=simple&url=$url")
echo "Short URL: $short_url"
```

## Next Steps

- [Provider Details](providers.md) - Learn about each provider's features
- [CLI Reference](cli-reference.md) - Complete command documentation
- [Troubleshooting](troubleshooting.md) - Solve common problems