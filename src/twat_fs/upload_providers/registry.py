# this_file: src/twat_fs/upload_providers/registry.py

"""
Provider metadata registry backed by fileshare.toml.

Loads structured metadata about file-sharing services from the bundled
fileshare.toml database. This provides runtime access to max file sizes,
retention periods, upload methods, and test results without hardcoding
these values in each provider module.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef,unused-ignore]

from loguru import logger

_TOML_PATH = Path(__file__).parent.parent / "data" / "fileshare.toml"


@dataclass(frozen=True)
class TestResultInfo:
    """Test result data from fileshare.toml."""

    tested_at: str = ""
    test_file_md5: str = ""
    status: str = "untested"
    upload_url: str = ""
    download_url: str = ""
    upload_time_s: float = 0.0
    download_time_s: float = 0.0
    upload_http_status: int = 0
    download_http_status: int = 0
    integrity_verified: bool = False
    error: str = ""


@dataclass(frozen=True)
class ServiceInfo:
    """Metadata for a single file-sharing service."""

    name: str
    rank: int
    tier: str  # recommended, usable, partial, dead
    status: str  # working, partial, changed, unreliable, down, dead
    url: str
    max_size: str = ""
    max_size_bytes: int | None = None
    retention: str = ""
    retention_min_days: float | None = None
    retention_max_days: float | None = None
    auth_required: bool = False
    method: str = "POST"  # POST, PUT, two-step, browser-only
    upload_curl: str = ""
    download_curl: str = ""
    response_format: str = "text"
    features: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    notes: str = ""
    single_download: bool = False
    open_source_url: str = ""
    test_result: TestResultInfo | None = None


# Module-level cache
_registry_cache: dict[str, ServiceInfo] | None = None


def _parse_test_result(data: dict[str, object]) -> TestResultInfo:
    """Parse a test_result table from the TOML data."""
    return TestResultInfo(
        tested_at=str(data.get("tested_at", "")),
        test_file_md5=str(data.get("test_file_md5", "")),
        status=str(data.get("status", "untested")),
        upload_url=str(data.get("upload_url", "")),
        download_url=str(data.get("download_url", "")),
        upload_time_s=float(data.get("upload_time_s", 0.0)),  # type: ignore[arg-type]
        download_time_s=float(data.get("download_time_s", 0.0)),  # type: ignore[arg-type]
        upload_http_status=int(data.get("upload_http_status", 0)),  # type: ignore[call-overload]
        download_http_status=int(data.get("download_http_status", 0)),  # type: ignore[call-overload]
        integrity_verified=bool(data.get("integrity_verified", False)),
        error=str(data.get("error", "")),
    )


def _parse_service(data: dict[str, object]) -> ServiceInfo:
    """Parse a single [[services]] entry from the TOML data."""
    test_result_data = data.get("test_result")
    test_result = _parse_test_result(test_result_data) if isinstance(test_result_data, dict) else None

    features_raw = data.get("features", [])
    features = list(features_raw) if isinstance(features_raw, list) else []

    caveats_raw = data.get("caveats", [])
    caveats = list(caveats_raw) if isinstance(caveats_raw, list) else []

    return ServiceInfo(
        name=str(data.get("name", "")),
        rank=int(data.get("rank", 999)),  # type: ignore[call-overload]
        tier=str(data.get("tier", "unknown")),
        status=str(data.get("status", "unknown")),
        url=str(data.get("url", "")),
        max_size=str(data.get("max_size", "")),
        max_size_bytes=int(data["max_size_bytes"]) if "max_size_bytes" in data else None,  # type: ignore[call-overload]
        retention=str(data.get("retention", "")),
        retention_min_days=float(data["retention_min_days"]) if "retention_min_days" in data else None,  # type: ignore[arg-type]
        retention_max_days=float(data["retention_max_days"]) if "retention_max_days" in data else None,  # type: ignore[arg-type]
        auth_required=bool(data.get("auth_required", False)),
        method=str(data.get("method", "POST")),
        upload_curl=str(data.get("upload_curl", "")),
        download_curl=str(data.get("download_curl", "")),
        response_format=str(data.get("response_format", "text")),
        features=[str(f) for f in features],
        caveats=[str(c) for c in caveats],
        notes=str(data.get("notes", "")),
        single_download=bool(data.get("single_download", False)),
        open_source_url=str(data.get("open_source_url", "")),
        test_result=test_result,
    )


def load_registry(toml_path: Path | None = None) -> dict[str, ServiceInfo]:
    """
    Load service metadata from fileshare.toml.

    Returns a dict keyed by service name (e.g. "catbox.moe", "x0.at").
    Results are cached after first load.

    Args:
        toml_path: Optional path to the TOML file. Defaults to the bundled
                   ``src/twat_fs/data/fileshare.toml``.

    Returns:
        Dictionary mapping service name to ServiceInfo.
    """
    global _registry_cache  # noqa: PLW0603

    if _registry_cache is not None and toml_path is None:
        return _registry_cache

    path = toml_path or _TOML_PATH
    if not path.exists():
        logger.warning("fileshare.toml not found at {}", path)
        return {}

    with open(path, "rb") as f:
        raw = tomllib.load(f)

    services_raw = raw.get("services", [])
    if not isinstance(services_raw, list):
        logger.warning("Expected 'services' to be a list in {}", path)
        return {}

    registry: dict[str, ServiceInfo] = {}
    for entry in services_raw:
        if not isinstance(entry, dict):
            continue
        info = _parse_service(entry)
        registry[info.name] = info

    if toml_path is None:
        _registry_cache = registry

    logger.debug("Loaded {} services from registry", len(registry))
    return registry


def get_service_info(name: str) -> ServiceInfo | None:
    """
    Get metadata for a specific service by name.

    Args:
        name: Service name as it appears in fileshare.toml (e.g. "x0.at", "catbox.moe").

    Returns:
        ServiceInfo if found, None otherwise.
    """
    registry = load_registry()
    return registry.get(name)


def get_verified_services() -> list[ServiceInfo]:
    """
    Get all services whose last test had integrity_verified=True.

    Returns:
        List of ServiceInfo objects sorted by rank.
    """
    registry = load_registry()
    return sorted(
        [s for s in registry.values() if s.test_result and s.test_result.integrity_verified],
        key=lambda s: s.rank,
    )


def get_services_by_tier(tier: str) -> list[ServiceInfo]:
    """
    Get all services in a specific tier.

    Args:
        tier: One of "recommended", "usable", "partial", "dead".

    Returns:
        List of ServiceInfo objects sorted by rank.
    """
    registry = load_registry()
    return sorted(
        [s for s in registry.values() if s.tier == tier],
        key=lambda s: s.rank,
    )
