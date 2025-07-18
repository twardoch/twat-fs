#!/usr/bin/env -S uv run
# /// script
# dependencies = ["ruff", "mypy", "rich"]
# ///
# this_file: scripts/lint.py

"""
Linting script for twat-fs package.
Runs ruff and mypy for code quality checks.
"""

import subprocess
import sys
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def run_command(cmd: list[str], description: str, capture_output: bool = True) -> bool:
    """Run a command and return success status."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn(f"[bold blue]{description}..."),
            console=console,
        ) as progress:
            task = progress.add_task(description)
            result = subprocess.run(cmd, check=True, capture_output=capture_output, text=True)
            progress.update(task, completed=True)
        
        console.print(f"✓ {description}", style="green")
        if capture_output and result.stdout:
            console.print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"✗ {description} failed", style="red")
        if capture_output and e.stdout:
            console.print(f"stdout: {e.stdout}")
        if capture_output and e.stderr:
            console.print(f"stderr: {e.stderr}", style="red")
        return False

def main():
    """Main linting function."""
    console.print("[bold]Running twat-fs linting[/bold]")
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    original_cwd = Path.cwd()
    
    try:
        import os
        os.chdir(project_root)
        
        success = True
        
        # Run ruff check
        console.print("\n[bold]Running ruff check...[/bold]")
        if not run_command([
            sys.executable, "-m", "ruff", "check", "src/twat_fs", "tests", "--output-format=github"
        ], "Ruff check"):
            success = False
        
        # Run ruff format check
        console.print("\n[bold]Running ruff format check...[/bold]")
        if not run_command([
            sys.executable, "-m", "ruff", "format", "--check", "src/twat_fs", "tests"
        ], "Ruff format check"):
            success = False
        
        # Run mypy
        console.print("\n[bold]Running mypy...[/bold]")
        if not run_command([
            sys.executable, "-m", "mypy", "src/twat_fs", "tests"
        ], "MyPy type check"):
            success = False
        
        if success:
            console.print("\n[bold green]All linting checks passed![/bold green]")
        else:
            console.print("\n[bold red]Some linting checks failed![/bold red]")
        
        return success
        
    except Exception as e:
        console.print(f"\n[bold red]Linting failed: {e}[/bold red]")
        return False
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)