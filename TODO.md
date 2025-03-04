---
this_file: TODO.md
---

# TODO

Tip: Periodically run `python ./cleanup.py status` to see results of lints and tests. Use `uv pip ...` not `pip ...`


## Phase 1

- [ ] Fix failing unit tests
  - [x] Fix `TestCreateProviderInstance` tests
  - [x] Fix `TestGatherWithConcurrency` tests
  - [ ] Fix `TestLogUploadAttempt.test_log_upload_attempt_success` test
    - Issue: logger.info is not being called in the log_upload_attempt function
    - Fix: Implement proper logger.info call in the success branch
  - [ ] Fix `TestGatherWithConcurrency.test_gather_with_concurrency_with_exceptions` test
    - Issue: Test is failing with RuntimeError instead of ValueError
    - Fix: Ensure the correct exception type is propagated in gather_with_concurrency
- [ ] Fix boolean argument issues in `utils.py`
  - [ ] Fix FBT001 linter error in `utils.py` line 251
    - Issue: Boolean-typed positional argument in function definition
    - Fix: Convert boolean positional arguments to keyword-only arguments
  - [ ] Refactor functions with too many arguments
    - Use keyword-only arguments for optional parameters
    - Group related parameters into dataclasses or TypedDict
- [ ] Fix type annotation issues
  - [ ] Fix missing imports for `aiohttp` and `loguru`
  - [ ] Fix unknown attribute error for `Response.status`
  - [ ] Add proper type hints for HTTP response objects

## Phase 2

- [ ] Fix exception handling issues
  - [ ] Implement consistent error handling patterns
  - [ ] Add proper error context in exception messages
  - [ ] Use custom exception types for specific error scenarios
- [ ] Fix linter issues in `cleanup.py`
  - [ ] Address unused imports
  - [ ] Fix function complexity issues
  - [ ] Improve error handling
- [ ] Update `pyproject.toml` to fix deprecated linter settings
  - [ ] Update ruff configuration
  - [ ] Add explicit Python version targets
  - [ ] Configure mypy settings

## Phase 3

- [ ] Improve code quality and maintainability
  - [ ] Reduce function complexity
  - [ ] Add comprehensive docstrings
  - [ ] Implement consistent logging patterns
- [ ] Enhance test coverage
  - [ ] Add tests for edge cases
  - [ ] Implement integration tests for providers
  - [ ] Add performance benchmarks

## Medium Priority

- [ ] Refine HTTP response handling
  - [ ] Standardize response parsing across providers
  - [ ] Improve error message extraction
- [ ] Fix function complexity issues
  - [ ] Break down complex functions into smaller, focused functions
  - [ ] Extract reusable utility functions
- [ ] Document best practices for creating new providers
  - [ ] Create comprehensive provider development guide
  - [ ] Add examples for common provider patterns
- [ ] Fix unused arguments and imports
  - [ ] Remove dead code
  - [ ] Consolidate duplicate functionality

## New Providers

- [ ] Add support for Imgur
- [ ] Add support for Cloudinary
- [ ] Add support for Google Drive
- [ ] Add support for OneDrive
- [ ] Add support for Box
- [ ] Add support for Mega
- [ ] Add support for Backblaze B2
- [ ] Add support for Wasabi

## Completed Tasks

- [x] Fix `TestCreateProviderInstance` tests
- [x] Fix `TestGatherWithConcurrency` tests
- [x] Create `utils.py` module for shared functionality
- [x] Refactor provider modules to use `utils.py`
- [x] Create provider templates
- [x] Implement factory pattern for provider instantiation
- [x] Standardize async/sync conversion patterns
- [x] Write unit tests for utility functions
- [x] Create provider base classes