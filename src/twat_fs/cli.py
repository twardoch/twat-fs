#!/usr/bin/env -S uv run
# /// script
# dependencies = ["fire", "loguru", "rich"]
# ///
# this_file: src/twat_fs/cli.py

"""
Command-line interface for twat-fs package.
"""

from __future__ import annotations

import hashlib
import os
import sys
from importlib import metadata
from pathlib import Path

import fire
import requests
from loguru import logger
from rich.console import Console
from rich.table import Table

from twat_fs.upload import (
    PROVIDERS_PREFERENCE,
    setup_provider as _setup_provider,
    setup_providers as _setup_providers,
    upload_file as _upload_file,
    UploadOptions,
)

logger.remove()
_DEFAULT_LOG_LEVEL = os.getenv("LOGURU_LEVEL", "WARNING").upper()

logger.add(
    sys.stderr,
    level=_DEFAULT_LOG_LEVEL,
    format="<red>Error: {message}</red>",
    filter=lambda record: record["level"].no >= logger.level("WARNING").no,
)


def _enable_verbose_logging() -> None:
    """Enable INFO-level logging to stderr for verbose mode."""
    logger.add(
        sys.stderr,
        level="INFO",
        format="{message}",
        filter=lambda record: record["level"].no < logger.level("WARNING").no,
    )


def _verify_download(url: str, local_path: Path) -> None:
    """Download the file from url and verify it matches local_path by SHA-256.

    Raises RuntimeError on mismatch or download failure.
    """
    with open(local_path, "rb") as f:
        local_hash = hashlib.sha256(f.read()).hexdigest()

    response = requests.get(url, timeout=60, allow_redirects=True, headers={"User-Agent": "twat-fs/1.0"})
    if response.status_code != 200:
        msg = f"Download check failed: HTTP {response.status_code}"
        raise RuntimeError(msg)
    remote_hash = hashlib.sha256(response.content).hexdigest()
    if remote_hash != local_hash:
        msg = f"Download check failed: hash mismatch (local={local_hash}, remote={remote_hash})"
        raise RuntimeError(msg)


def parse_provider_list(provider: str) -> list[str] | None:
    """Parse a provider list string like '[s3,dropbox]' into a list."""
    if provider.startswith("[") and provider.endswith("]"):
        try:
            return [p.strip() for p in provider[1:-1].split(",")]
        except Exception:
            return None
    return None


class UploadProviderCommands:
    """Commands for managing upload providers."""

    def _display_single_provider_status(self, provider_id: str, *, online: bool, console: Console) -> None:
        with console.status("[cyan]Testing provider...[/cyan]"):
            result = _setup_provider(provider_id, verbose=True, online=online)
            if result.success:
                console.print(f"\n[green]Provider {provider_id} is ready to use[/green]")
                if result.help_info.get("max_size"):
                    console.print(f"  Max Size: {result.help_info['max_size']}")
                if result.help_info.get("retention"):
                    console.print(f"  Retention: {result.help_info['retention']}")
                if result.help_info.get("auth_required") and result.help_info["auth_required"] != "None":
                    console.print(f"  Auth: {result.help_info['auth_required']}")
                if online and result.timing:
                    console.print(f"\n[cyan]Online test time: {result.timing.get('total_duration', 0.0):.2f}s[/cyan]")
            else:
                console.print(f"\n[red]Provider {provider_id} is not ready[/red]")
                console.print(f"\n[yellow]Reason:[/yellow] {result.explanation}")
                console.print("\n[yellow]Setup Instructions:[/yellow]")
                console.print(result.help_info.get("setup", "No setup instructions available"))

    def _display_all_providers_status_table(self, *, online: bool, console: Console) -> None:
        table = Table(title="Provider Setup Status", show_lines=True)
        table.add_column("Provider", no_wrap=True)
        table.add_column("Status", no_wrap=True)
        table.add_column("Max Size", no_wrap=True)
        table.add_column("Retention", no_wrap=True)
        table.add_column("Auth", no_wrap=True)
        if online:
            table.add_column("Time (s)", justify="right", no_wrap=True)
        table.add_column("Details", width=50)

        with console.status("[cyan]Testing providers...[/cyan]") as _:
            results = _setup_providers(verbose=True, online=online)

            ready_providers = []
            not_ready_providers = []

            for provider, info in results.items():
                if provider.lower() == "simple":
                    continue

                time_metric = info.timing.get("total_duration", float("inf")) if info.timing else float("inf")
                if info.success:
                    ready_providers.append((provider, info, time_metric))
                else:
                    not_ready_providers.append((provider, info, time_metric))

            ready_providers.sort(key=lambda x: x[2])
            not_ready_providers.sort(key=lambda x: x[0])

            sorted_providers_info = [(p, i) for p, i, _ in ready_providers] + [
                (p, i) for p, i, _ in not_ready_providers
            ]

            for provider, info in sorted_providers_info:
                current_status = "[green]Ready[/green]" if info.success else "[red]Not Ready[/red]"
                max_size = info.help_info.get("max_size", "")
                retention = info.help_info.get("retention", "")
                auth = info.help_info.get("auth_required", "")
                if auth == "None":
                    auth = ""

                details = info.explanation
                if info.help_info.get("setup"):
                    details = f"{details}\n{info.help_info['setup']}"

                if online:
                    time_val = ""
                    if info.timing and info.timing.get("total_duration") is not None:
                        time_val = f"{info.timing.get('total_duration', 0.0):.2f}"
                    row = [
                        provider,
                        current_status,
                        max_size,
                        retention,
                        auth,
                        time_val,
                        details,
                    ]
                else:
                    row = [provider, current_status, max_size, retention, auth, details]
                table.add_row(*row)

        console.print("\n")
        console.print(table)

    def status(self, provider_id: str | None = None, *, online: bool = False) -> None:
        """
        Show provider setup status.

        Args:
            provider_id: Optional provider ID to show status info for.
            online: If True, run online tests to verify provider functionality.
        """
        console = Console(stderr=True)

        if provider_id:
            self._display_single_provider_status(provider_id, console=console, online=online)
        else:
            self._display_all_providers_status_table(console=console, online=online)

    def list(self, *, online: bool = False) -> None:
        """List all available (ready) provider IDs, one per line. If --online is provided, run online tests.
        In online mode, reconfigure logger so that info messages are printed to stderr."""
        if online:
            logger.remove()
            logger.add(sys.stderr, level="INFO", format="{message}")

        active_providers = []

        for provider in PROVIDERS_PREFERENCE:
            if provider.lower() == "simple":
                continue
            result = _setup_provider(provider, verbose=False, online=online)
            if result.success:
                active_providers.append(provider)

        sys.exit(0)


class TwatFS:
    """
    A robust and extensible file upload utility with support for multiple storage providers.

    Commands:
        upload              Upload a file using configured providers
        upload_provider    Manage upload providers (status, list)
    """

    def __init__(self) -> None:
        self.upload_provider = UploadProviderCommands()

    def version(self) -> None:
        """Show version information."""
        try:
            version = metadata.version("twat-fs")
            print(f"twat-fs {version}")
        except metadata.PackageNotFoundError:
            print("twat-fs (version unknown)")

    def upload(
        self,
        file_path: str | Path,
        provider: str | list[str] = PROVIDERS_PREFERENCE,
        remote_path: str | None = None,
        *,
        unique: bool = False,
        force: bool = False,
        fragile: bool = False,
        verbose: bool = False,
        no_check: bool = False,
    ) -> str:
        """
        Upload a file using the specified provider(s) with automatic fallback.

        Args:
            file_path: Path to the file to upload
            provider: Provider(s) to use for upload. Can be a single provider or a list
            unique: Add timestamp to filename to ensure uniqueness
            force: Overwrite existing files if they exist
            remote_path: Custom remote path/prefix (provider-specific)
            fragile: If True, fail immediately without trying fallback providers
            verbose: If True, emit progress/timing info to stderr
            no_check: If True, skip the post-upload SHA-256 download verification

        Returns:
            URL of the uploaded file
        """
        if verbose:
            _enable_verbose_logging()

        try:
            if isinstance(provider, str):
                providers = parse_provider_list(provider)
                if providers is not None:
                    provider = providers

            path = Path(file_path)
            if not path.exists():
                logger.error(f"File not found: {file_path}")
                sys.exit(1)

            provider_list = [provider] if isinstance(provider, str) else list(provider)

            if verbose:
                size = path.stat().st_size
                print(
                    f"Uploading {path} ({size:,} bytes) via {','.join(provider_list)}...",
                    file=sys.stderr,
                    flush=True,
                )

            if no_check:
                options = UploadOptions(
                    remote_path=None,
                    unique=unique,
                    force=force,
                    upload_path=remote_path,
                    fragile=fragile,
                )
                return _upload_file(file_path, provider=provider, options=options)

            # default: try providers one-by-one, verify each, fall through on mismatch
            last_error: str = "no providers attempted"
            for single in provider_list:
                try:
                    single_options = UploadOptions(
                        remote_path=None,
                        unique=unique,
                        force=force,
                        upload_path=remote_path,
                        fragile=True,
                    )
                    url = _upload_file(file_path, provider=[single], options=single_options)
                except Exception as e:
                    last_error = f"{single}: upload failed: {e}"
                    logger.warning(last_error)
                    if fragile:
                        break
                    continue
                logger.info(f"Verifying download from {url}...")
                try:
                    _verify_download(url, path)
                except Exception as e:
                    last_error = f"{single}: {e}"
                    logger.warning(f"Verification failed for {single}, trying next provider: {e}")
                    if fragile:
                        break
                    continue
                logger.info(f"Verification OK for {single}: SHA-256 matches")
                return url

            logger.error(f"Upload with verification failed: {last_error}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            sys.exit(1)


def main() -> None:
    """Entry point for the CLI."""
    if __name__ == "__main__":
        fire.Fire(TwatFS)
    else:
        fire.Fire(TwatFS())


def main_2url() -> None:
    """Entry point equivalent to `twat-fs upload` with the same API."""
    fire.Fire(TwatFS().upload, name="file2url")


upload_file = TwatFS().upload
setup_provider = TwatFS().upload_provider.status


def setup_providers() -> None:
    return TwatFS().upload_provider.status(None)


if __name__ == "__main__":
    main()
