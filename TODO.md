---
this_file: TODO.md
---

# TODO

This document outlines the current tasks for the project—with immediate fixes taking priority—followed by medium- and long-term improvements. The details below are based on recent cleanup logs and test feedback.

---

## Immediate Priorities (Critical Fixes)

### A. Error Handling Improvements

1. **Test Coverage for New Error System**
   - Add comprehensive tests for RetryableError scenarios
   - Add comprehensive tests for NonRetryableError scenarios
   - Add tests for provider fallback chains
   - Add tests for URL validation

2. **Error Message Improvements**
   - Add more context to error messages
   - Include provider-specific troubleshooting info
   - Add error codes for common failures
   - Improve logging of error chains

3. **URL Validation Enhancements**
   - Add support for custom validation strategies
   - Add content-type validation
   - Add size validation
   - Add timeout configuration

### B. Test Failures and Provider Core Issues

1. **FAL Provider Implementation Flaws**
   - **Missing Core Functions:**  
     - Implement `get_credentials()` in `src/twat_fs/upload_providers/fal.py` so that it retrieves credentials from the environment.  
       *Example:*
       ```python
       def get_credentials() -> dict[str, Any] | None:
           """Fetch FAL credentials from environment."""
           return {"key": os.getenv("FAL_KEY")} if os.getenv("FAL_KEY") else None
       ```
     - Implement the `get_provider()` function to initialize and return the FAL client.  
     - Verify that the FAL provider fully complies with the Provider protocol.
     
   - **Abstract Class Instantiation Issues:**  
     - Ensure concrete implementations (e.g., in `bashupload.py`, `simple.py`, etc.) implement the required abstract method (`upload_file_impl`).  
       *For instance, rename or refactor the upload method to consistently follow the naming convention (either `upload_file` or `upload_file_impl`).*
   
2. **Test Infrastructure and Mocks**
   - Update test mocks to correctly reflect the method signatures.  
     - Ensure that in tests (e.g., in `tests/test_upload.py`), when mocking provider methods, the signature includes all expected keyword arguments: `unique`, `force`, and `upload_path`.
   - Fix FAL test fixtures to correctly import and call `fal.get_credentials()` and `fal.get_provider()`.
   - Address any attribute errors in tests (e.g., missing attributes on the fal provider module).

> **Wait, but**  
> These changes are critical because they directly influence both provider functionality and test accuracy. The FAL provider errors are causing several tests to error out, which blocks valid test runs. Properly updating mocks will allow integration tests to reflect the true behavior of the system.

### C. Code Quality and Refactoring

1. **CLI and Function Arguments**
   - Refactor boolean-typed positional arguments (`unique`, `force`) in `src/twat_fs/cli.py` to keyword-only arguments.  
     *Example:*
     ```python
     def upload_file(
         file_path: str | Path,
         provider: str | list[str] = PROVIDERS_PREFERENCE,
         *,  # Enforce keyword usage from here on
         unique: bool = False,
         force: bool = False,
         upload_path: str | None = None,
     ) -> str:
         ...
     ```
   
2. **Dropbox Provider Complexity**
   - Reduce complexity in `src/twat_fs/upload_providers/dropbox.py`:
     - Break the `upload_file` function into helper functions such as `_validate_upload_path()`, `_create_remote_folder()`, and `_upload_file_content()`.
     - Add missing type annotations, fix return types, and ensure a final return statement exists.
   
3. **General Provider Implementations**
   - For unused method arguments (e.g., `remote_path` in `bashupload.py`, `simple.py`, `termbin.py`, `uguu.py`, and `www0x0.py`), rename the parameter to `_remote_path` to signify it is intentionally unused.
   - Verify that method names and signatures follow the provider contract consistently across all modules.

> **Wait, but**  
> Clear structuring of function signatures and reducing complexity not only eases maintenance but also helps the type checker (mypy/ruff) pass with fewer errors. This clarity is critical to support future extension and new provider integrations.

### D. Type System Overhaul and Documentation

1. **Type Annotation Consistency**
   - Add missing return type annotations in all functions across both source modules and tests.
   - Change legacy type hints (e.g., `Union[str, list[str]]`) to the newer union syntax using the pipe operator (`str | list[str]`).
   - Fix incompatibility issues such as the return type incompatibilities (as seen in `dropbox.py`).

2. **Documentation and Docstrings**
   - Update docstrings for all functions to explain parameter roles, methodologies, and error conditions.
   - Provide concrete examples within the docstrings where feasible.

> **Wait, but**  
> Consistent type annotations strengthen the robustness and maintainability of the codebase. Detailed docstrings and in-line comments will further help new contributors understand the provider architecture and the rationale behind key decisions.

### E. Test Suite Improvements

1. **Error Handling Tests**
   - Add tests for RetryableError scenarios:
     - Rate limiting
     - Network timeouts
     - Server errors
   - Add tests for NonRetryableError scenarios:
     - Authentication failures
     - Invalid files
     - Provider not available
   - Add tests for provider fallback chains
   - Add tests for URL validation

2. **Provider-Specific Tests**
   - Add tests for catbox.moe provider
   - Add tests for litterbox.catbox.moe provider
   - Update existing provider tests with new error handling

---

## Medium-Term Priorities

1. **Provider Health Monitoring**
   - Add provider health checks
   - Add provider statistics collection
   - Add provider performance metrics
   - Add provider reliability scoring

2. **Smart Provider Selection**
   - Implement provider scoring system
   - Add automatic provider ranking
   - Add file-type based provider selection
   - Add size-based provider selection

3. **Enhanced Error Recovery**
   - Add more sophisticated retry strategies
   - Add circuit breaker pattern
   - Add provider quarantine
   - Add provider rate limiting

4. **Documentation Enhancements**
   - Add error handling guide
   - Add provider selection guide
   - Add troubleshooting guide
   - Add performance tuning guide

---

## Long-Term Goals / Enhancements

1. **Provider Feature Enhancements**
   - Add provider health monitoring
   - Add provider statistics
   - Add provider rate limiting
   - Add provider circuit breakers

2. **CI/CD and Automated Release**
   - Add automated error reporting
   - Add performance regression testing
   - Add reliability testing
   - Add load testing

3. **Security Hardening**
   - Add URL scanning
   - Add content validation
   - Add provider verification
   - Add upload encryption

---

## Additional Notes

- **Review and Iteration:**  
  Regularly review the changes in `LOG.md` and integrate any new issues or updates from code quality tools (like ruff and mypy).

- **Collaboration and Commits:**  
  Ensure that changes are grouped logically with clear commit messages for clarity during reviews.

- **Performance Improvements:**  
  As features stabilize, consider performance profiling and optimizations for large file uploads and fallback logic.

---

*This TODO document is a living artifact. Revisit and update it frequently as fixes are applied and new issues or improvements are identified.*


