---
this_file: src_docs/getting-started/configuration.md
---

# Configuration Guide

This guide explains how to configure twat-fs providers, especially those requiring authentication.

## Simple Providers (No Configuration Required)

These providers work out of the box without any configuration:

- **catbox** - catbox.moe (200MB limit)
- **litterbox** - litter.catbox.moe (1GB limit, temporary)
- **www0x0** - 0x0.st (512MB limit)
- **uguu** - uguu.se (128MB limit, temporary)
- **bashupload** - bashupload.com 
- **filebin** - filebin.net (temporary)
- **pixeldrain** - pixeldrain.com

You can start using these immediately:

```bash
twat-fs upload myfile.jpg --provider catbox
```

## Authenticated Providers

These providers require configuration before use:

### Dropbox Configuration

1. **Get an Access Token**
   - Go to [Dropbox App Console](https://www.dropbox.com/developers/apps)
   - Create a new app or use an existing one
   - Generate an access token

2. **Set Environment Variable**
   ```bash
   export DROPBOX_ACCESS_TOKEN="your_access_token_here"
   ```

3. **Advanced OAuth2 Setup (Optional)**
   
   If you need token refresh capabilities:
   ```bash
   export DROPBOX_REFRESH_TOKEN="your_refresh_token"
   export DROPBOX_APP_KEY="your_app_key"
   export DROPBOX_APP_SECRET="your_app_secret"
   ```

4. **Test Configuration**
   ```bash
   twat-fs upload_provider status dropbox --online
   ```

### AWS S3 Configuration

1. **Set Required Environment Variables**
   ```bash
   # Required
   export AWS_S3_BUCKET="your-bucket-name"
   export AWS_DEFAULT_REGION="us-east-1"  # or your preferred region
   ```

2. **Configure Authentication (Choose One Method)**

   **Option A: Access Keys**
   ```bash
   export AWS_ACCESS_KEY_ID="your_access_key_id"
   export AWS_SECRET_ACCESS_KEY="your_secret_access_key"
   ```

   **Option B: AWS CLI Configuration**
   ```bash
   aws configure
   # Follow the prompts to enter your credentials
   ```

   **Option C: IAM Roles (for EC2/Lambda)**
   - No configuration needed if running on AWS with proper IAM roles

3. **Optional: S3-Compatible Services**
   
   For MinIO, DigitalOcean Spaces, etc.:
   ```bash
   export AWS_ENDPOINT_URL="https://your-s3-compatible-endpoint.com"
   ```

4. **Test Configuration**
   ```bash
   twat-fs upload_provider status s3 --online
   ```

### Fal.ai Configuration

1. **Get API Credentials**
   - Sign up at [fal.ai](https://fal.ai)
   - Get your API key from the dashboard

2. **Set Environment Variable**
   ```bash
   export FAL_KEY="your_key_id:your_key_secret"
   ```

3. **Test Configuration**
   ```bash
   twat-fs upload_provider status fal --online
   ```

## Configuration Methods

### Environment Variables

The recommended way to configure providers is through environment variables.

**Temporary (current session only):**
```bash
export AWS_S3_BUCKET="my-bucket"
```

**Persistent (add to shell profile):**
```bash
# Add to ~/.bashrc, ~/.zshrc, or equivalent
echo 'export AWS_S3_BUCKET="my-bucket"' >> ~/.bashrc
source ~/.bashrc
```

**Windows Command Prompt:**
```cmd
set AWS_S3_BUCKET=my-bucket
```

**Windows PowerShell:**
```powershell
$env:AWS_S3_BUCKET = "my-bucket"
```

### Configuration Files

You can also create a `.env` file in your project directory:

```bash
# .env file
DROPBOX_ACCESS_TOKEN=your_token_here
AWS_S3_BUCKET=my-bucket
AWS_DEFAULT_REGION=us-east-1
```

Then load it before running twat-fs:

```bash
# Using python-dotenv
python -c "from dotenv import load_dotenv; load_dotenv()"
twat-fs upload myfile.jpg --provider s3

# Or source it directly (Linux/macOS)
export $(cat .env | xargs)
```

## Provider-Specific Settings

### S3 Advanced Configuration

**Custom Object Naming:**
```bash
# Upload with custom prefix
twat-fs upload file.jpg --provider s3 --remote_path "images/2024/"

# Result: s3://bucket/images/2024/file.jpg
```

**Access Control:**
```python
# In Python code, you can pass additional S3 parameters
from twat_fs import upload_file

# This requires modifying the provider to accept these parameters
url = upload_file("file.jpg", provider="s3", options={
    "ACL": "public-read",  # Make publicly accessible
    "StorageClass": "GLACIER"  # Use cheaper storage
})
```

### Dropbox Path Configuration

```bash
# Upload to specific Dropbox folder
twat-fs upload document.pdf --provider dropbox --remote_path "/Documents/Work/"
```

## Security Best Practices

### 1. Never Hardcode Credentials

❌ **Bad:**
```python
token = "sk-1234567890abcdef"  # Never do this!
```

✅ **Good:**
```python
import os
token = os.environ.get("DROPBOX_ACCESS_TOKEN")
if not token:
    raise ValueError("DROPBOX_ACCESS_TOKEN not set")
```

### 2. Use Secrets Management

For production environments, consider using:

- **AWS Secrets Manager** for AWS credentials
- **HashiCorp Vault** for multi-cloud secrets
- **GitHub Secrets** for CI/CD
- **Docker Secrets** for containerized apps

### 3. Limit Permissions

- Create dedicated service accounts with minimal permissions
- For S3, use bucket policies to restrict access
- For Dropbox, use app folders instead of full access

### 4. Rotate Credentials Regularly

Set up a rotation schedule:
```bash
# Example: Check credential age
aws iam list-access-keys --user-name upload-user
```

## Troubleshooting Configuration

### Check Provider Status

Always verify your configuration:

```bash
# Check if provider is configured
twat-fs upload_provider status s3

# Test with actual upload
twat-fs upload_provider status s3 --online
```

### Common Issues

**"Provider not configured"**
- Check environment variables are set
- Verify variable names are correct (case-sensitive)
- Ensure no extra spaces in values

**"Authentication failed"**
- Verify credentials are valid
- Check token hasn't expired
- Ensure proper permissions are granted

**"Bucket not found" (S3)**
- Verify bucket name is correct
- Check region is set correctly
- Ensure bucket exists and is accessible

### Debug Mode

Enable debug logging to see detailed configuration info:

```bash
# Set log level
export LOGURU_LEVEL=DEBUG
twat-fs upload test.txt --provider s3
```

## Configuration Examples

### Multi-Provider Setup

Configure multiple providers for fallback:

```bash
# ~/.bashrc or ~/.zshrc
export DROPBOX_ACCESS_TOKEN="dropbox_token_here"
export AWS_S3_BUCKET="my-s3-bucket"
export AWS_DEFAULT_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="aws_key_here"
export AWS_SECRET_ACCESS_KEY="aws_secret_here"
export FAL_KEY="fal_key_here"
```

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.10
WORKDIR /app

# Install twat-fs
RUN pip install twat-fs[all]

# Set provider configs
ENV DROPBOX_ACCESS_TOKEN=${DROPBOX_TOKEN}
ENV AWS_S3_BUCKET=${S3_BUCKET}
ENV AWS_DEFAULT_REGION=us-east-1

# Copy credentials at runtime
COPY .env /app/.env
RUN export $(cat .env | xargs)
```

### CI/CD Configuration

**GitHub Actions:**
```yaml
- name: Upload artifacts
  env:
    AWS_S3_BUCKET: ${{ secrets.S3_BUCKET }}
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_KEY }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET }}
  run: |
    twat-fs upload build/output.zip --provider s3
```

## Next Steps

- [Basic Usage](../user-guide/basic-usage.md) - Learn upload commands
- [Provider Details](../user-guide/providers.md) - Provider-specific features
- [Troubleshooting](../user-guide/troubleshooting.md) - Solve common issues