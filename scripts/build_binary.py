#!/usr/bin/env -S uv run
# /// script
# dependencies = ["pyinstaller", "rich"]
# ///
# this_file: scripts/build_binary.py

"""
Binary building script for twat-fs package.
Creates standalone executable using PyInstaller.
"""

import subprocess
import sys
import platform
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
    """Main binary building function."""
    console.print("[bold]Building twat-fs binary[/bold]")
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    original_cwd = Path.cwd()
    
    try:
        import os
        os.chdir(project_root)
        
        # Determine binary name based on platform
        binary_name = "twat-fs"
        if platform.system() == "Windows":
            binary_name += ".exe"
        
        console.print(f"Building for platform: {platform.system()}")
        console.print(f"Binary name: {binary_name}")
        
        # Clean previous builds
        console.print("\n[bold]Cleaning previous builds...[/bold]")
        dist_dir = project_root / "dist"
        build_dir = project_root / "build"
        
        if dist_dir.exists():
            import shutil
            shutil.rmtree(dist_dir)
            console.print("✓ Removed dist directory", style="green")
        
        if build_dir.exists():
            import shutil
            shutil.rmtree(build_dir)
            console.print("✓ Removed build directory", style="green")
        
        # Build binary
        console.print("\n[bold]Building binary...[/bold]")
        
        # PyInstaller command
        cmd = [
            "uv", "run", "pyinstaller",
            "--onefile",
            "--name", binary_name,
            "--add-data", "src/twat_fs/data:twat_fs/data",
            # Add hidden imports for all providers
            "--hidden-import", "twat_fs.upload_providers.catbox",
            "--hidden-import", "twat_fs.upload_providers.litterbox",
            "--hidden-import", "twat_fs.upload_providers.www0x0",
            "--hidden-import", "twat_fs.upload_providers.uguu",
            "--hidden-import", "twat_fs.upload_providers.bashupload",
            "--hidden-import", "twat_fs.upload_providers.filebin",
            "--hidden-import", "twat_fs.upload_providers.pixeldrain",
            "--hidden-import", "twat_fs.upload_providers.dropbox",
            "--hidden-import", "twat_fs.upload_providers.s3",
            "--hidden-import", "twat_fs.upload_providers.fal",
            # Add other potential hidden imports
            "--hidden-import", "twat_fs.upload_providers.factory",
            "--hidden-import", "twat_fs.upload_providers.core",
            "--hidden-import", "twat_fs.upload_providers.utils",
            "--hidden-import", "twat_fs.upload_providers.async_utils",
            # Entry point
            "src/twat_fs/__main__.py"
        ]
        
        if not run_command(cmd, "Building binary"):
            return False
        
        # Test binary
        console.print("\n[bold]Testing binary...[/bold]")
        binary_path = project_root / "dist" / binary_name
        
        if binary_path.exists():
            console.print(f"✓ Binary created: {binary_path}", style="green")
            
            # Test version command
            try:
                result = subprocess.run(
                    [str(binary_path), "version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    console.print("✓ Binary test passed", style="green")
                    console.print(f"Output: {result.stdout.strip()}", style="cyan")
                else:
                    console.print("✗ Binary test failed", style="red")
                    console.print(f"Error: {result.stderr}", style="red")
                    return False
            except subprocess.TimeoutExpired:
                console.print("✗ Binary test timed out", style="red")
                return False
            except Exception as e:
                console.print(f"✗ Binary test failed: {e}", style="red")
                return False
        else:
            console.print("✗ Binary not found", style="red")
            return False
        
        # Show binary info
        console.print("\n[bold]Binary information:[/bold]")
        stat = binary_path.stat()
        size_mb = stat.st_size / (1024 * 1024)
        console.print(f"  Size: {size_mb:.2f} MB", style="cyan")
        console.print(f"  Path: {binary_path}", style="cyan")
        
        console.print("\n[bold green]Binary build completed successfully![/bold green]")
        return True
        
    except Exception as e:
        console.print(f"\n[bold red]Binary build failed: {e}[/bold red]")
        return False
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)