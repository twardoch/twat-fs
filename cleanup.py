#!/usr/bin/env -S uv run -s
# /// script
# dependencies = [
# ]
# ///
# this_file: cleanup.py

"""
Cleanup tool for managing repository tasks.
Provides functionality for updating, checking, and pushing changes.

Usage:
    cleanup.py update  # Update and commit changes
    cleanup.py push    # Push changes to remote
    cleanup.py status  # Show current status
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, NoReturn

# Configuration
IGNORE_PATTERNS = [
    ".git",
    ".venv",
    "__pycache__",
    "*.pyc",
    "dist",
    "build",
    "*.egg-info",
]
REQUIRED_FILES = ["LOG.md", "README.md", "TODO.md"]


def print_message(message: str) -> None:
    """Print a message to console with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} - {message}")
    return None


def run_command(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    try:
        return subprocess.run(cmd, check=check, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print_message(f"Command failed: {' '.join(cmd)}")
        print_message(f"Error: {e.stderr}")
        if check:
            raise
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def check_command_exists(cmd: str) -> bool:
    """Check if a command exists in the system."""
    try:
        subprocess.run(["which", cmd], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False


class Cleanup:
    """Main cleanup tool class."""

    def __init__(self) -> None:
        self.workspace = Path.cwd()

    def _print_header(self, message: str) -> None:
        """Print a section header."""
        print_message(f"\n=== {message} ===")
        return None

    def _check_required_files(self) -> bool:
        """Check if all required files exist."""
        missing = False
        for file in REQUIRED_FILES:
            if not (self.workspace / file).exists():
                print_message(f"Error: {file} is missing")
                missing = True
        return not missing

    def _generate_tree(self) -> None:
        """Generate and save a tree of the project structure."""
        if not check_command_exists("tree"):
            print_message(
                "Warning: 'tree' command not found. Skipping tree generation."
            )
            return None

        ignore_pattern = " ".join([f"-I '{p}'" for p in IGNORE_PATTERNS])
        cmd = f"tree -a {ignore_pattern}"

        try:
            result = run_command(cmd.split())
            with open("tree.txt", "w") as f:
                f.write(result.stdout)
            print_message("Project structure saved to tree.txt")
        except Exception as e:
            print_message(f"Failed to generate tree: {e}")
        return None

    def _git_status(self) -> bool:
        """Check git status and return True if there are changes."""
        result = run_command(["git", "status", "--porcelain"], check=False)
        return bool(result.stdout.strip())

    def update(self) -> None:
        """Update the project: generate tree, check files, and commit if needed."""
        self._print_header("Starting Update Process")

        # Check required files
        if not self._check_required_files():
            print_message("Missing required files. Please fix and retry.")
            return None

        # Generate tree
        self._generate_tree()

        # Check git status
        if self._git_status():
            print_message("Changes detected in repository")
            try:
                # Add all changes
                run_command(["git", "add", "."])
                # Commit changes
                commit_msg = "Update repository files"
                run_command(["git", "commit", "-m", commit_msg])
                print_message("Changes committed successfully")
            except Exception as e:
                print_message(f"Failed to commit changes: {e}")
        else:
            print_message("No changes to commit")
        return None

    def push(self) -> None:
        """Push changes to remote repository."""
        self._print_header("Pushing Changes")

        try:
            run_command(["git", "push"])
            print_message("Changes pushed successfully")
        except Exception as e:
            print_message(f"Failed to push changes: {e}")
        return None

    def status(self) -> None:
        """Show current status."""
        self._print_header("Current Status")

        # Check files
        self._check_required_files()

        # Show git status
        result = run_command(["git", "status"], check=False)
        print(result.stdout)
        return None


def print_usage() -> None:
    """Print usage information."""
    print("Usage:")
    print("  cleanup.py update  # Update and commit changes")
    print("  cleanup.py push    # Push changes to remote")
    print("  cleanup.py status  # Show current status")
    return None


def main() -> NoReturn:
    """Main entry point."""
    if len(sys.argv) != 2 or sys.argv[1] not in ["update", "push", "status"]:
        print_usage()
        sys.exit(1)

    cleanup = Cleanup()
    command = sys.argv[1]

    if command == "update":
        cleanup.update()
    elif command == "push":
        cleanup.push()
    elif command == "status":
        cleanup.status()

    sys.exit(0)


if __name__ == "__main__":
    main()
