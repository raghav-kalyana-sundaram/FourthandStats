"""Data download module — fetches from nflverse and writes per-season parquets."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import polars as pl
from tqdm import tqdm

from fourthandstats.data.manifest import update_manifest_after_download
from fourthandstats.data.sources.source_registry import REGISTRY, SourceDef, get_source
from fourthandstats.utils.logging import get_logger
from fourthandstats.utils.paths import RAW_DIR

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _season_path(dataset: str, season: int) -> Path:
    return RAW_DIR / dataset / f"{dataset}_{season}.parquet"


def _static_path(dataset: str) -> Path:
    return RAW_DIR / dataset / f"{dataset}.parquet"


def _write_atomic(df: pl.DataFrame, dest: Path) -> None:
    """Write a Polars DataFrame to parquet atomically (tmp → rename)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".parquet.tmp")
    df.write_parquet(tmp)
    tmp.rename(dest)


def _season_exists(dataset: str, season: int) -> bool:
    return _season_path(dataset, season).exists()


def _static_exists(dataset: str) -> bool:
    return _static_path(dataset).exists()


# ---------------------------------------------------------------------------
# Per-dataset download functions
# ---------------------------------------------------------------------------


def download_seasonal(
    dataset: str,
    seasons: list[int],
    force: bool = False,
    dry_run: bool = False,
) -> tuple[list[Path], int]:
    """Download a seasonal dataset, one parquet file per season.

    Returns (list of paths written, total rows written).
    """
    source = get_source(dataset)
    if not source.seasonal:
        raise ValueError(f"'{dataset}' is a static dataset, use download_static()")

    to_download = [s for s in seasons if force or not _season_exists(dataset, s)]
    already_present = [s for s in seasons if not force and _season_exists(dataset, s)]

    if already_present:
        logger.info(
            "[%s] skipping seasons already on disk: %s (use --force to re-download)",
            dataset,
            already_present,
        )

    if not to_download:
        logger.info("[%s] all requested seasons already present", dataset)
        # Return existing paths, recount rows
        paths = [_season_path(dataset, s) for s in seasons]
        rows = sum(pl.read_parquet(p).height for p in paths if p.exists())
        return paths, rows

    if dry_run:
        for s in to_download:
            print(f"  [DRY RUN] would download {dataset} season {s}")
        return [], 0

    written_paths: list[Path] = []
    total_rows = 0

    with tqdm(to_download, desc=f"{dataset}", unit="season", file=sys.stdout, leave=True) as pbar:
        for season in pbar:
            pbar.set_postfix(season=season)
            logger.debug("[%s] fetching season %d...", dataset, season)
            try:
                df = source.fetch_fn([season])
                if df is None or df.is_empty():
                    logger.warning("[%s] season %d returned empty data — skipping", dataset, season)
                    continue

                dest = _season_path(dataset, season)
                _write_atomic(df, dest)

                row_count = df.height
                total_rows += row_count
                written_paths.append(dest)
                logger.info("[%s] season %d: %d rows → %s", dataset, season, row_count, dest)

            except Exception as exc:
                logger.error("[%s] season %d failed: %s", dataset, season, exc)
                # Don't corrupt existing file — skip this season but continue
                continue

    # Include already-present seasons in the manifest update
    all_seasons_with_data = sorted(
        {s for s in seasons if _season_exists(dataset, s)}
    )
    if all_seasons_with_data:
        all_rows = sum(
            pl.read_parquet(_season_path(dataset, s)).height
            for s in all_seasons_with_data
        )
        update_manifest_after_download(dataset, all_seasons_with_data, all_rows)

    return written_paths, total_rows


def download_static(
    dataset: str,
    force: bool = False,
    dry_run: bool = False,
) -> tuple[Optional[Path], int]:
    """Download a static (non-seasonal) dataset.

    Returns (path written or None, row count).
    """
    source = get_source(dataset)
    if source.seasonal:
        raise ValueError(f"'{dataset}' is a seasonal dataset, use download_seasonal()")

    dest = _static_path(dataset)
    if dest.exists() and not force:
        logger.info("[%s] already on disk, skipping (use --force to re-download)", dataset)
        rows = pl.read_parquet(dest).height
        update_manifest_after_download(dataset, [], rows)
        return dest, rows

    if dry_run:
        print(f"  [DRY RUN] would download static dataset {dataset}")
        return None, 0

    logger.info("[%s] fetching...", dataset)
    try:
        df = source.fetch_fn()
        if df is None or df.is_empty():
            logger.warning("[%s] returned empty data", dataset)
            return None, 0

        _write_atomic(df, dest)
        rows = df.height
        update_manifest_after_download(dataset, [], rows)
        logger.info("[%s] %d rows → %s", dataset, rows, dest)
        return dest, rows

    except Exception as exc:
        logger.error("[%s] failed: %s", dataset, exc)
        return None, 0


# ---------------------------------------------------------------------------
# Convenience wrappers (called by scripts/update_data.py)
# ---------------------------------------------------------------------------


def download_all_mvp(
    seasons: list[int],
    force: bool = False,
    dry_run: bool = False,
) -> None:
    """Download the MVP dataset set needed to build initial metrics."""
    from fourthandstats.data.sources.source_registry import MVP_DATASETS

    print(f"\nDownloading MVP datasets for seasons {seasons}...\n")

    for dataset in MVP_DATASETS:
        source = REGISTRY[dataset]
        if source.seasonal:
            download_seasonal(dataset, seasons, force=force, dry_run=dry_run)
        else:
            download_static(dataset, force=force, dry_run=dry_run)

    print("\nDownload complete.\n")


def download_datasets(
    datasets: list[str],
    seasons: list[int],
    force: bool = False,
    dry_run: bool = False,
) -> None:
    """Download specific named datasets."""
    for dataset in datasets:
        source = get_source(dataset)
        if source.seasonal:
            download_seasonal(dataset, seasons, force=force, dry_run=dry_run)
        else:
            download_static(dataset, force=force, dry_run=dry_run)
