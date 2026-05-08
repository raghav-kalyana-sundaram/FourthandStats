"""Update data — download raw NFL data from nflverse.

Usage:
    python scripts/update_data.py --seasons 2024 2025
    python scripts/update_data.py --seasons 1999-2025
    python scripts/update_data.py --current-season
    python scripts/update_data.py --seasons 2024 2025 --datasets pbp,schedules
    python scripts/update_data.py --seasons 2024 2025 --dry-run
    python scripts/update_data.py --seasons 2024 2025 --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project src/ to path so the package is importable without `pip install -e .`
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fourthandstats.data.download import download_all_mvp, download_datasets
from fourthandstats.data.manifest import load_manifest
from fourthandstats.data.sources.nflverse_source import get_current_season
from fourthandstats.data.sources.source_registry import ALL_DATASETS, MVP_DATASETS
from fourthandstats.utils.paths import ensure_dirs
from fourthandstats.utils.time import parse_season_range


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Download NFL data from nflverse",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python scripts/update_data.py --current-season
  python scripts/update_data.py --seasons 2024 2025
  python scripts/update_data.py --seasons 1999-2025
  python scripts/update_data.py --seasons 2025 --datasets pbp,schedules
  python scripts/update_data.py --seasons 2025 --dry-run
  python scripts/update_data.py --seasons 2024 2025 --force
        """,
    )

    season_group = p.add_mutually_exclusive_group(required=True)
    season_group.add_argument(
        "--seasons",
        nargs="+",
        help="Season(s) or range. e.g. 2024 2025  or  1999-2025",
    )
    season_group.add_argument(
        "--current-season",
        action="store_true",
        help="Download the current (or most recently completed) season",
    )

    p.add_argument(
        "--datasets",
        help=f"Comma-separated datasets to download (default: MVP set). "
             f"Available: {', '.join(ALL_DATASETS)}",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be downloaded without actually downloading",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if parquet files already exist on disk",
    )
    p.add_argument(
        "--status",
        action="store_true",
        help="Print current manifest status and exit",
    )

    return p.parse_args()


def print_status() -> None:
    manifest = load_manifest()
    print("\n=== FourthandStats — Data Status ===\n")
    if not manifest.loaded_seasons:
        print("No data downloaded yet.")
        print(f"\nRun: python scripts/update_data.py --seasons 2024 2025\n")
        return

    print(f"Loaded seasons : {manifest.loaded_seasons}")
    print(f"Latest season  : {manifest.latest_loaded_season}")
    print(f"Last update    : {manifest.last_data_update}")
    print(f"Last rebuild   : {manifest.last_metric_rebuild or 'never'}")
    print()
    print("Datasets:")
    for name, status in manifest.datasets.items():
        mark = "✓" if status.available else "✗"
        seasons_str = f"seasons={status.seasons}" if status.seasons else "(static)"
        rows_str = f"{status.row_count:,} rows" if status.row_count else "?"
        print(f"  {mark} {name:<20} {rows_str:<15} {seasons_str}")
    if manifest.warnings:
        print("\nWarnings:")
        for w in manifest.warnings:
            print(f"  ⚠ {w}")
    print()


def main() -> int:
    args = parse_args()
    ensure_dirs()

    if args.status:
        print_status()
        return 0

    # Resolve season list
    if args.current_season:
        current = get_current_season()
        seasons = [current]
        print(f"Current season detected: {current}")
    else:
        # Parse each token — could be "2025", "2024 2025", or "1999-2025"
        raw = " ".join(args.seasons)
        seasons = parse_season_range(raw)

    print(f"Seasons to process: {seasons}")

    if args.dry_run:
        print("[DRY RUN mode — nothing will be downloaded]\n")

    # Resolve dataset list
    if args.datasets:
        datasets = [d.strip() for d in args.datasets.split(",")]
        unknown = [d for d in datasets if d not in ALL_DATASETS]
        if unknown:
            print(f"ERROR: Unknown datasets: {unknown}")
            print(f"Available: {ALL_DATASETS}")
            return 1
        download_datasets(
            datasets=datasets,
            seasons=seasons,
            force=args.force,
            dry_run=args.dry_run,
        )
    else:
        download_all_mvp(seasons=seasons, force=args.force, dry_run=args.dry_run)

    if not args.dry_run:
        print_status()

    return 0


if __name__ == "__main__":
    sys.exit(main())
