---
this_file: TODO.md
---

# TODO

This document outlines the current tasks for the project—with immediate fixes taking priority—followed by medium- and long-term improvements. The details below are based on recent cleanup logs and test feedback.

---

## Immediate Priorities (Critical Fixes)

### A. Test Failures and Provider Core Issues

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

---

## B. Code Quality and Refactoring

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

---

## C. Type System Overhaul and Documentation

1. **Type Annotation Consistency**
   - Add missing return type annotations in all functions across both source modules and tests.
   - Change legacy type hints (e.g., `Union[str, list[str]]`) to the newer union syntax using the pipe operator (`str | list[str]`).
   - Fix incompatibility issues such as the return type incompatibilities (as seen in `dropbox.py`).

2. **Documentation and Docstrings**
   - Update docstrings for all functions to explain parameter roles, methodologies, and error conditions.
   - Provide concrete examples within the docstrings where feasible.

> **Wait, but**  
> Consistent type annotations strengthen the robustness and maintainability of the codebase. Detailed docstrings and in-line comments will further help new contributors understand the provider architecture and the rationale behind key decisions.

---

## D. Test Suite Improvements

1. **Mock and Fixture Corrections**
   - Adjust existing test mocks (especially in `tests/test_upload.py` and `tests/test_integration.py`) to match updated function signatures and ensure proper parameters are passed.
   - Replace hardcoded test credentials with safer mock values or environment substitutes.

2. **Enhance Test Coverage**
   - Add tests for edge cases and provider fallback mechanisms.
   - Use parameterized tests (with `pytest.mark.parametrize`) or property-based testing (e.g., hypothesis) to cover a broad range of inputs.
   - Create shared test contracts for provider implementations (via a common "provider contract test").

> **Wait, but**  
> Upgrading the test suite is as crucial as fixing provider code. A more robust testing infrastructure will catch integration issues faster and provide ongoing assurance as refactoring continues.

---

## E. Untracked Files and Version Control Cleanup

1. **File Cleanup**
   - Confirm that `src/twat_fs/upload_providers/www0x0.py` should be retained (as it appears to be a rename from `0x0.py`).
   - Remove the outdated `src/twat_fs/upload_providers/0x0.py` file and add the new file properly into version control.

> **Wait, but**  
> Version control hygiene is important to avoid confusion over file naming, especially when similar files exist. Ensuring that only the correct files are tracked prevents stale code from complicating further development.

---

## Medium-Term Priorities

1. **Test Coverage Expansion**
   - Develop unit tests for skipped S3 provider tests.
   - Create more comprehensive tests covering provider authentication (valid, invalid, missing credentials).
   - Simulate various error conditions (network failures, API errors) across providers.
   - Integrate performance benchmarks to evaluate upload speeds and handle bottlenecks.

2. **Documentation Enhancements**
   - Produce detailed, provider-specific documentation that describes configuration, setup instructions, and usage examples.
   - Add a "Choosing a Provider" guide to help users pick the best provider for their use case.
   - Include a troubleshooting guide covering common errors such as missing credentials and mock mismatches.

> **Wait, but**  
> Expanding both tests and user documentation are medium-term improvements that reinforce the stability of the package while smoothing the user experience. They also serve as a strong foundation for future feature work.

---

## Long-Term Goals / Enhancements

1. **Provider Feature Enhancements**
   - Implement provider selection logic based on file attributes (size, type).
   - Add periodic health checks and statistics for each provider.
   - Incorporate advanced features such as upload cancellation, resume support, and progress callbacks.
   
2. **CI/CD and Automated Release**
   - Establish an automated version bump mechanism.
   - Integrate automated releases and dependency management (e.g., Dependabot).
   - Generate code coverage reports as part of continuous integration.

3. **Security Hardening**
   - Ensure no hardcoded credentials are present (replace with secure environment variables).
   - Implement retries with exponential backoff for failed uploads.
   - Add rate limiting to prevent abuse.

4. **Provider Contract and Abstract Method Enforcement**
   - Formalize the provider contract and ensure all providers adhere to it.
   - Document abstract method requirements for new provider implementations in a dedicated "Provider Development Guide."

> **Wait, but**  
> Long-term enhancements will not only improve feature richness but also operational resilience and security. Keeping these goals in sight, even as immediate issues are resolved, will foster sustainable development practices.

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


