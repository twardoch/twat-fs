---
this_file: LOG.md
---

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- New error handling system with RetryableError and NonRetryableError
- Intelligent provider fallback with exponential backoff
- URL validation for all uploaded files
- Completed implementation of all simple upload providers:
  - catbox.moe for permanent uploads (new default)
  - litterbox.catbox.moe for temporary uploads
  - termbin.com for text uploads
  - 0x0.st for general file uploads
  - uguu.se for temporary file uploads
  - bashupload.com for general file uploads
  - filebin.net for temporary uploads (6-day expiration)
  - pixeldrain.com for general file uploads
- Added comprehensive error handling for all providers
- Added type hints and docstrings throughout the codebase
- Added provider fallback mechanism for failed uploads
- Added test suite with 48 passing tests covering core functionality

### Fixed

- Fixed FAL provider implementation to properly handle ignored parameters
- Fixed S3 provider to handle all upload parameters correctly
- Fixed provider parameter handling in _try_provider function
- Fixed various type annotation issues
- Fixed provider fallback to properly handle temporary vs permanent failures
- Fixed URL validation to ensure all returned URLs are accessible

### Changed

- Improved provider architecture with better error handling
- Enhanced provider protocol implementation
- Updated documentation with new provider information
- Standardized error handling across all providers
- Reorganized TODO.md to prioritize code quality and type system improvements
- Changed default provider to catbox.moe for better reliability
- Improved provider fallback mechanism with exponential backoff
- Enhanced error messages with provider context
- Removed Dropbox, S3, and Pixeldrain providers from provider preference, focusing on simpler providers that do not require authentication

### Known Issues

- 28 code quality issues identified by ruff:
  - Module level imports not at top of file
  - Boolean-typed positional arguments need refactoring
  - Complex functions need simplification
  - Unused method arguments in providers
- 75 type checking issues identified by mypy:
  - Missing return type annotations
  - Missing type annotations in test functions
  - Incompatible return value types
  - Missing library stubs for dependencies

## [1.7.9] - 2025-02-15

### Added

- S3 advanced testing capabilities
- Integration tests for all providers
- New CLI interface with improved usability

### Changed

- Improved upload provider architecture
- Enhanced error handling in S3 provider
- Updated documentation

## [1.7.8] - 2025-02-15

### Added

- S3 upload provider implementation
- Basic S3 testing framework

### Changed

- Refactored upload provider initialization
- Updated provider documentation

## [1.7.5] - 2025-02-15

### Added

- Upload provider base infrastructure
- Provider-specific configuration handling

### Changed

- Restructured package architecture
- Improved test coverage

## [1.0.9] - 2025-02-15

### Added

- Support for Dropbox as upload provider
- FAL.ai integration improvements

### Fixed

- Various bug fixes in upload functionality
- Provider authentication issues

## [1.0.8] - 2025-02-15

### Added

- Initial FAL.ai provider support
- Basic upload functionality

### Changed

- Improved error handling
- Enhanced documentation

## [1.0.7] - 2025-02-14

### Added

- Basic upload functionality
- Initial provider framework

### Changed

- Package structure improvements
- Documentation updates

## [1.0.6] - 2025-02-14

### Added

- Initial test suite
- Basic CLI functionality

## [1.0.5] - 2025-02-14

### Added

- Project structure setup
- Basic package configuration

## [1.0.0] - 2025-02-14

### Added

- Initial release
- Basic project setup
- Core functionality structure

# Development Log

## 2024-02-17

### Integration of Simple Upload Providers

Added support for simple file upload services that don't require authentication:

1. Created new base infrastructure:
   - `SimpleProviderBase` class in `upload_providers/simple.py`
   - Async support with proper error handling
   - Consistent `UploadResult` type for all providers
   - File validation utilities

2. Implemented providers:
   - Termbin.com (text-only uploads via netcat)
   - 0x0.st (general file uploads via HTTP)
   - Uguu.se (temporary file uploads)
   - Bashupload.com (general file uploads)

3. Completed migration:
   - Moved all providers from `uploaders/` to `upload_providers/`
   - Enhanced error handling and logging
   - Added proper type hints and docstrings
   - Removed old `uploaders` directory

4. Next steps:
   - Add comprehensive tests
   - Implement rate limiting and file validation
   - Update documentation
   - Add provider fallback mechanism

### Next Steps

1. Complete provider safety features:
   - Rate limiting
   - File size validation
   - File type validation
   - Retry logic

2. Add comprehensive tests:
   - Unit tests for each provider
   - Integration tests
   - Error handling tests

3. Improve documentation:
   - Update main README
   - Add provider-specific docs
   - Document limitations

4. Enhance provider system:
   - Add fallback mechanism
   - Add provider selection logic
   - Add health checks
   - Add usage statistics

## 2024-02-18

### Enhanced Error Handling and Provider Fallback

1. Implemented new error handling system:
   - Added RetryableError for temporary failures
   - Added NonRetryableError for permanent failures
   - Added provider context to error messages
   - Added URL validation for all uploads

2. Improved provider fallback:
   - One retry with exponential backoff for temporary failures
   - Immediate fallback to next provider for permanent failures
   - Clear error messages with provider context
   - Proper handling of provider chains

3. Added URL validation:
   - HEAD request validation for all URLs
   - Redirect following
   - Retry on temporary failures
   - Configurable timeouts

4. Next steps:
   - Add more test coverage for error scenarios
   - Improve error messages and logging
   - Add performance metrics
   - Add provider health checks

[1.7.9]: https://github.com/twardoch/twat-fs/compare/v1.7.8...v1.7.9
[1.7.8]: https://github.com/twardoch/twat-fs/compare/v1.7.5...v1.7.8
[1.7.5]: https://github.com/twardoch/twat-fs/compare/v1.0.9...v1.7.5
[1.0.9]: https://github.com/twardoch/twat-fs/compare/v1.0.8...v1.0.9
[1.0.8]: https://github.com/twardoch/twat-fs/compare/v1.0.7...v1.0.8
[1.0.7]: https://github.com/twardoch/twat-fs/compare/v1.0.6...v1.0.7
[1.0.6]: https://github.com/twardoch/twat-fs/compare/v1.0.5...v1.0.6
[1.0.5]: https://github.com/twardoch/twat-fs/compare/v1.0.0...v1.0.5
[1.0.0]: https://github.com/twardoch/twat-fs/releases/tag/v1.0.0 
