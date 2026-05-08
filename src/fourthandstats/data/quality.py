"""Data quality validation — checks raw and processed tables for correctness."""

from __future__ import annotations

import polars as pl

from fourthandstats.data.manifest import load_manifest
from fourthandstats.utils.logging import get_logger
from fourthandstats.utils.paths import RAW_DIR, processed_path

logger = get_logger(__name__)

MODERN_TEAMS = {
    "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE",
    "DAL", "DEN", "DET", "GB",  "HOU", "IND", "JAX", "KC",
    "LA",  "LAC", "LV",  "MIA", "MIN", "NE",  "NO",  "NYG",
    "NYJ", "PHI", "PIT", "SEA", "SF",  "TB",  "TEN", "WAS",
}

# Relocated team abbreviations that appear in historical data
LEGACY_TEAM_MAP = {
    "STL": "LA",
    "SD":  "LAC",
    "OAK": "LV",
    "JAC": "JAX",
}


class ValidationResult:
    def __init__(self, name: str):
        self.name = name
        self.checks: list[tuple[str, str, str]] = []  # (status, check_name, detail)

    def ok(self, check: str, detail: str = "") -> None:
        self.checks.append(("PASS", check, detail))

    def warn(self, check: str, detail: str = "") -> None:
        self.checks.append(("WARN", check, detail))
        logger.warning("[%s] WARN %s: %s", self.name, check, detail)

    def fail(self, check: str, detail: str = "") -> None:
        self.checks.append(("FAIL", check, detail))
        logger.error("[%s] FAIL %s: %s", self.name, check, detail)

    @property
    def passed(self) -> bool:
        return not any(s == "FAIL" for s, _, _ in self.checks)

    def summary(self) -> str:
        lines = [f"\n=== Validation: {self.name} ==="]
        for status, check, detail in self.checks:
            icon = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗"}[status]
            lines.append(f"  {icon} [{status}] {check}" + (f" — {detail}" if detail else ""))
        overall = "PASSED" if self.passed else "FAILED"
        lines.append(f"\nResult: {overall} ({sum(1 for s,_,_ in self.checks if s=='PASS')} passed, "
                     f"{sum(1 for s,_,_ in self.checks if s=='WARN')} warnings, "
                     f"{sum(1 for s,_,_ in self.checks if s=='FAIL')} failures)")
        return "\n".join(lines)


def validate_pbp_raw(seasons: list[int]) -> ValidationResult:
    result = ValidationResult("pbp_raw")

    for season in seasons:
        path = RAW_DIR / "pbp" / f"pbp_{season}.parquet"
        if not path.exists():
            result.fail(f"pbp_{season}.parquet exists", "file not found")
            continue
        result.ok(f"pbp_{season}.parquet exists")

        df = pl.read_parquet(path)
        rows = len(df)

        # Row count sanity (~35K regular + ~10K playoffs = ~45K+)
        if rows < 30_000:
            result.warn(f"pbp_{season} row count", f"only {rows:,} rows — expected ~45,000+")
        else:
            result.ok(f"pbp_{season} row count", f"{rows:,} rows")

        # Required columns
        required = ["epa", "success", "pass", "rush", "play_type", "posteam", "defteam",
                    "down", "yards_gained", "season", "week", "game_id"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            result.fail(f"pbp_{season} required columns", f"missing: {missing}")
        else:
            result.ok(f"pbp_{season} required columns")

        # EPA not all null
        epa_null_pct = df["epa"].is_null().mean() * 100
        if epa_null_pct > 10:
            result.warn(f"pbp_{season} EPA nulls", f"{epa_null_pct:.1f}% null")
        else:
            result.ok(f"pbp_{season} EPA nulls", f"{epa_null_pct:.1f}%")

        # Season column matches filename
        seasons_in_file = df["season"].unique().to_list()
        if seasons_in_file != [season]:
            result.warn(f"pbp_{season} season values", f"found {seasons_in_file}")
        else:
            result.ok(f"pbp_{season} season values")

    return result


def validate_team_season_summary() -> ValidationResult:
    result = ValidationResult("team_season_summary")
    path = processed_path("team_season_summary")

    if not path.exists():
        result.fail("file exists", "team_season_summary.parquet not found")
        return result
    result.ok("file exists")

    df = pl.read_parquet(path)
    result.ok("loads cleanly", f"{len(df):,} rows")

    for season in sorted(df["season"].unique().to_list()):
        season_df = df.filter(pl.col("season") == season)
        teams_in_season = set(season_df["team"].to_list())
        n = len(teams_in_season)

        # Should have 32 modern teams for full seasons
        missing_modern = MODERN_TEAMS - teams_in_season
        if n < 32:
            result.warn(f"season {season} team count", f"{n} teams (missing: {missing_modern})")
        else:
            result.ok(f"season {season} team count", f"{n} teams")

        # No duplicate (team, season)
        dupes = season_df.filter(season_df["team"].is_duplicated())
        if not dupes.is_empty():
            result.fail(f"season {season} duplicates", f"{len(dupes)} duplicate rows")
        else:
            result.ok(f"season {season} no duplicates")

    # Key metric columns numeric (not all null)
    for col in ["off_epa_per_play", "def_epa_per_play_allowed", "net_epa_per_play"]:
        if col not in df.columns:
            result.fail(f"column {col} exists")
            continue
        null_pct = df[col].is_null().mean() * 100
        if null_pct > 5:
            result.warn(f"{col} nulls", f"{null_pct:.1f}%")
        else:
            result.ok(f"{col} present", f"{null_pct:.1f}% null")

    return result


def validate_player_season_summary() -> ValidationResult:
    result = ValidationResult("player_season_summary")
    path = processed_path("player_season_summary")

    if not path.exists():
        result.fail("file exists", "player_season_summary.parquet not found")
        return result
    result.ok("file exists")

    df = pl.read_parquet(path)
    result.ok("loads cleanly", f"{len(df):,} rows")

    # Should have meaningful QB data
    qb_rows = df.filter(pl.col("dropbacks").is_not_null() & (pl.col("dropbacks") > 0))
    if len(qb_rows) < 30:
        result.warn("QB rows", f"only {len(qb_rows)} rows with dropbacks")
    else:
        result.ok("QB rows", f"{len(qb_rows)} rows with dropbacks")

    return result


def validate_manifest() -> ValidationResult:
    result = ValidationResult("manifest")
    manifest = load_manifest()

    if not manifest.loaded_seasons:
        result.fail("loaded_seasons", "manifest is empty — no data downloaded yet")
        return result
    result.ok("loaded_seasons", str(manifest.loaded_seasons))

    # Check each claimed dataset actually has files
    for ds_name, status in manifest.datasets.items():
        if not status.available:
            continue
        if status.seasons:
            for s in status.seasons:
                p = RAW_DIR / ds_name / f"{ds_name}_{s}.parquet"
                if not p.exists():
                    result.fail(f"{ds_name}_{s} on disk", "file missing but manifest claims available")
                else:
                    result.ok(f"{ds_name}_{s} on disk")
        else:
            p = RAW_DIR / ds_name / f"{ds_name}.parquet"
            if not p.exists():
                result.fail(f"{ds_name} static on disk", "file missing but manifest claims available")
            else:
                result.ok(f"{ds_name} static on disk")

    return result


def run_all_validations(seasons: list[int]) -> list[ValidationResult]:
    """Run all validation checks and return results."""
    results = [
        validate_manifest(),
        validate_pbp_raw(seasons),
        validate_team_season_summary(),
        validate_player_season_summary(),
    ]
    return results
