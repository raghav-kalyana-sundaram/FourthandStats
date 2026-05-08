"""Validate all data — raw downloads and processed tables.

Usage:
    python scripts/validate_data.py
    python scripts/validate_data.py --seasons 2024 2025
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fourthandstats.data.manifest import load_manifest
from fourthandstats.data.quality import run_all_validations
from fourthandstats.utils.paths import LOGS_DIR, ensure_dirs
from fourthandstats.utils.time import parse_season_range


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate FourthandStats data")
    p.add_argument(
        "--seasons",
        nargs="+",
        help="Seasons to validate PBP for (default: all loaded seasons from manifest)",
    )
    return p.parse_args()


def main() -> int:
    ensure_dirs()
    args = parse_args()

    manifest = load_manifest()

    if args.seasons:
        seasons = parse_season_range(" ".join(args.seasons))
    else:
        seasons = manifest.loaded_seasons

    if not seasons:
        print("No seasons to validate. Run update_data.py first.")
        return 1

    print(f"\n=== FourthandStats — Data Validation ===")
    print(f"Validating seasons: {seasons}\n")

    results = run_all_validations(seasons)

    all_passed = True
    report_lines = [f"FourthandStats Validation Report — {datetime.now().isoformat()}"]

    for result in results:
        summary = result.summary()
        print(summary)
        report_lines.append(summary)
        if not result.passed:
            all_passed = False

    # Write report to logs
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = LOGS_DIR / f"validation_{datetime.now().strftime('%Y-%m-%d')}.txt"
    report_path.write_text("\n".join(report_lines))
    print(f"\nReport saved: {report_path}")

    if all_passed:
        print("\n✓ All validation checks passed.\n")
        return 0
    else:
        print("\n✗ Some validation checks failed. See report above.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
