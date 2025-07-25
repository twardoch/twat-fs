---
this_file: src_docs/getting-started/quickstart.md
---

# Quick Start Guide

This guide will help you get started with twat-fs in just a few minutes.

## Your First Upload

The simplest way to upload a file is to use the default provider:

```bash
twat-fs upload myfile.jpg
```

This will:
1. Upload your file to catbox.moe (the default provider)
2. Return a URL where your file can be accessed
3. The URL will be printed to the console

## Basic Usage Examples

### Upload to a Specific Provider

```bash
# Upload to Litterbox (temporary storage)
twat-fs upload myfile.pdf --provider litterbox

# Upload to 0x0.st
twat-fs upload myfile.txt --provider www0x0

# Upload to AWS S3 (requires configuration)
twat-fs upload myfile.zip --provider s3
```

### Upload with Options

```bash
# Add timestamp to filename for uniqueness
twat-fs upload myfile.jpg --unique

# Force overwrite if file exists (provider-dependent)
twat-fs upload myfile.doc --force

# Specify a custom remote path (provider-dependent)
twat-fs upload myfile.pdf --remote_path "documents/2024/"
```

### Provider Fallback

twat-fs automatically falls back to alternative providers if one fails:

```bash
# Try S3 first, fall back to Dropbox, then catbox
twat-fs upload myfile.jpg --provider "[s3,dropbox,catbox]"

# Disable fallback (fail immediately if provider fails)
twat-fs upload myfile.jpg --provider s3 --fragile
```

## Checking Provider Status

Before uploading, you can check which providers are available:

```bash
# List all available providers
twat-fs upload_provider list

# Check status of a specific provider
twat-fs upload_provider status s3

# Check all providers with online test
twat-fs upload_provider status --online
```

## Python API Usage

You can also use twat-fs programmatically in your Python code:

```python
from twat_fs import upload_file

# Simple upload
url = upload_file("myfile.jpg")
print(f"File uploaded to: {url}")

# Upload with specific provider
url = upload_file("myfile.pdf", provider="s3")

# Upload with options
from twat_fs.upload import UploadOptions

options = UploadOptions(
    unique=True,      # Add timestamp to filename
    fragile=False,    # Allow fallback to other providers
    remote_path="uploads/2024/"  # Custom path
)
url = upload_file("myfile.doc", provider="dropbox", options=options)

# Handle errors
from twat_fs.upload_providers.core import RetryableError, NonRetryableError

try:
    url = upload_file("myfile.zip", provider="s3")
except FileNotFoundError:
    print("File not found")
except RetryableError as e:
    print(f"Temporary error: {e}")
except NonRetryableError as e:
    print(f"Permanent error: {e}")
```

## Common Use Cases

### Temporary File Sharing

Use providers with expiration for temporary sharing:

```bash
# Upload to Litterbox (1 hour expiration)
twat-fs upload sensitive.pdf --provider litterbox

# Upload to Uguu (48 hour expiration)  
twat-fs upload temp_file.zip --provider uguu
```

### Permanent Storage

Use authenticated providers for permanent storage:

```bash
# Upload to S3 (permanent, requires AWS credentials)
twat-fs upload important.doc --provider s3

# Upload to Dropbox (permanent, requires access token)
twat-fs upload backup.zip --provider dropbox
```

### Anonymous Uploads

Use simple providers for anonymous uploads:

```bash
# Upload to catbox (anonymous, 200MB limit)
twat-fs upload image.png --provider catbox

# Upload to 0x0.st (anonymous, 512MB limit)
twat-fs upload video.mp4 --provider www0x0
```

### Batch Uploads

Upload multiple files using shell features:

```bash
# Upload all JPG files in current directory
for file in *.jpg; do
    twat-fs upload "$file"
done

# Upload with parallel processing
find . -name "*.pdf" -print0 | xargs -0 -P 4 -I {} twat-fs upload {}
```

## Understanding Output

When you upload a file, twat-fs provides information about the upload:

```bash
$ twat-fs upload photo.jpg
Uploading photo.jpg to catbox...
Successfully uploaded to: https://files.catbox.moe/abc123.jpg
Upload completed in 2.3s
```

With verbose output:

```bash
$ twat-fs upload photo.jpg -v
Starting upload of photo.jpg (2.5 MB)
Provider: catbox
Reading file... done (0.1s)
Uploading... done (1.8s)
Validating URL... done (0.4s)
Successfully uploaded to: https://files.catbox.moe/abc123.jpg
Total time: 2.3s
```

## Tips and Best Practices

1. **Provider Selection**
   - Use simple providers (catbox, 0x0) for quick, anonymous uploads
   - Use authenticated providers (S3, Dropbox) for important files
   - Use temporary providers (litterbox, uguu) for sensitive data

2. **File Size Limits**
   - catbox: 200MB
   - 0x0.st: 512MB
   - litterbox: 1GB
   - S3/Dropbox: No practical limit

3. **Performance**
   - Simple providers are generally faster
   - Authenticated providers offer more features but may be slower
   - Use `--fragile` to fail fast if you don't want fallback delays

4. **Security**
   - Anonymous providers don't require authentication but offer no access control
   - Files uploaded to simple providers are publicly accessible
   - Use authenticated providers for sensitive data

## Next Steps

- [Configuration Guide](configuration.md) - Set up authenticated providers
- [Provider Details](../user-guide/providers.md) - Learn about each provider
- [CLI Reference](../user-guide/cli-reference.md) - Full command documentation
- [Troubleshooting](../user-guide/troubleshooting.md) - Common issues and solutions