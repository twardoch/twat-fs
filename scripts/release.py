#!/usr/bin/env -S uv run
# /// script
# dependencies = ["build", "twine", "rich"]
# ///
# this_file: scripts/release.py

"""
Release script for twat-fs package.
Builds the package and prepares for release.
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
            console.print(result.stdout, style="dim")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"✗ {description} failed", style="red")
        if e.stdout:
            console.print(f"stdout: {e.stdout}", style="dim")
        if e.stderr:
            console.print(f"stderr: {e.stderr}", style="red")
        return False

def main():
    """Main release function."""
    console.print("[bold]Preparing twat-fs release[/bold]")
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    original_cwd = Path.cwd()
    
    try:
        import os
        os.chdir(project_root)
        
        # Check git status
        console.print("\n[bold]Checking git status...[/bold]")
        result = subprocess.run(
            ["git", "status", "--porcelain"], 
            capture_output=True, 
            text=True
        )
        if result.stdout.strip():
            console.print("[yellow]Warning: Working directory is not clean[/yellow]")
            console.print(result.stdout)
        
        # Get current version
        console.print("\n[bold]Getting version information...[/bold]")
        try:
            result = subprocess.run(
                [sys.executable, "-c", "exec(open('src/twat_fs/__version__.py').read()); print(__version__)"],
                capture_output=True,
                text=True,
                check=True
            )
            version = result.stdout.strip()
            console.print(f"  Current version: {version}", style="green")
        except Exception as e:
            console.print(f"  Could not determine version: {e}", style="red")
            return False
        
        # Build package
        console.print("\n[bold]Building package...[/bold]")
        if not run_command([sys.executable, "-m", "build"], "Building package"):
            return False
        
        # Check with twine
        console.print("\n[bold]Checking package with twine...[/bold]")
        if not run_command([sys.executable, "-m", "twine", "check", "dist/*"], "Checking package"):
            return False
        
        # List built files
        console.print("\n[bold]Built files:[/bold]")
        dist_dir = project_root / "dist"
        if dist_dir.exists():
            for file in dist_dir.iterdir():
                console.print(f"  {file.name}", style="cyan")
        
        console.print("\n[bold green]Release preparation completed![/bold green]")
        console.print("\n[bold]Next steps:[/bold]")
        console.print("1. Tag the release: git tag vX.Y.Z")
        console.print("2. Push the tag: git push origin vX.Y.Z")
        console.print("3. Upload to PyPI: python -m twine upload dist/*")
        
        return True
        
    except Exception as e:
        console.print(f"\n[bold red]Release preparation failed: {e}[/bold red]")
        return False
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)