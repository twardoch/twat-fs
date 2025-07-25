---
this_file: src_docs/user-guide/troubleshooting.md
---

# Troubleshooting Guide

This guide helps you resolve common issues with twat-fs.

## Common Issues

### Installation Issues

#### "Command not found"

**Problem:** After installation, `twat-fs` command is not recognized.

**Solutions:**

1. **Check if twat-fs is in PATH:**
   ```bash
   which twat-fs
   # or
   where twat-fs  # Windows
   ```

2. **Add to PATH (Binary installation):**
   ```bash
   # Linux/macOS
   export PATH="$PATH:/path/to/twat-fs"
   echo 'export PATH="$PATH:/path/to/twat-fs"' >> ~/.bashrc
   
   # Windows
   # Add the directory to PATH in System Properties
   ```

3. **Use full path:**
   ```bash
   /usr/local/bin/twat-fs upload file.jpg
   ```

4. **Python package installation:**
   ```bash
   # Make sure you're in the right environment
   which python
   python -m twat_fs upload file.jpg
   ```

#### "Permission denied"

**Problem:** Cannot execute twat-fs binary.

**Solution:**
```bash
chmod +x twat-fs
# or
chmod 755 twat-fs
```

#### "Python version error"

**Problem:** "Python 3.10+ required" error.

**Solutions:**

1. **Check Python version:**
   ```bash
   python --version
   ```

2. **Use binary version instead:**
   - Download pre-built binary which includes Python

3. **Install newer Python:**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3.10
   
   # macOS with Homebrew
   brew install python@3.10
   ```

### Upload Errors

#### "File not found"

**Problem:** twat-fs cannot find the file to upload.

**Solutions:**

1. **Check file exists:**
   ```bash
   ls -la myfile.txt
   ```

2. **Use absolute path:**
   ```bash
   twat-fs upload /home/user/documents/myfile.txt
   ```

3. **Check current directory:**
   ```bash
   pwd
   ls
   ```

4. **Escape spaces in filename:**
   ```bash
   twat-fs upload "my file with spaces.txt"
   # or
   twat-fs upload my\ file\ with\ spaces.txt
   ```

#### "Provider not configured"

**Problem:** Authenticated provider requires configuration.

**Solutions:**

1. **Check environment variables:**
   ```bash
   # S3
   echo $AWS_S3_BUCKET
   echo $AWS_ACCESS_KEY_ID
   
   # Dropbox
   echo $DROPBOX_ACCESS_TOKEN
   ```

2. **Set missing variables:**
   ```bash
   export AWS_S3_BUCKET="my-bucket"
   export AWS_DEFAULT_REGION="us-east-1"
   ```

3. **Verify provider status:**
   ```bash
   twat-fs upload_provider status s3
   ```

#### "Upload failed"

**Problem:** Upload starts but fails to complete.

**Solutions:**

1. **Check file size limits:**
   - catbox: 200MB
   - uguu: 128MB
   - 0x0.st: 512MB

2. **Try different provider:**
   ```bash
   twat-fs upload largefile.zip --provider bashupload
   ```

3. **Check network connection:**
   ```bash
   ping 8.8.8.8
   curl https://catbox.moe
   ```

4. **Enable debug logging:**
   ```bash
   export LOGURU_LEVEL=DEBUG
   twat-fs upload file.jpg
   ```

### Provider-Specific Issues

#### S3 Issues

**"Access Denied"**

Check IAM permissions:
```bash
aws s3 ls s3://your-bucket/
aws s3 cp test.txt s3://your-bucket/
```

Required S3 permissions:
- `s3:PutObject`
- `s3:GetObject` (for validation)
- `s3:ListBucket` (optional)

**"Bucket not found"**

1. Verify bucket exists:
   ```bash
   aws s3 ls | grep your-bucket
   ```

2. Check region:
   ```bash
   echo $AWS_DEFAULT_REGION
   # Should match bucket region
   ```

**"Invalid credentials"**

1. Test AWS credentials:
   ```bash
   aws sts get-caller-identity
   ```

2. Refresh credentials:
   ```bash
   aws configure
   ```

#### Dropbox Issues

**"Invalid access token"**

1. Regenerate token:
   - Go to [Dropbox App Console](https://www.dropbox.com/developers/apps)
   - Generate new access token

2. Check token format:
   ```bash
   # Should start with 'sl.'
   echo $DROPBOX_ACCESS_TOKEN | head -c 3
   ```

**"Insufficient space"**

Check Dropbox storage:
```python
import dropbox
dbx = dropbox.Dropbox(access_token)
usage = dbx.users_get_space_usage()
print(f"Used: {usage.used / 1e9:.2f} GB")
```

#### Simple Provider Issues

**"Cloudflare challenge"**

Some providers use Cloudflare protection.

Solutions:
1. Wait and retry later
2. Use different provider
3. Try from different network

**"File type not allowed"**

Some providers block certain extensions.

Solutions:
1. Rename file with allowed extension
2. Compress file to .zip
3. Use different provider

### Network Issues

#### SSL Certificate Errors

**Problem:** "SSL: CERTIFICATE_VERIFY_FAILED"

**Solutions:**

1. **Update certificates:**
   ```bash
   # macOS
   pip install --upgrade certifi
   
   # Linux
   sudo apt-get update && sudo apt-get install ca-certificates
   
   # Python
   python -m pip install --upgrade certifi
   ```

2. **Set certificate bundle:**
   ```bash
   export SSL_CERT_FILE=$(python -m certifi)
   export REQUESTS_CA_BUNDLE=$(python -m certifi)
   ```

3. **Disable verification (NOT RECOMMENDED):**
   ```bash
   export PYTHONHTTPSVERIFY=0
   ```

#### Timeout Errors

**Problem:** "Upload timed out"

**Solutions:**

1. **Increase timeout:**
   ```bash
   export TWAT_FS_TIMEOUT=600  # 10 minutes
   ```

2. **Use smaller files:**
   ```bash
   # Split large file
   split -b 100M largefile.zip part_
   
   # Upload parts
   for part in part_*; do
       twat-fs upload "$part"
   done
   ```

3. **Try different provider:**
   - Simple providers are often faster
   - S3 handles large files better

#### Proxy Issues

**Problem:** Behind corporate proxy

**Solutions:**

1. **Set proxy environment:**
   ```bash
   export HTTP_PROXY=http://proxy.company.com:8080
   export HTTPS_PROXY=http://proxy.company.com:8080
   export NO_PROXY=localhost,127.0.0.1
   ```

2. **Python requests proxy:**
   ```bash
   export REQUESTS_PROXY=http://proxy.company.com:8080
   ```

### Performance Issues

#### Slow Uploads

**Diagnosis:**
```bash
# Test network speed
curl -o /dev/null http://speedtest.tele2.net/100MB.zip

# Test provider with small file
time twat-fs upload small.txt --provider catbox
```

**Solutions:**

1. **Use closer provider:**
   - Check provider locations
   - Use CDN-enabled providers (S3, Dropbox)

2. **Compress files:**
   ```bash
   gzip large.txt
   twat-fs upload large.txt.gz
   ```

3. **Parallel uploads:**
   ```bash
   # Upload directory in parallel
   find . -type f | parallel -j 4 twat-fs upload {}
   ```

### Debugging Techniques

#### Enable Debug Logging

```bash
export LOGURU_LEVEL=DEBUG
twat-fs upload test.txt 2>&1 | tee debug.log
```

#### Test with curl

Test provider directly:
```bash
# Catbox
curl -F "reqtype=fileupload" -F "fileToUpload=@test.txt" https://catbox.moe/user/api.php

# 0x0.st
curl -F "file=@test.txt" https://0x0.st
```

#### Check provider status

Many providers have status pages:
- https://catbox.moe (check homepage)
- https://0x0.st (check homepage)
- AWS: https://status.aws.amazon.com/

#### Python debugging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from twat_fs import upload_file
try:
    url = upload_file("test.txt", provider="s3")
except Exception as e:
    import traceback
    traceback.print_exc()
```

## Getting Help

### Diagnostic Information

When reporting issues, include:

1. **Version information:**
   ```bash
   twat-fs version
   python --version
   uname -a  # or systeminfo on Windows
   ```

2. **Error messages:**
   ```bash
   twat-fs upload test.txt 2>&1 | tee error.log
   ```

3. **Environment:**
   ```bash
   env | grep -E "(AWS|DROPBOX|FAL|PROXY)"
   ```

4. **Debug log:**
   ```bash
   export LOGURU_LEVEL=DEBUG
   twat-fs upload test.txt 2>&1 > debug.log
   ```

### Support Channels

1. **GitHub Issues:**
   - https://github.com/twardoch/twat-fs/issues
   - Search existing issues first
   - Use issue templates

2. **Documentation:**
   - Check this guide first
   - Read provider-specific docs
   - Review CLI reference

3. **Community:**
   - Stack Overflow tag: `twat-fs`
   - Discord/Slack (if available)

### Quick Fixes Checklist

- [ ] File exists and is readable
- [ ] Provider is configured (env vars set)
- [ ] Network connection works
- [ ] File size within provider limits
- [ ] Latest version installed
- [ ] Tried different provider
- [ ] Checked provider status page
- [ ] Enabled debug logging
- [ ] Tested with small file
- [ ] Verified credentials work

## See Also

- [Installation Guide](../getting-started/installation.md) - Proper installation steps
- [Configuration Guide](../getting-started/configuration.md) - Provider setup
- [Provider Details](providers.md) - Provider-specific information
- [CLI Reference](cli-reference.md) - Command options