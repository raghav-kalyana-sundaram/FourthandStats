"""Rebuild all derived metric tables from raw parquets.

Workflow:
  1. Build derived tables to data/processed/.tmp/
  2. Run validation against .tmp/ outputs
  3. On pass: swap .tmp/ → final
  4. On fail: keep previous, log, exit 1
  5. Update build_manifest.json

Usage:
    python scripts/rebuild_metrics.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fourthandstats.data.manifest import update_build_manifest
from fourthandstats.data.schema import build_schema
from fourthandstats.data.transform import build_all_tables
from fourthandstats.data.quality import validate_team_season_summary, validate_player_season_summary
from fourthandstats.metrics.percentiles import build_team_percentiles
from fourthandstats.metrics.ratings import build_team_ratings
from fourthandstats.utils.paths import PROCESSED_DIR, ensure_dirs, processed_path
from fourthandstats.utils.logging import get_logger

logger = get_logger(__name__)


def main() -> int:
    ensure_dirs()

    print("\n=== FourthandStats — Rebuilding Metrics ===\n")

    # Step 1: Build derived tables
    print("Step 1/4: Building derived tables...")
    row_counts = build_all_tables()
    for table, rows in row_counts.items():
        print(f"  ✓ {table}: {rows:,} rows")

    # Step 2: Build percentiles
    print("\nStep 2/4: Computing percentiles...")
    pct_rows = build_team_percentiles()
    print(f"  ✓ metric_percentiles: {pct_rows:,} rows")

    # Step 3: Build ratings
    print("\nStep 3/4: Computing composite ratings...")
    rating_rows = build_team_ratings()
    print(f"  ✓ team ratings added: {rating_rows:,} rows")

    # Step 4: Validate
    print("\nStep 4/4: Validating outputs...")
    v_team = validate_team_season_summary()
    v_player = validate_player_season_summary()

    print(v_team.summary())
    print(v_player.summary())

    if not v_team.passed or not v_player.passed:
        print("\nERROR: Validation failed — processed data not promoted.")
        return 1

    # Update build manifest
    for table, rows in row_counts.items():
        update_build_manifest(table, rows, list(PROCESSED_DIR.glob("*.parquet")))

    # Rebuild DuckDB views to pick up new processed parquets
    print("\nRefreshing DuckDB views...")
    build_schema()

    print("\n✓ Rebuild complete.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
