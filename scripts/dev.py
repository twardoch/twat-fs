#!/usr/bin/env -S uv run
# /// script
# dependencies = ["rich", "fire"]
# ///
# this_file: scripts/dev.py

"""
Development utility script for twat-fs package.
Provides common development commands.
"""

import subprocess
import sys
from pathlib import Path
from rich.console import Console
import fire

console = Console()

class DevCommands:
    """Development commands for twat-fs."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.scripts_dir = self.project_root / "scripts"
    
    def build(self):
        """Build the package."""
        console.print("[bold]Building package...[/bold]")
        return subprocess.run([sys.executable, str(self.scripts_dir / "build.py")]).returncode
    
    def test(self):
        """Run tests."""
        console.print("[bold]Running tests...[/bold]")
        return subprocess.run([sys.executable, str(self.scripts_dir / "test.py")]).returncode
    
    def lint(self):
        """Run linting."""
        console.print("[bold]Running linting...[/bold]")
        return subprocess.run([sys.executable, str(self.scripts_dir / "lint.py")]).returncode
    
    def fix(self):
        """Fix linting issues."""
        console.print("[bold]Fixing linting issues...[/bold]")
        import os
        os.chdir(self.project_root)
        
        # Run ruff fix
        subprocess.run([
            sys.executable, "-m", "ruff", "check", "--fix", "--unsafe-fixes", 
            "src/twat_fs", "tests"
        ])
        
        # Run ruff format
        subprocess.run([
            sys.executable, "-m", "ruff", "format", 
            "src/twat_fs", "tests"
        ])
        
        console.print("[green]Linting fixes applied![/green]")
    
    def release(self):
        """Prepare for release."""
        console.print("[bold]Preparing release...[/bold]")
        return subprocess.run([sys.executable, str(self.scripts_dir / "release.py")]).returncode
    
    def all(self):
        """Run all checks (lint, test, build)."""
        console.print("[bold]Running all checks...[/bold]")
        
        # Run lint
        if self.lint() != 0:
            console.print("[red]Linting failed![/red]")
            return 1
        
        # Run tests
        if self.test() != 0:
            console.print("[red]Tests failed![/red]")
            return 1
        
        # Run build
        if self.build() != 0:
            console.print("[red]Build failed![/red]")
            return 1
        
        console.print("[green]All checks passed![/green]")
        return 0
    
    def setup(self):
        """Set up development environment."""
        console.print("[bold]Setting up development environment...[/bold]")
        import os
        os.chdir(self.project_root)
        
        # Install dependencies
        subprocess.run([
            sys.executable, "-m", "uv", "pip", "install", "-e", ".[all,dev,test]"
        ])
        
        console.print("[green]Development environment set up![/green]")

if __name__ == "__main__":
    fire.Fire(DevCommands)