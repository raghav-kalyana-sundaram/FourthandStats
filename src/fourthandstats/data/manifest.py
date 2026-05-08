"""Data and build manifests — pydantic models + read/write helpers."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from fourthandstats.utils.paths import MANIFESTS_DIR
from fourthandstats.utils.time import utc_now


# ---------------------------------------------------------------------------
# Data manifest
# ---------------------------------------------------------------------------


class DatasetStatus(BaseModel):
    available: bool = False
    seasons: list[int] = Field(default_factory=list)
    row_count: Optional[int] = None
    last_updated: Optional[datetime] = None
    reason: Optional[str] = None  # when unavailable, explain why


class DataManifest(BaseModel):
    loaded_seasons: list[int] = Field(default_factory=list)
    latest_loaded_season: Optional[int] = None
    latest_loaded_week: Optional[int] = None
    includes_playoffs: bool = False
    last_data_update: Optional[datetime] = None
    last_metric_rebuild: Optional[datetime] = None
    datasets: dict[str, DatasetStatus] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


_DATA_MANIFEST_PATH = MANIFESTS_DIR / "data_manifest.json"


def load_manifest() -> DataManifest:
    """Load the data manifest from disk, returning a blank one if missing."""
    if not _DATA_MANIFEST_PATH.exists():
        return DataManifest()
    try:
        raw = json.loads(_DATA_MANIFEST_PATH.read_text())
        return DataManifest.model_validate(raw)
    except Exception:
        return DataManifest()


def save_manifest(manifest: DataManifest) -> None:
    """Write the data manifest atomically."""
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _DATA_MANIFEST_PATH.with_suffix(".json.tmp")
    tmp.write_text(manifest.model_dump_json(indent=2))
    tmp.rename(_DATA_MANIFEST_PATH)


def update_manifest_after_download(
    dataset: str,
    seasons: list[int],
    row_count: int,
) -> DataManifest:
    """Update and persist the manifest after a successful dataset download."""
    manifest = load_manifest()

    status = manifest.datasets.get(dataset, DatasetStatus())
    status.available = True
    status.seasons = sorted(set(status.seasons) | set(seasons))
    status.row_count = row_count
    status.last_updated = utc_now()
    status.reason = None
    manifest.datasets[dataset] = status

    # Recompute aggregate loaded_seasons from all seasonal datasets
    all_seasons: set[int] = set()
    for ds_status in manifest.datasets.values():
        all_seasons.update(ds_status.seasons)
    manifest.loaded_seasons = sorted(all_seasons)
    if manifest.loaded_seasons:
        manifest.latest_loaded_season = max(manifest.loaded_seasons)
    manifest.last_data_update = utc_now()

    save_manifest(manifest)
    return manifest


# ---------------------------------------------------------------------------
# Build manifest
# ---------------------------------------------------------------------------


class TableBuildStatus(BaseModel):
    row_count: int = 0
    build_time: Optional[datetime] = None
    source_files: list[str] = Field(default_factory=list)
    source_hash: Optional[str] = None


class BuildManifest(BaseModel):
    last_build: Optional[datetime] = None
    tables: dict[str, TableBuildStatus] = Field(default_factory=dict)


_BUILD_MANIFEST_PATH = MANIFESTS_DIR / "build_manifest.json"


def load_build_manifest() -> BuildManifest:
    if not _BUILD_MANIFEST_PATH.exists():
        return BuildManifest()
    try:
        raw = json.loads(_BUILD_MANIFEST_PATH.read_text())
        return BuildManifest.model_validate(raw)
    except Exception:
        return BuildManifest()


def save_build_manifest(manifest: BuildManifest) -> None:
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _BUILD_MANIFEST_PATH.with_suffix(".json.tmp")
    tmp.write_text(manifest.model_dump_json(indent=2))
    tmp.rename(_BUILD_MANIFEST_PATH)


def update_build_manifest(table: str, row_count: int, source_files: list[Path]) -> BuildManifest:
    manifest = load_build_manifest()
    manifest.tables[table] = TableBuildStatus(
        row_count=row_count,
        build_time=utc_now(),
        source_files=[str(f) for f in source_files],
    )
    manifest.last_build = utc_now()
    save_build_manifest(manifest)
    return manifest
