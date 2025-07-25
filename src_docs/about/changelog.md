---
this_file: src_docs/about/changelog.md
---

# Changelog

All notable changes to twat-fs are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive MkDocs documentation site
- Provider capability discovery system
- Progress reporting functionality
- Batch upload support
- Performance benchmarking suite

### Changed
- Renamed `types.py` to `provider_types.py` to avoid module name conflict
- Improved error handling with more granular error types
- Enhanced type annotations throughout the codebase

### Fixed
- Fixed `gather_with_concurrency` exception handling
- Fixed test mock paths for logger
- Fixed type annotation issues in async methods
- Addressed all linting errors (FBT001/002/003, B904, ARG002)

## [2.5.4] - 2024-01-15

### Added
- Binary distribution support for all major platforms
- Installation scripts for easy setup
- GitHub Actions workflow for automated releases

### Changed
- Updated CI/CD pipeline with improved testing matrix
- Enhanced documentation with binary installation instructions

### Fixed
- Fixed Windows path handling issues
- Improved error messages for configuration problems

## [2.5.3] - 2024-01-10

### Added
- Fal.ai provider for AI/ML workflows
- Provider health check functionality
- Online testing for providers

### Changed
- Improved retry logic with exponential backoff
- Better error classification (Retryable vs NonRetryable)

### Fixed
- Fixed timeout issues with large file uploads
- Resolved race condition in async uploads

## [2.5.0] - 2024-01-01

### Added
- AWS S3 provider with full feature support
- Dropbox provider with OAuth2 support
- Provider fallback system
- Comprehensive test suite

### Changed
- Migrated to plugin-based provider architecture
- Standardized provider interface with protocols
- Improved async/sync compatibility

### Deprecated
- Old provider configuration format

## [2.0.0] - 2023-12-15

### Added
- Multiple provider support
- Async upload capabilities
- CLI interface with Fire
- Type hints throughout

### Changed
- Complete rewrite of core upload logic
- New modular architecture
- Improved error handling

### Breaking Changes
- Changed API from `upload()` to `upload_file()`
- Provider names are now lowercase
- Configuration via environment variables

## [1.0.0] - 2023-11-01

### Added
- Initial release
- Support for catbox.moe uploads
- Basic CLI functionality
- Simple API for programmatic use

[Unreleased]: https://github.com/twardoch/twat-fs/compare/v2.5.4...HEAD
[2.5.4]: https://github.com/twardoch/twat-fs/compare/v2.5.3...v2.5.4
[2.5.3]: https://github.com/twardoch/twat-fs/compare/v2.5.0...v2.5.3
[2.5.0]: https://github.com/twardoch/twat-fs/compare/v2.0.0...v2.5.0
[2.0.0]: https://github.com/twardoch/twat-fs/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/twardoch/twat-fs/releases/tag/v1.0.0