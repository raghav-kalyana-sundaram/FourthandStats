"""Path resolution utilities — all paths relative to project root."""

from pathlib import Path

# Project root is three levels up from this file: src/fourthandstats/utils/paths.py
PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw" / "nflverse"
PROCESSED_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"
MANIFESTS_DIR = DATA_DIR / "manifests"

CONFIG_DIR = PROJECT_ROOT / "config"
SAVED_VIEWS_DIR = PROJECT_ROOT / "saved_views"
EXPORTS_DIR = PROJECT_ROOT / "exports"
LOGS_DIR = PROJECT_ROOT / "logs"


def ensure_dirs() -> None:
    """Create all runtime directories if they don't exist."""
    for d in (RAW_DIR, PROCESSED_DIR, CACHE_DIR, MANIFESTS_DIR, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    for sub in ("charts", "reports", "tables"):
        (EXPORTS_DIR / sub).mkdir(parents=True, exist_ok=True)


def raw_season_path(dataset: str, season: int) -> Path:
    """Return the expected path for a raw per-season parquet file."""
    return RAW_DIR / dataset / f"{dataset}_{season}.parquet"


def raw_static_path(dataset: str) -> Path:
    """Return the expected path for a raw non-seasonal parquet file."""
    return RAW_DIR / dataset / f"{dataset}.parquet"


def processed_path(name: str) -> Path:
    """Return the expected path for a processed/derived parquet table."""
    return PROCESSED_DIR / f"{name}.parquet"
