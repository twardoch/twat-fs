---
this_file: TODO.md
---

# TODO

Tip: Periodically run `./cleanup.py status` to see results of lints and tests.

## Phase 1

- [ ] Implement a factory pattern for provider instantiation
  - Create a provider factory that simplifies the creation of providers
  - Reduce code duplication in `get_provider()` methods
  - Standardize error handling during initialization

## Phase 2

- [ ] Standardize async/sync conversion patterns
  - Create helper functions for common async patterns
  - Ensure consistent type hints for async operations
  - Standardize conversion logic across providers

## Phase 3

- [ ] Write unit tests for utils.py functions
  - Test each utility function thoroughly
  - Cover edge cases and error conditions
  - Ensure backward compatibility

## Medium Priority

- [ ] Refine HTTP response handling across providers
  - Ensure all providers use `handle_http_response()` consistently
  - Standardize handling of various HTTP status codes
  - Improve handling of rate limits (429) and other non-200 responses

- [ ] Create provider base classes to reduce inheritance boilerplate
  - Implement a base class for async-capable providers
  - Implement a base class for providers requiring credentials
  - Reduce duplicate code through inheritance

- [ ] Document best practices for creating new providers
  - Create clear documentation for adding new providers
  - Show how to leverage the shared utilities
  - Provide examples of following established patterns

- [ ] Add comprehensive type annotations for async operations
  - Ensure consistent type handling in async/await conversions
  - Improve type hints for async decorators
  - Add proper typing for async context managers

## New Providers

### Simple File Hosting Providers

- [ ] Implement Transfer.sh provider
  - Simple HTTP POST API
  - No authentication required
  - Similar to existing simple providers
  - Good for temporary file sharing

- [ ] Implement AnonFiles provider
  - Simple API for anonymous file uploads
  - Returns direct download links
  - No authentication required
  - Similar implementation to existing simple providers

### Cloud Storage Providers

- [ ] Implement Google Drive provider
  - Requires OAuth2 authentication
  - Leverage existing async/sync patterns
  - Add support for folder organization
  - Dependencies: google-api-python-client, google-auth

- [ ] Implement Microsoft OneDrive provider
  - Requires OAuth2 authentication
  - Similar to Dropbox implementation pattern
  - Dependencies: Office365-REST-Python-Client or Microsoft Graph SDK

- [ ] Implement pCloud provider
  - API key based authentication
  - Good for privacy-focused users
  - Dependencies: pcloud-sdk-python

### S3-Compatible Storage

- [ ] Implement Backblaze B2 provider
  - S3-compatible API
  - Can leverage existing S3 provider with custom endpoint
  - Cost-effective storage solution
  - Dependencies: boto3 (already used for S3)

- [ ] Implement DigitalOcean Spaces provider
  - S3-compatible API
  - Can leverage existing S3 provider with custom endpoint
  - Dependencies: boto3 (already used for S3)

### Media and Specialized Providers

- [ ] Implement Imgur provider
  - Specialized for image uploads
  - API key based authentication
  - Add image-specific metadata handling
  - Dependencies: requests

- [ ] Implement Cloudinary provider
  - Media transformation capabilities
  - API key based authentication
  - Support for image/video optimization
  - Dependencies: cloudinary or requests

### Version Control Platforms

- [ ] Implement GitHub Gist provider
  - Good for text file sharing with syntax highlighting
  - OAuth or token-based authentication
  - Implement file size and type constraints
  - Dependencies: PyGithub or requests

- [ ] Implement GitLab Snippet provider
  - Similar to GitHub Gist
  - Support for self-hosted GitLab instances
  - Token-based authentication
  - Dependencies: python-gitlab or requests

### Enterprise and Specialized Services

- [ ] Implement Azure Blob Storage provider
  - Microsoft's object storage solution
  - Similar pattern to S3 provider
  - Dependencies: azure-storage-blob

- [ ] Implement Box provider
  - Enterprise file sharing and collaboration
  - OAuth authentication
  - Dependencies: boxsdk

- [ ] Implement WeTransfer provider
  - Popular service for large file transfers
  - API key based authentication
  - Support for expiring links
  - Dependencies: requests

### Decentralized Storage Options

- [ ] Implement IPFS provider via Pinata or Infura
  - Distributed file system
  - Pin files to IPFS network
  - API key based authentication
  - Dependencies: ipfshttpclient or requests

## Implementation Strategy

- [ ] Update provider preference list in `__init__.py` to include new providers
- [ ] Add environment variable documentation for each new provider
- [ ] Create integration tests for each new provider
- [ ] Update documentation with new provider capabilities and requirements

## Completed Tasks

- [x] Create utils.py to centralize common functionality for upload providers
  
  A `utils.py` file has been created in the `upload_providers` folder with several helper functions:
  - `create_provider_help` for standardizing provider help dictionaries
  - `safe_file_handle` for file operations
  - `validate_file` for file validation
  - `handle_http_response` for HTTP response handling
  - `get_env_credentials` for credential management
  - `create_provider_instance` for provider initialization
  - `standard_upload_wrapper` for consistent upload handling
  - `log_upload_attempt` for consistent logging

- [x] Refactor provider modules to use utils.py consistently
  
  All providers have been refactored:
  - pixeldrain.py, bashupload.py, catbox.py, filebin.py
  - uguu.py, www0x0.py, dropbox.py, s3.py
  - fal.py, litterbox.py

- [x] Create provider templates for standardized implementation
  
  Created two template files in the `templates` directory:
  - `simple_provider_template.py` for providers without authentication
  - `authenticated_provider_template.py` for providers requiring credentials