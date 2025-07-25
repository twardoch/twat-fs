---
this_file: src_docs/user-guide/providers.md
---

# Provider Details

This page provides detailed information about each upload provider supported by twat-fs.

## Provider Comparison

| Provider | Auth Required | Max Size | Retention | Anonymous | API Limits | Best For |
|----------|--------------|----------|-----------|-----------|------------|----------|
| catbox | No | 200MB | Permanent* | Yes | None | Quick shares |
| litterbox | No | 1GB | 1h-72h | Yes | None | Temporary files |
| www0x0 | No | 512MB | 365 days** | Yes | None | Dev/testing |
| uguu | No | 128MB | 48 hours | Yes | None | Small temp files |
| bashupload | No | 50GB | 3 days | Yes | None | Large temp files |
| filebin | No | Unlimited*** | 6 days | Yes | None | Collections |
| pixeldrain | No | 20GB | 120 days** | Yes | None | Media files |
| dropbox | Yes | Unlimited | Permanent | No | Rate limits | Personal storage |
| s3 | Yes | Unlimited | Permanent | No | Pay per use | Production |
| fal | Yes | Varies | Varies | No | Pay per use | AI/ML workflows |

\* Files may be deleted for inactivity or ToS violations  
\** Inactive files are deleted after this period  
\*** Reasonable use policy applies

## Simple Providers

### Catbox (catbox.moe)

**Overview:** Popular, reliable file host with good uptime and no registration required.

**Features:**
- 200MB file size limit
- Direct file links
- No expiration (with caveats)
- Supports most file types
- No JavaScript required

**Usage:**
```bash
twat-fs upload file.jpg --provider catbox
```

**Limitations:**
- No folder organization
- No access control
- Files deleted if inactive for extended periods
- Subject to DMCA takedowns

**Best Practices:**
- Ideal for sharing images and documents
- Good for permanent links in documentation
- Not suitable for sensitive data

### Litterbox (litter.catbox.moe)

**Overview:** Temporary version of Catbox for files that should expire.

**Features:**
- 1GB file size limit
- Configurable expiration (1h, 12h, 24h, 72h)
- Same infrastructure as Catbox
- No registration required

**Usage:**
```bash
# Default 1 hour expiration
twat-fs upload file.zip --provider litterbox

# In Python with custom expiration
from twat_fs import upload_file
from twat_fs.upload_providers import ExpirationTime

url = upload_file("file.zip", provider="litterbox", 
                  expiration=ExpirationTime.HOURS_24)
```

**Best For:**
- Sharing large files temporarily
- Sensitive data that should auto-delete
- Quick file transfers

### 0x0.st (www0x0)

**Overview:** Minimalist file host popular with developers.

**Features:**
- 512MB file size limit  
- 365 day retention for active files
- Command-line friendly
- Supports curl uploads
- No JavaScript or cookies

**Usage:**
```bash
twat-fs upload script.py --provider www0x0
```

**Limitations:**
- Files deleted after 365 days of no downloads
- No preview for most file types
- Minimal interface

**Best For:**
- Code snippets and scripts
- Command-line workflows
- Developer tools

### Uguu.se

**Overview:** Simple temporary file host with cute anime theme.

**Features:**
- 128MB file size limit
- 48 hour retention
- Clean interface
- Fast uploads
- No ads

**Usage:**
```bash
twat-fs upload document.pdf --provider uguu
```

**Best For:**
- Small temporary files
- Quick shares that don't need long retention
- When other providers are down

### Bashupload

**Overview:** Command-line focused host with large file support.

**Features:**
- 50GB file size limit
- 3 day retention
- Designed for terminal use
- Simple curl-compatible API
- Progress indicators

**Usage:**
```bash
twat-fs upload large_backup.tar.gz --provider bashupload
```

**Best For:**
- Large file transfers
- Server-to-server transfers
- Backup dumps

### Filebin

**Overview:** Pastebin-style file host with collections.

**Features:**
- No hard size limit
- 6 day retention
- File collections/bins
- Syntax highlighting for code
- Archive downloads

**Usage:**
```bash
twat-fs upload project.zip --provider filebin
```

**Best For:**
- Multiple related files
- Code sharing with highlighting
- Temporary project shares

### Pixeldrain

**Overview:** Feature-rich file host with good multimedia support.

**Features:**
- 20GB file size limit
- 120 days retention for free uploads
- Video/audio streaming
- Gallery view for images
- Download acceleration

**Usage:**
```bash
twat-fs upload video.mp4 --provider pixeldrain
```

**Best For:**
- Media files (video, audio, images)
- Large files that need preview
- Streaming content

## Authenticated Providers

### Dropbox

**Overview:** Popular cloud storage with robust API.

**Features:**
- No file size limit (account storage limit applies)
- Permanent storage
- Version history
- Shared folders
- Rich permissions

**Configuration:**
```bash
export DROPBOX_ACCESS_TOKEN="your_token_here"
```

**Usage:**
```bash
# Upload to root
twat-fs upload file.doc --provider dropbox

# Upload to specific folder
twat-fs upload file.doc --provider dropbox --remote_path "/Documents/Work/"
```

**Advanced Features:**
- OAuth2 token refresh
- Team folders (with business account)
- Paper documents
- File requests

**Best For:**
- Personal backups
- Team collaboration
- Document management

### AWS S3

**Overview:** Industry-standard object storage.

**Features:**
- Unlimited storage
- 5TB single file limit
- 99.999999999% durability
- Global CDN integration
- Fine-grained permissions

**Configuration:**
```bash
export AWS_S3_BUCKET="my-bucket"
export AWS_DEFAULT_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

**Usage:**
```bash
# Basic upload
twat-fs upload file.zip --provider s3

# With custom path
twat-fs upload file.zip --provider s3 --remote_path "backups/2024/"
```

**Advanced Features:**
- Storage classes (Standard, IA, Glacier)
- Lifecycle policies
- Cross-region replication
- Signed URLs
- Multipart uploads for large files

**Cost Considerations:**
- Storage: ~$0.023/GB/month (Standard)
- Transfer: ~$0.09/GB (out)
- Requests: ~$0.0004 per 1000 requests

**Best For:**
- Production applications
- Large-scale storage
- Global distribution
- Compliance requirements

### Fal.ai

**Overview:** Specialized storage for AI/ML workflows.

**Features:**
- Integrated with Fal.ai compute
- Optimized for model files
- Fast CDN
- Version control
- Collaboration features

**Configuration:**
```bash
export FAL_KEY="key_id:key_secret"
```

**Usage:**
```bash
twat-fs upload model.onnx --provider fal
```

**Best For:**
- Machine learning models
- Training datasets
- AI application assets
- Compute pipeline integration

## Provider Selection Guide

### For Temporary Sharing
1. **litterbox** - Large files, configurable expiration
2. **uguu** - Small files, 48h retention
3. **bashupload** - Very large files, 3 day retention

### For Permanent Storage
1. **s3** - Production use, high reliability
2. **dropbox** - Personal/team use, easy sharing
3. **catbox** - Anonymous permanent (with caveats)

### For Media Files
1. **pixeldrain** - Streaming, previews, galleries
2. **catbox** - Images and small videos
3. **s3** - Large media libraries

### For Development
1. **www0x0** - Code snippets, scripts
2. **filebin** - Multi-file projects
3. **catbox** - Quick binary shares

### For Large Files
1. **s3** - Unlimited, reliable
2. **dropbox** - User-friendly, good speeds
3. **bashupload** - Temporary, up to 50GB

## Performance Tips

### Speed Optimization
- Simple providers are generally faster for small files
- S3 with multipart upload is fastest for large files
- Dropbox has good global performance
- Use providers geographically close to you

### Reliability
- Set up fallback chains for critical uploads
- Monitor provider status pages
- Keep authentication tokens updated
- Test providers regularly with `--online`

### Cost Optimization
- Use temporary providers for short-term needs
- Consider S3 Glacier for archives
- Monitor S3 usage to avoid surprises
- Use Dropbox for frequently accessed files

## Security Considerations

### Anonymous Providers
- All uploads are public
- No access control available
- URLs are hard to guess but not private
- Consider encryption for sensitive data

### Authenticated Providers
- Use strong authentication tokens
- Rotate credentials regularly
- Set up proper IAM policies (S3)
- Enable 2FA where available
- Monitor access logs

### Data Privacy
- Read provider ToS carefully
- Consider data residency requirements
- Encrypt before uploading sensitive data
- Keep records of what's uploaded where

## Troubleshooting Providers

### Common Issues

**"Provider not available"**
- Check if provider module is installed
- Verify provider name spelling
- See if provider service is online

**"Upload failed"**
- Check file size limits
- Verify file type is allowed
- Test with smaller file
- Check provider status page

**"Authentication failed"**
- Verify credentials are set
- Check token expiration
- Ensure proper permissions
- Test with provider's official tools

### Provider-Specific Issues

**Catbox/Litterbox:**
- May reject certain file types
- Cloudflare challenges during high load
- Check https://catbox.moe/faq

**S3:**
- Bucket policy conflicts
- CORS issues for web access
- Region mismatch errors

**Dropbox:**
- Token expiration
- Rate limiting (too many requests)
- Storage quota exceeded

## Next Steps

- [CLI Reference](cli-reference.md) - Full command documentation
- [Troubleshooting](troubleshooting.md) - Solve common problems
- [API Reference](../development/api-reference.md) - Programmatic usage