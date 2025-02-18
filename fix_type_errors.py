#!/usr/bin/env python3

import re
from pathlib import Path
import tokenize
import io
import contextlib


def fix_provider_file(file_path: Path) -> bool:
    """
    Fix type errors in a provider file.

    Args:
        file_path: Path to the Python file to modify

    Returns:
        bool: Whether any changes were made
    """
    with open(file_path) as f:
        content = f.read()

    # Check syntax first
    try:
        list(tokenize.generate_tokens(io.StringIO(content).readline))
    except tokenize.TokenError:
        return False

    # Track changes
    changes_made = False

    # Add necessary imports
    imports_to_add = [
        "from twat_fs.upload_providers.core import convert_to_upload_result",
        "from twat_fs.upload_providers.types import UploadResult",
        "from typing import Any",
    ]

    # Add imports if not present
    for import_stmt in imports_to_add:
        if import_stmt not in content:
            content = import_stmt + "\n" + content
            changes_made = True

    # Patterns for fixing upload methods
    patterns = [
        # Change return type annotation for upload_file and async_upload_file
        (
            r"def (async_)?upload_file\((.*?)\) -> str:",
            r"def \1upload_file(\2) -> UploadResult:",
        ),
        # Wrap return values with convert_to_upload_result
        (r"return\s+([^(]+)$", r"return convert_to_upload_result(\1)"),
        # Replace SimpleProviderBase with BaseProvider
        (
            r"from twat_fs\.upload_providers\.simple import SimpleProviderBase",
            r"from twat_fs.upload_providers.simple import BaseProvider",
        ),
        # Update class inheritance
        (r"class \w+\(SimpleProviderBase\):", r"class \g<0>[:-1] BaseProvider):"),
    ]

    # Apply patterns
    for pattern, repl in patterns:
        new_content, n = re.subn(pattern, repl, content, flags=re.MULTILINE | re.DOTALL)
        if n > 0:
            content = new_content
            changes_made = True

    # Write changes if any
    if changes_made:
        with open(file_path, "w") as f:
            f.write(content)

    return changes_made


def main():
    # Paths to check
    paths = [
        "src/twat_fs/upload_providers/dropbox.py",
        "src/twat_fs/upload_providers/core.py",
        "src/twat_fs/upload_providers/litterbox.py",
        "src/twat_fs/upload_providers/catbox.py",
        "src/twat_fs/upload_providers/uguu.py",
        "src/twat_fs/upload_providers/pixeldrain.py",
        "src/twat_fs/upload_providers/filebin.py",
        "src/twat_fs/upload_providers/bashupload.py",
        "src/twat_fs/upload_providers/fal.py",
    ]

    for path_str in paths:
        path = Path(path_str)

        # Fix type errors
        with contextlib.suppress(Exception):
            fix_provider_file(path)


if __name__ == "__main__":
    main()
