#!/usr/bin/env -S uv run
# /// script
# dependencies = ["build", "hatch", "rich"]
# ///
# this_file: scripts/build.py

"""
Build script for twat-fs package.
Builds the package using hatchling backend with version from git tags.
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
    """Main build function."""
    console.print("[bold]Building twat-fs package[/bold]")
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    original_cwd = Path.cwd()
    
    try:
        import os
        os.chdir(project_root)
        
        # Clean previous builds
        console.print("\n[bold]Cleaning previous builds...[/bold]")
        dist_dir = project_root / "dist"
        if dist_dir.exists():
            import shutil
            shutil.rmtree(dist_dir)
            console.print("✓ Removed dist directory", style="green")
        
        # Build package
        console.print("\n[bold]Building package...[/bold]")
        if not run_command([sys.executable, "-m", "build"], "Building package"):
            return False
        
        # List built files
        console.print("\n[bold]Built files:[/bold]")
        if dist_dir.exists():
            for file in dist_dir.iterdir():
                console.print(f"  {file.name}", style="cyan")
        
        # Show version information
        console.print("\n[bold]Version information:[/bold]")
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "-c", "exec(open('src/twat_fs/__version__.py').read()); print(__version__)"],
                capture_output=True,
                text=True,
                check=True
            )
            console.print(f"  Version: {result.stdout.strip()}", style="green")
        except Exception as e:
            console.print(f"  Could not determine version: {e}", style="yellow")
        
        console.print("\n[bold green]Build completed successfully![/bold green]")
        return True
        
    except Exception as e:
        console.print(f"\n[bold red]Build failed: {e}[/bold red]")
        return False
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)