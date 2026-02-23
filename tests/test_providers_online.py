# this_file: tests/test_providers_online.py

"""
Online integration tests for twat_fs upload providers.

These tests perform REAL uploads to external services and verify round-trip
integrity by downloading the file and comparing checksums.

All tests are marked with ``@pytest.mark.online`` and skipped by default.
Run with::

    pytest -m online tests/test_providers_online.py

Adapted from TO-INTEGRATE/pastebin_tester.py.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from pathlib import Path

import pytest
import requests

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

TEST_FILE = Path(__file__).parent.parent / "src" / "twat_fs" / "data" / "test.jpg"
USER_AGENT = "twat-fs/1.0"
TIMEOUT = 30


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _upload_and_verify(upload_fn: Callable[[Path], str], test_file: Path = TEST_FILE) -> str:
    """
    Generic upload-then-verify helper.

    ``upload_fn`` must accept a Path and return the download URL string.
    The helper then downloads from that URL and compares SHA-256 checksums.
    """
    if not test_file.exists():
        pytest.skip(f"Test file not found: {test_file}")

    original_hash = _sha256(test_file)

    url = upload_fn(test_file)
    assert url, "Upload returned empty URL"
    assert url.startswith("http"), f"Upload returned invalid URL: {url}"

    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Download failed: HTTP {resp.status_code}"

    downloaded_hash = _sha256_bytes(resp.content)
    assert downloaded_hash == original_hash, (
        f"Integrity mismatch: original={original_hash}, downloaded={downloaded_hash}"
    )

    return url


# ---------------------------------------------------------------------------
# Upload functions for each provider
# ---------------------------------------------------------------------------


def _upload_catbox(path: Path) -> str:
    with open(path, "rb") as f:
        resp = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": (path.name, f, "application/octet-stream")},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
    resp.raise_for_status()
    return resp.text.strip()


def _upload_litterbox(path: Path) -> str:
    with open(path, "rb") as f:
        resp = requests.post(
            "https://litterbox.catbox.moe/resources/internals/api.php",
            data={"reqtype": "fileupload", "time": "1h"},
            files={"fileToUpload": (path.name, f, "application/octet-stream")},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
    resp.raise_for_status()
    return resp.text.strip()


def _upload_x0at(path: Path) -> str:
    with open(path, "rb") as f:
        resp = requests.post(
            "https://x0.at/",
            files={"file": (path.name, f, "application/octet-stream")},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
    resp.raise_for_status()
    return resp.text.strip()


def _upload_tmpfilelink(path: Path) -> str:
    with open(path, "rb") as f:
        resp = requests.post(
            "https://tmpfile.link/api/upload",
            files={"file": (path.name, f, "application/octet-stream")},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
    resp.raise_for_status()
    data = resp.json()
    url = str(data.get("downloadLink", ""))
    if not url:
        msg = f"No downloadLink in response: {data}"
        raise ValueError(msg)
    return url


def _upload_tmpfilesorg(path: Path) -> str:
    with open(path, "rb") as f:
        resp = requests.post(
            "https://tmpfiles.org/api/v1/upload",
            files={"file": (path.name, f, "application/octet-stream")},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
    resp.raise_for_status()
    data = resp.json()
    page_url = data.get("data", {}).get("url", "")
    if not page_url:
        msg = f"No data.url in response: {data}"
        raise ValueError(msg)
    # Transform page URL to direct download URL by inserting /dl/
    dl_url = re.sub(r"(https?://tmpfiles\.org)/", r"\1/dl/", page_url, count=1)
    return dl_url


def _upload_www0x0(path: Path) -> str:
    with open(path, "rb") as f:
        resp = requests.post(
            "https://0x0.st",
            files={"file": (path.name, f, "application/octet-stream")},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
    resp.raise_for_status()
    return resp.text.strip()


def _upload_pixeldrain(path: Path) -> str:
    with open(path, "rb") as f:
        content = f.read()
    resp = requests.put(
        f"https://pixeldrain.com/api/file/{path.name}",
        data=content,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/octet-stream",
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    file_id = data.get("id", "")
    if not file_id:
        msg = f"No id in pixeldrain response: {data}"
        raise ValueError(msg)
    return f"https://pixeldrain.com/api/file/{file_id}"


# ---------------------------------------------------------------------------
# Online test class
# ---------------------------------------------------------------------------


@pytest.mark.online
@pytest.mark.slow
class TestProvidersOnline:
    """Online integration tests for upload providers.

    Run with: pytest -m online tests/test_providers_online.py
    """

    def test_catbox_upload_and_verify(self):
        """Upload to catbox.moe and verify integrity."""
        _upload_and_verify(_upload_catbox)

    def test_litterbox_upload_and_verify(self):
        """Upload to litterbox.catbox.moe and verify integrity."""
        _upload_and_verify(_upload_litterbox)

    def test_x0at_upload_and_verify(self):
        """Upload to x0.at and verify integrity."""
        _upload_and_verify(_upload_x0at)

    def test_tmpfilelink_upload_and_verify(self):
        """Upload to tmpfile.link and verify integrity."""
        _upload_and_verify(_upload_tmpfilelink)

    def test_tmpfilesorg_upload_and_verify(self):
        """Upload to tmpfiles.org and verify integrity."""
        _upload_and_verify(_upload_tmpfilesorg)

    def test_www0x0_upload_and_verify(self):
        """Upload to 0x0.st and verify integrity."""
        _upload_and_verify(_upload_www0x0)

    def test_pixeldrain_upload_and_verify(self):
        """Upload to pixeldrain.com and verify integrity."""
        _upload_and_verify(_upload_pixeldrain)


# sendit.sh is single-download, so we test upload-only (no integrity check)
@pytest.mark.online
@pytest.mark.slow
class TestSingleDownloadProviders:
    """Providers that delete files after first download — upload-only tests."""

    def test_senditsh_upload(self):
        """Upload to sendit.sh and verify a URL is returned (no download — single-use link)."""
        if not TEST_FILE.exists():
            pytest.skip(f"Test file not found: {TEST_FILE}")

        with open(TEST_FILE, "rb") as f:
            content = f.read()

        resp = requests.put(
            f"https://sendit.sh/{TEST_FILE.name}",
            data=content,
            headers={"User-Agent": USER_AGENT},
            timeout=60,
        )
        assert resp.status_code == 200, f"sendit.sh upload failed: HTTP {resp.status_code}"

        match = re.search(r"https?://sendit\.sh/\S+", resp.text)
        assert match, f"No URL found in sendit.sh response: {resp.text[:200]}"
        url = match.group(0)
        assert url.startswith("http"), f"Invalid URL: {url}"
