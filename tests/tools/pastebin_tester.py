#!/usr/bin/env python3
# this_file: pastebin_tester.py
"""
Test anonymous file-upload services with a real file, verify round-trip
integrity, collect stats, and update fileshare.toml with findings.

Usage:
    python3 pastebin_tester.py [--file test.zip] [--toml fileshare.toml]
"""

import hashlib
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx
import toml
import tomli_w

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TIMEOUT = 60  # seconds per request
USER_AGENT = "pastebin-tester/1.0"
HEADERS = {"User-Agent": USER_AGENT}


# ---------------------------------------------------------------------------
# Result data
# ---------------------------------------------------------------------------


@dataclass
class TestResult:
    name: str
    status: str = "untested"  # ok, upload_failed, download_failed, integrity_failed, skipped, error
    upload_url: str = ""
    download_url: str = ""
    upload_time_s: float = 0.0
    download_time_s: float = 0.0
    upload_http_status: int = 0
    download_http_status: int = 0
    upload_response_body: str = ""
    file_matches: bool = False
    error: str = ""
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Hash helper
# ---------------------------------------------------------------------------


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def bytes_md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


# ---------------------------------------------------------------------------
# Upload functions — one per service
# ---------------------------------------------------------------------------


def upload_0x0st(client: httpx.Client, filepath: Path) -> TestResult:
    r = TestResult(name="0x0.st")
    with open(filepath, "rb") as f:
        t0 = time.monotonic()
        resp = client.post("https://0x0.st", files={"file": (filepath.name, f, "application/octet-stream")})
        r.upload_time_s = time.monotonic() - t0
    r.upload_http_status = resp.status_code
    r.upload_response_body = resp.text.strip()
    if resp.status_code == 200:
        r.upload_url = resp.text.strip()
        r.download_url = r.upload_url
    return r


def upload_catbox(client: httpx.Client, filepath: Path) -> TestResult:
    r = TestResult(name="catbox.moe")
    with open(filepath, "rb") as f:
        t0 = time.monotonic()
        resp = client.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": (filepath.name, f, "application/octet-stream")},
        )
        r.upload_time_s = time.monotonic() - t0
    r.upload_http_status = resp.status_code
    r.upload_response_body = resp.text.strip()
    if resp.status_code == 200 and resp.text.strip().startswith("http"):
        r.upload_url = resp.text.strip()
        r.download_url = r.upload_url
    return r


def upload_litterbox(client: httpx.Client, filepath: Path) -> TestResult:
    r = TestResult(name="litterbox.catbox.moe")
    with open(filepath, "rb") as f:
        t0 = time.monotonic()
        resp = client.post(
            "https://litterbox.catbox.moe/resources/internals/api.php",
            data={"reqtype": "fileupload", "time": "72h"},
            files={"fileToUpload": (filepath.name, f, "application/octet-stream")},
        )
        r.upload_time_s = time.monotonic() - t0
    r.upload_http_status = resp.status_code
    r.upload_response_body = resp.text.strip()
    if resp.status_code == 200 and resp.text.strip().startswith("http"):
        r.upload_url = resp.text.strip()
        r.download_url = r.upload_url
    return r


def upload_tempsh(client: httpx.Client, filepath: Path) -> TestResult:
    r = TestResult(name="temp.sh")
    with open(filepath, "rb") as f:
        content = f.read()
    t0 = time.monotonic()
    resp = client.put(f"https://temp.sh/{filepath.name}", content=content)
    r.upload_time_s = time.monotonic() - t0
    r.upload_http_status = resp.status_code
    r.upload_response_body = resp.text.strip()
    if resp.status_code == 200 and resp.text.strip().startswith("http"):
        r.upload_url = resp.text.strip()
        r.download_url = r.upload_url
    return r


def upload_pixeldrain(client: httpx.Client, filepath: Path) -> TestResult:
    r = TestResult(name="pixeldrain.com")
    with open(filepath, "rb") as f:
        content = f.read()
    t0 = time.monotonic()
    resp = client.put(
        f"https://pixeldrain.com/api/file/{filepath.name}",
        content=content,
        headers={"Content-Type": "application/octet-stream"},
    )
    r.upload_time_s = time.monotonic() - t0
    r.upload_http_status = resp.status_code
    r.upload_response_body = resp.text.strip()
    if resp.status_code in (200, 201):
        try:
            data = resp.json()
            file_id = data.get("id", "")
            if file_id:
                r.upload_url = f"https://pixeldrain.com/u/{file_id}"
                r.download_url = f"https://pixeldrain.com/api/file/{file_id}"
        except Exception:
            pass
    return r


def upload_putre(client: httpx.Client, filepath: Path) -> TestResult:
    r = TestResult(name="put.re")
    with open(filepath, "rb") as f:
        t0 = time.monotonic()
        resp = client.post("https://api.put.re/upload", files={"file": (filepath.name, f, "application/octet-stream")})
        r.upload_time_s = time.monotonic() - t0
    r.upload_http_status = resp.status_code
    r.upload_response_body = resp.text.strip()[:500]
    if resp.status_code == 200:
        try:
            data = resp.json()
            r.upload_url = data.get("link", "") or data.get("url", "")
            r.download_url = r.upload_url
        except Exception:
            pass
    return r


def upload_x0at(client: httpx.Client, filepath: Path) -> TestResult:
    r = TestResult(name="x0.at")
    with open(filepath, "rb") as f:
        t0 = time.monotonic()
        resp = client.post("https://x0.at/", files={"file": (filepath.name, f, "application/octet-stream")})
        r.upload_time_s = time.monotonic() - t0
    r.upload_http_status = resp.status_code
    r.upload_response_body = resp.text.strip()
    if resp.status_code == 200 and resp.text.strip().startswith("http"):
        r.upload_url = resp.text.strip()
        r.download_url = r.upload_url
    return r


def upload_uguu(client: httpx.Client, filepath: Path) -> TestResult:
    r = TestResult(name="uguu.se")
    with open(filepath, "rb") as f:
        t0 = time.monotonic()
        resp = client.post(
            "https://uguu.se/upload",
            files={"files[]": (filepath.name, f, "application/octet-stream")},
        )
        r.upload_time_s = time.monotonic() - t0
    r.upload_http_status = resp.status_code
    r.upload_response_body = resp.text.strip()[:500]
    if resp.status_code == 200:
        try:
            data = resp.json()
            if isinstance(data, list) and data:
                r.upload_url = data[0].get("url", "")
            elif isinstance(data, dict):
                r.upload_url = data.get("url", "") or data.get("files", [{}])[0].get("url", "")
            r.download_url = r.upload_url
        except Exception:
            # Some versions return plain text URL
            if resp.text.strip().startswith("http"):
                r.upload_url = resp.text.strip()
                r.download_url = r.upload_url
    return r


def upload_senditsh(client: httpx.Client, filepath: Path) -> TestResult:
    r = TestResult(name="sendit.sh")
    r.notes.append("single-download service; verification download will consume the link")
    with open(filepath, "rb") as f:
        content = f.read()
    t0 = time.monotonic()
    resp = client.put(f"https://sendit.sh/{filepath.name}", content=content)
    r.upload_time_s = time.monotonic() - t0
    r.upload_http_status = resp.status_code
    r.upload_response_body = resp.text.strip()[:500]
    if resp.status_code == 200:
        # Response may contain URL directly or embedded in text like "wget https://..."
        url_match = re.search(r"(https?://sendit\.sh/\S+)", resp.text)
        if url_match:
            r.upload_url = url_match.group(1)
            r.download_url = r.upload_url
    return r


def upload_tempfileorg(client: httpx.Client, filepath: Path) -> TestResult:
    r = TestResult(name="tempfile.org")
    with open(filepath, "rb") as f:
        t0 = time.monotonic()
        resp = client.post(
            "https://tempfile.org/api/upload/local",
            data={"expiryHours": "48"},
            files={"files": (filepath.name, f, "application/octet-stream")},
        )
        r.upload_time_s = time.monotonic() - t0
    r.upload_http_status = resp.status_code
    r.upload_response_body = resp.text.strip()[:500]
    if resp.status_code == 200:
        try:
            data = resp.json()
            url = data.get("url", "") or data.get("downloadUrl", "")
            if not url and "data" in data:
                url = data["data"].get("url", "") or data["data"].get("downloadUrl", "")
            # Structure: {"files": [{"id": "...", "name": "...", "url": "..."}]}
            if not url and "files" in data:
                files = data["files"]
                if isinstance(files, list) and files:
                    url = files[0].get("url", "")
                    fname = files[0].get("name", "")
                    # The page URL needs filename appended for direct download
                    if url and fname and not url.endswith(fname):
                        dl_url = url.rstrip("/") + "/" + fname
                    else:
                        dl_url = url
                    r.upload_url = url
                    r.download_url = dl_url
                    return r
            r.upload_url = url
            r.download_url = url
        except Exception:
            pass
    return r


def upload_tmpfilesorg(client: httpx.Client, filepath: Path) -> TestResult:
    r = TestResult(name="tmpfiles.org")
    with open(filepath, "rb") as f:
        t0 = time.monotonic()
        resp = client.post(
            "https://tmpfiles.org/api/v1/upload",
            files={"file": (filepath.name, f, "application/octet-stream")},
        )
        r.upload_time_s = time.monotonic() - t0
    r.upload_http_status = resp.status_code
    r.upload_response_body = resp.text.strip()[:500]
    if resp.status_code == 200:
        try:
            data = resp.json()
            url = data.get("data", {}).get("url", "")
            if url:
                # Convert to direct download URL by inserting /dl/
                r.upload_url = url
                r.download_url = url.replace("tmpfiles.org/", "tmpfiles.org/dl/", 1)
        except Exception:
            pass
    return r


def upload_fileio(client: httpx.Client, filepath: Path) -> TestResult:
    r = TestResult(name="file.io")
    r.notes.append("single-download service; verification download will consume the link")
    # Try multiple known API patterns
    endpoints = ["https://file.io/", "https://file.io/api/v1/upload"]
    for endpoint in endpoints:
        with open(filepath, "rb") as f:
            t0 = time.monotonic()
            resp = client.post(
                endpoint,
                files={"file": (filepath.name, f, "application/octet-stream")},
                headers={"Accept": "application/json"},
            )
            r.upload_time_s = time.monotonic() - t0
        r.upload_http_status = resp.status_code
        r.upload_response_body = resp.text.strip()[:500]
        if resp.status_code == 200:
            try:
                data = resp.json()
                if data.get("success"):
                    r.upload_url = data.get("link", "")
                    r.download_url = r.upload_url
                    return r
            except Exception:
                continue  # HTML response, try next endpoint
    return r


def upload_gofile(client: httpx.Client, filepath: Path) -> TestResult:
    r = TestResult(name="gofile.io")
    # Step 1: get upload server
    try:
        srv_resp = client.get("https://api.gofile.io/servers")
        srv_data = srv_resp.json()
        server = srv_data.get("data", {}).get("servers", [{}])[0].get("name", "")
        if not server:
            r.error = f"Could not get server: {srv_resp.text[:200]}"
            r.status = "upload_failed"
            return r
    except Exception as e:
        r.error = f"Server lookup failed: {e}"
        r.status = "upload_failed"
        return r

    # Step 2: upload
    with open(filepath, "rb") as f:
        t0 = time.monotonic()
        resp = client.post(
            f"https://{server}.gofile.io/uploadFile",
            files={"file": (filepath.name, f, "application/octet-stream")},
        )
        r.upload_time_s = time.monotonic() - t0
    r.upload_http_status = resp.status_code
    r.upload_response_body = resp.text.strip()[:500]
    if resp.status_code == 200:
        try:
            data = resp.json()
            dl_page = data.get("data", {}).get("downloadPage", "")
            file_url = data.get("data", {}).get("directLink", "") or data.get("data", {}).get("fileUrl", "")
            r.upload_url = dl_page or file_url
            r.download_url = file_url or dl_page
            r.notes.append("download page requires JS; direct file link may not work without token")
        except Exception:
            pass
    return r


def upload_tmpfilelink(client: httpx.Client, filepath: Path) -> TestResult:
    r = TestResult(name="tmpfile.link")
    with open(filepath, "rb") as f:
        t0 = time.monotonic()
        resp = client.post(
            "https://tmpfile.link/api/upload",
            files={"file": (filepath.name, f, "application/octet-stream")},
        )
        r.upload_time_s = time.monotonic() - t0
    r.upload_http_status = resp.status_code
    r.upload_response_body = resp.text.strip()[:500]
    if resp.status_code == 200:
        try:
            data = resp.json()
            r.upload_url = data.get("downloadLink", "") or data.get("url", "")
            r.download_url = r.upload_url
        except Exception:
            if resp.text.strip().startswith("http"):
                r.upload_url = resp.text.strip()
                r.download_url = r.upload_url
    return r


# ---------------------------------------------------------------------------
# Download & verify
# ---------------------------------------------------------------------------


def download_and_verify(client: httpx.Client, result: TestResult, expected_md5: str) -> None:
    if not result.download_url:
        result.status = "upload_failed"
        if not result.error:
            result.error = f"No download URL obtained (HTTP {result.upload_http_status})"
        return

    try:
        t0 = time.monotonic()
        resp = client.get(result.download_url, follow_redirects=True)
        result.download_time_s = time.monotonic() - t0
        result.download_http_status = resp.status_code

        if resp.status_code != 200:
            result.status = "download_failed"
            result.error = f"Download HTTP {resp.status_code}"
            return

        got_md5 = bytes_md5(resp.content)
        result.file_matches = got_md5 == expected_md5
        if result.file_matches:
            result.status = "ok"
        else:
            result.status = "integrity_failed"
            result.error = (
                f"MD5 mismatch: expected {expected_md5}, got {got_md5} (downloaded {len(resp.content)} bytes)"
            )
    except Exception as e:
        result.status = "download_failed"
        result.error = str(e)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

UPLOAD_FUNCTIONS = [
    upload_0x0st,
    upload_catbox,
    upload_litterbox,
    upload_tempsh,
    upload_pixeldrain,
    upload_putre,
    upload_x0at,
    upload_uguu,
    upload_senditsh,
    upload_tempfileorg,
    upload_tmpfilesorg,
    upload_fileio,
    upload_gofile,
    upload_tmpfilelink,
]


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def print_report(results: list[TestResult], filepath: Path, expected_md5: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\n{'=' * 78}")
    print(f"  PASTEBIN TESTER REPORT — {now}")
    print(f"  File: {filepath.name} ({filepath.stat().st_size} bytes, MD5: {expected_md5})")
    print(f"{'=' * 78}\n")

    ok = [r for r in results if r.status == "ok"]
    failed = [r for r in results if r.status != "ok"]

    print(f"  PASSED: {len(ok)}/{len(results)}   FAILED: {len(failed)}/{len(results)}\n")

    # Detailed table
    print(f"  {'Service':<28} {'Status':<18} {'Upload(s)':<10} {'DL(s)':<10} {'Match':<6} {'URL'}")
    print(f"  {'-' * 27} {'-' * 17} {'-' * 9} {'-' * 9} {'-' * 5} {'-' * 40}")

    for r in results:
        match_str = "YES" if r.file_matches else "NO"
        status_icon = "OK" if r.status == "ok" else r.status.upper()
        url_display = r.upload_url[:60] if r.upload_url else "(none)"
        print(
            f"  {r.name:<28} {status_icon:<18} {r.upload_time_s:<10.2f} {r.download_time_s:<10.2f} {match_str:<6} {url_display}"
        )

    # Errors section
    if failed:
        print(f"\n  {'─' * 78}")
        print("  ERRORS & DETAILS\n")
        for r in failed:
            print(f"  [{r.name}]")
            print(f"    Status:   {r.status}")
            print(f"    Error:    {r.error}")
            print(f"    HTTP:     upload={r.upload_http_status} download={r.download_http_status}")
            body_preview = r.upload_response_body[:200].replace("\n", " ")
            print(f"    Response: {body_preview}")
            if r.notes:
                print(f"    Notes:    {'; '.join(r.notes)}")
            print()

    # Public URLs section
    print(f"\n  {'─' * 78}")
    print("  PUBLIC DOWNLOAD URLs\n")
    for r in results:
        icon = "[OK]" if r.status == "ok" else "[!!]"
        url = r.upload_url or "(no URL)"
        print(f"  {icon} {r.name:<28} {url}")

    # Speed rankings
    working = [r for r in results if r.upload_time_s > 0]
    if working:
        print(f"\n  {'─' * 78}")
        print("  SPEED RANKINGS (upload time)\n")
        for i, r in enumerate(sorted(working, key=lambda x: x.upload_time_s), 1):
            bar = "#" * max(1, int(r.upload_time_s * 4))
            print(f"  {i:>2}. {r.name:<28} {r.upload_time_s:>6.2f}s  {bar}")

    print(f"\n{'=' * 78}\n")


# ---------------------------------------------------------------------------
# TOML updater
# ---------------------------------------------------------------------------


def update_toml(toml_path: Path, results: list[TestResult], expected_md5: str) -> None:
    with open(toml_path) as f:
        data = toml.load(f)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Build lookup by service name
    result_map: dict[str, TestResult] = {}
    for r in results:
        result_map[r.name] = r

    for svc in data.get("services", []):
        name = svc.get("name", "")
        r = result_map.get(name)
        if not r:
            continue

        # Add/update test_result sub-table
        svc["test_result"] = {
            "tested_at": now,
            "test_file_md5": expected_md5,
            "status": r.status,
            "upload_url": r.upload_url,
            "download_url": r.download_url,
            "upload_time_s": round(r.upload_time_s, 3),
            "download_time_s": round(r.download_time_s, 3),
            "upload_http_status": r.upload_http_status,
            "download_http_status": r.download_http_status,
            "integrity_verified": r.file_matches,
        }
        if r.error:
            svc["test_result"]["error"] = r.error
        if r.notes:
            svc["test_result"]["notes"] = r.notes

        # Update top-level status based on test
        if r.status == "ok":
            svc["status"] = "working"
        elif r.status in ("upload_failed", "download_failed", "integrity_failed"):
            if svc.get("status") == "working":
                svc["status"] = "partial"

    # Write back — use tomli_w for clean output
    with open(toml_path, "wb") as f:
        tomli_w.dump(data, f)

    print(f"  Updated {toml_path} with test results.\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Test anonymous file-upload services")
    parser.add_argument("--file", default="test.zip", help="File to upload (default: test.zip)")
    parser.add_argument("--toml", default="fileshare.toml", help="TOML file to update (default: fileshare.toml)")
    args = parser.parse_args()

    # Resolve paths relative to script directory
    script_dir = Path(__file__).parent
    filepath = Path(args.file)
    if not filepath.is_absolute():
        filepath = script_dir / filepath
    toml_path = Path(args.toml)
    if not toml_path.is_absolute():
        toml_path = script_dir / toml_path

    if not filepath.exists():
        print(f"ERROR: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    expected_md5 = file_md5(filepath)
    print(f"\nFile: {filepath} ({filepath.stat().st_size} bytes)")
    print(f"MD5:  {expected_md5}\n")

    results: list[TestResult] = []

    client = httpx.Client(
        timeout=httpx.Timeout(TIMEOUT, connect=15),
        headers=HEADERS,
        follow_redirects=True,
    )

    for upload_fn in UPLOAD_FUNCTIONS:
        name = upload_fn.__name__.replace("upload_", "")
        print(f"  Testing {name}...", end=" ", flush=True)
        try:
            r = upload_fn(client, filepath)
            if r.upload_url:
                print(f"uploaded ({r.upload_time_s:.1f}s) → verifying...", end=" ", flush=True)
                download_and_verify(client, r, expected_md5)
                icon = "OK" if r.status == "ok" else r.status.upper()
                print(icon)
            else:
                r.status = "upload_failed"
                if not r.error:
                    r.error = f"No URL in response (HTTP {r.upload_http_status})"
                print(f"FAILED — {r.error[:80]}")
        except Exception as e:
            r = TestResult(name=name, status="error", error=str(e))
            print(f"ERROR — {e}")
        results.append(r)

    client.close()

    print_report(results, filepath, expected_md5)

    if toml_path.exists():
        update_toml(toml_path, results, expected_md5)
    else:
        print(f"  TOML file not found at {toml_path}; skipping update.\n")


if __name__ == "__main__":
    main()
