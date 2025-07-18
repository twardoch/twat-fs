#!/usr/bin/env -S uv run
# /// script
# dependencies = ["pytest", "pytest-cov", "rich"]
# ///
# this_file: scripts/test.py

"""
Test script for twat-fs package.
Runs tests with coverage reporting.
"""

import subprocess
import sys
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn(f"[bold blue]{description}..."),
            console=console,
        ) as progress:
            task = progress.add_task(description)
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            progress.update(task, completed=True)
        
        console.print(f"✓ {description}", style="green")
        if result.stdout:
            console.print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"✗ {description} failed", style="red")
        if e.stdout:
            console.print(f"stdout: {e.stdout}")
        if e.stderr:
            console.print(f"stderr: {e.stderr}", style="red")
        return False

def main():
    """Main test function."""
    console.print("[bold]Running twat-fs tests[/bold]")
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    original_cwd = Path.cwd()
    
    try:
        import os
        os.chdir(project_root)
        
        # Run tests with coverage
        console.print("\n[bold]Running tests with coverage...[/bold]")
        cmd = [
            sys.executable, "-m", "pytest",
            "--cov=src/twat_fs",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--cov-config=pyproject.toml",
            "-v",
            "tests/"
        ]
        
        if not run_command(cmd, "Running tests"):
            # Try running tests without coverage if that fails
            console.print("\n[bold yellow]Retrying without coverage...[/bold yellow]")
            cmd = [sys.executable, "-m", "pytest", "-v", "tests/"]
            if not run_command(cmd, "Running tests (no coverage)"):
                return False
        
        console.print("\n[bold green]Tests completed successfully![/bold green]")
        return True
        
    except Exception as e:
        console.print(f"\n[bold red]Test run failed: {e}[/bold red]")
        return False
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)