---
this_file: TODO.md
---

# TODO



- [ ] Review and refactor shared functionality in upload provider modules

  Across nearly all provider modules (such as bashupload.py, catbox.py, filebin.py, pixeldrain.py, uguu.py, www0x0.py, etc.), there are several notable repeated patterns:

  - **Provider Help Dictionaries**  
    Each module defines a `PROVIDER_HELP` dictionary with keys like `setup` and `deps` even though the content may vary slightly. The overall structure is identical across providers. This redundancy suggests that a helper or factory function could generate these help dictionaries based upon provider-specific parameters.

  - **Common Provider Accessor Functions**  
    Most modules implement:
    - A class method `get_provider()` that typically returns a cast instance (e.g., using `cast(ProviderClient, cls())`).
    - A module-level function `get_provider()` which simply wraps the class method.
    - A similar pattern with `get_credentials()` where simple providers always return `None` (with a comment noting that they don't need credentials).
    - An `upload_file()` wrapper function that retrieves the provider instance (raising an error if not found) and then delegates to its `upload_file` or `upload_file_impl` method.
    
    These functions follow nearly identical logic and error-checking (for instance, checking if the provider exists, and if not, raising a ValueError with a message like "Failed to initialize provider").

  - **File Handling and Error Patterns**  
    There is recurring code around handling file operations:
    - Opening files in binary mode for upload.
    - Validating file existence and readability.
    - Consistent error handling in case an API call fails or an exception is caught.
    
    This pattern appears in multiple providers and is an ideal candidate for consolidation into a shared utility function.

  - **Similar Import and Inheritance Structures**  
    Many of the simple providers import from the same base module (`simple.py`) and reuse a common provider type pattern—assigning a `provider_name`, setting a URL, and implementing an `upload_file_impl` method that closely follows the same structure.

  **Refactoring Proposal**:

  - Create a new file named `utils.py` inside the `upload_providers` folder.
  - Offload common functionality such as:
    - Helper functions to generate or validate the `PROVIDER_HELP` dictionaries.
    - A universal file handling utility (e.g., context managers for opening and validating files).
    - Standardized implementations for the module-level `get_provider()`, `get_credentials()`, and `upload_file()` functions.
    - Error handling wrappers for calling the provider's upload routines.
    
  Consolidating these functions would adhere to DRY principles and simplify the maintenance and evolution of provider modules.

- [ ] Investigate if any additional unique provider-specific patterns might require conditional handling in the utils module

- **Additional Common Patterns Identified:**

  - **Asynchronous-to-Synchronous Conversion:**
    Several providers (e.g., catbox.py, fal.py, litterbox.py) use an `async_to_sync` wrapper to convert asynchronous upload methods into synchronous ones. The conversion logic is nearly identical across these modules and could be centralized into a shared utility.

  - **HTTP Response and Status Code Validation:**
    Many modules include similar logic to check HTTP response codes (e.g., handling 429 for rate limits by raising `RetryableError`, and non-200 responses by raising `NonRetryableError`). This pattern is repeated in providers like bashupload.py, pixeldrain.py, and www0x0.py, among others, suggesting an opportunity to abstract this into a helper function.

  - **Environment Variable Credential Handling:**
    Providers such as dropbox.py, fal.py, and s3.py fetch credentials from environment variables using similar patterns. A shared utility function could streamline this process, ensuring consistent validation and error messages.

  - **File Handling Techniques:**
    While some providers utilize the file handling logic in `simple.py` (which includes methods for validating and opening files in binary mode), others implement their own similar patterns. Unifying these methods could reduce redundancy and potential errors.

  - **Consistent Logging Practices:**
    Across all providers, there is recurring use of logging (using `logger.debug`, `logger.warning`, and `logger.error`) to report state changes, errors, and debugging information. Standardizing these log messages and the structure in which they are used can improve maintainability.

  - **Async/Coroutine Type Handling:**
    With the recent protocol updates to support both Awaitable[UploadResult] and Coroutine[Any, Any, UploadResult], providers need consistent patterns for:
    - Converting between async/await and coroutine patterns
    - Handling async decorators with proper type hints
    - Managing async context managers and resource cleanup
    - Standardizing error handling in async code

  *Note: The intent of these refactoring steps is to offload the shared portions into a new `utils.py` module inside the `upload_providers` folder. The module has been created, but providers need to be updated to use it consistently, especially with the new async type handling patterns.*