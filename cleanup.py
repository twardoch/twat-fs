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

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import NoReturn

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


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
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

    def _check_required_files(self) -> bool:
        """Check if all required files exist."""
        missing = False
        for file in REQUIRED_FILES:
            if not (self.workspace / file).exists():
                print_message(f"Error: {file} is missing")
                missing = True
        return not missing

    def _generate_tree(self) -> None:
        """Generate and display tree structure of the project."""
        if not check_command_exists("tree"):
            print_message(
                "Warning: 'tree' command not found. Skipping tree generation."
            )
            return None

        try:
            result = run_command(
                ["tree", "-a", "-I", ".git", "--gitignore", "-n", "-h", "-I", "*_cache"]
            )
            print("\nProject structure:")
            print(result.stdout)
        except Exception as e:
            print_message(f"Failed to generate tree: {e}")
        return None

    def _git_status(self) -> bool:
        """Check git status and return True if there are changes."""
        result = run_command(["git", "status", "--porcelain"], check=False)
        return bool(result.stdout.strip())

    def _venv(self) -> None:
        """Create and activate virtual environment using uv."""
        print_message("Setting up virtual environment")
        try:
            run_command(["uv", "venv"])
            # Note: source command can't be run directly in Python
            # The activation needs to be done in the shell by the user
            print_message("Virtual environment created. Please activate it with:")
            print("source .venv/bin/activate")
        except Exception as e:
            print_message(f"Failed to create virtual environment: {e}")

    def _install(self) -> None:
        """Install package in development mode with all extras."""
        print_message("Installing package with all extras")
        try:
            self._venv()
            run_command(["uv", "pip", "install", "-e", ".[all,test,dev]"])
            print_message("Package installed successfully")
        except Exception as e:
            print_message(f"Failed to install package: {e}")

    def _hatch(self) -> None:
        """Run hatch commands for fixing, type checking and testing."""
        print_message("Running hatch commands")

        # Run each command with check=False to handle warnings
        try:
            self._install()
            # Store all results to check success
            results = []

            print_message("Running code fixes...")
            result = run_command(["python", "-m", "hatch", "run", "fix"], check=False)
            results.append(result)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)

            print_message("Running type checks...")
            result = run_command(
                ["python", "-m", "hatch", "run", "type-check"], check=False
            )
            results.append(result)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)

            print_message("Running tests...")
            result = run_command(["python", "-m", "hatch", "test"], check=False)
            results.append(result)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)

            # Check if all commands completed successfully
            if all(cmd.returncode == 0 for cmd in results):
                print_message("All hatch commands completed successfully")
            else:
                print_message("Hatch commands completed with warnings/errors")
        except Exception as e:
            print_message(f"Failed during hatch commands: {e}")

    def status(self) -> None:
        """Show current repository status: tree structure, git status, and run checks."""
        self._print_header("Current Status")

        # Check required files
        self._check_required_files()

        # Show tree structure
        self._generate_tree()

        # Show git status
        result = run_command(["git", "status"], check=False)
        print(result.stdout)

        # Run additional checks
        self._print_header("Environment Status")
        self._venv()
        self._install()
        self._hatch()

    def venv(self) -> None:
        """Create and activate virtual environment."""
        self._print_header("Virtual Environment Setup")
        self._venv()

    def install(self) -> None:
        """Install package with all extras."""
        self._print_header("Package Installation")
        self._install()

    def hatch(self) -> None:
        """Run hatch commands."""
        self._print_header("Hatch Commands")
        self._hatch()

    def update(self) -> None:
        """Show status and commit any changes if needed."""
        # First show current status
        self.status()

        # Then handle git changes if any
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

    def push(self) -> None:
        """Push changes to remote repository."""
        self._print_header("Pushing Changes")
        try:
            run_command(["git", "push"])
            print_message("Changes pushed successfully")
        except Exception as e:
            print_message(f"Failed to push changes: {e}")


def print_usage() -> None:
    """Print usage information."""
    print("Usage:")
    print("  cleanup.py status   # Show current status and run all checks")
    print("  cleanup.py update   # Update and commit changes")
    print("  cleanup.py push     # Push changes to remote")
    print("  cleanup.py venv     # Create virtual environment")
    print("  cleanup.py install  # Install package with all extras")
    print("  cleanup.py hatch    # Run hatch commands")


def main() -> NoReturn:
    """Main entry point."""
    valid_commands = ["update", "push", "status", "venv", "install", "hatch"]
    if len(sys.argv) != 2 or sys.argv[1] not in valid_commands:
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
    elif command == "venv":
        cleanup.venv()
    elif command == "install":
        cleanup.install()
    elif command == "hatch":
        cleanup.hatch()

    sys.exit(0)


if __name__ == "__main__":
    main()
