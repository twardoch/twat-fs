"""Smoke tests for the twat_fs package contract."""
# this_file: tests/test_twat_fs.py

from __future__ import annotations

import subprocess
import sys
from importlib import metadata

import twat_fs


def test_version():
    """Verify package exposes version."""
    assert twat_fs.__version__


def test_public_contract_exports() -> None:
    """The package exposes the public API used by callers and the twat host."""
    assert callable(twat_fs.main)
    assert "__version__" in twat_fs.__all__
    assert "main" in twat_fs.__all__
    assert "upload_file" in twat_fs.__all__
    assert "PROVIDERS_PREFERENCE" in twat_fs.__all__


def test_installed_entry_points() -> None:
    """Installed metadata exposes the direct CLI and twat plugin entry."""
    console_scripts = metadata.entry_points(group="console_scripts")
    scripts = {entry_point.name: entry_point.value for entry_point in console_scripts}
    assert scripts["twat-fs"] == "twat_fs:main"

    plugin_entries = metadata.entry_points(group="twat.plugins")
    plugins = {entry_point.name: entry_point.value for entry_point in plugin_entries}
    assert plugins["fs"] == "twat_fs"


def test_python_module_help_smoke() -> None:
    """`python -m twat_fs --help` reaches the provider CLI."""
    result = subprocess.run(
        [sys.executable, "-m", "twat_fs", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "upload" in output
