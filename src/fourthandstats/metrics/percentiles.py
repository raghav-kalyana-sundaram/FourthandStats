"""Percentile calculations — per-(metric, season) for teams and players."""

from __future__ import annotations

import polars as pl

from fourthandstats.utils.logging import get_logger
from fourthandstats.utils.paths import processed_path

logger = get_logger(__name__)

# Team metrics to percentile-rank (higher = better for all, except noted)
TEAM_METRICS = [
    "off_epa_per_play",
    "def_epa_per_play_allowed",   # LOWER is better — inverted below
    "net_epa_per_play",
    "off_success_rate",
    "def_success_rate_allowed",   # LOWER is better
    "explosive_play_rate",
    "explosive_play_rate_allowed",  # LOWER is better
    "pass_epa_per_play",
    "rush_epa_per_play",
    "pass_epa_per_play_allowed",  # LOWER
    "rush_epa_per_play_allowed",  # LOWER
    "third_down_success_rate",
    "third_down_success_rate_allowed",  # LOWER
    "red_zone_epa_per_play",
    "red_zone_epa_per_play_allowed",  # LOWER
    "turnover_epa_forced",
    "turnover_epa_committed",     # LOWER (you want to avoid committing turnovers)
]

# Metrics where LOWER value = better (we invert rank so percentile 100 = best)
LOWER_IS_BETTER = {
    "def_epa_per_play_allowed",
    "def_success_rate_allowed",
    "explosive_play_rate_allowed",
    "pass_epa_per_play_allowed",
    "rush_epa_per_play_allowed",
    "third_down_success_rate_allowed",
    "red_zone_epa_per_play_allowed",
    "turnover_epa_committed",
    "explosive_play_rate_pass_allowed",
    "explosive_play_rate_rush_allowed",
}


def _rank_to_percentile(rank: pl.Series, n: int, lower_is_better: bool) -> pl.Series:
    """Convert a rank (1-based) to a 0–100 percentile."""
    if lower_is_better:
        # Rank 1 (lowest value) = percentile 100
        return ((n - rank) / (n - 1) * 100).round(1)
    else:
        # Rank 1 (lowest value) = percentile 0; rank n = percentile 100
        return ((rank - 1) / (n - 1) * 100).round(1)


def build_team_percentiles() -> int:
    """Compute per-season percentiles for all team metrics.

    Returns row count of the metric_percentiles table.
    """
    src = processed_path("team_season_summary")
    if not src.exists():
        logger.error("team_season_summary.parquet not found — run rebuild first")
        return 0

    df = pl.read_parquet(src)
    records = []

    for season in sorted(df["season"].unique().to_list()):
        season_df = df.filter(pl.col("season") == season)
        n = len(season_df)
        if n < 2:
            continue

        for metric in TEAM_METRICS:
            if metric not in season_df.columns:
                continue

            vals = season_df.select(["team", metric]).drop_nulls()
            if vals.is_empty():
                continue

            lower = metric in LOWER_IS_BETTER
            ranked = vals.with_columns(
                pl.col(metric).rank(method="average").alias("rank")
            )

            for row in ranked.iter_rows(named=True):
                pct = _rank_to_percentile(
                    pl.Series([row["rank"]]), n=n, lower_is_better=lower
                )[0]
                records.append({
                    "entity_type": "team",
                    "entity_id": row["team"],
                    "season": season,
                    "metric": metric,
                    "value": row[metric],
                    "rank": int(row["rank"]),
                    "percentile": float(pct),
                    "n": n,
                })

    if not records:
        logger.warning("No percentile records computed")
        return 0

    out = pl.DataFrame(records)
    dest = processed_path("metric_percentiles")
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.write_parquet(str(dest))
    logger.info("metric_percentiles: %d rows", len(out))
    return len(out)


def get_team_percentile(team: str, season: int, metric: str) -> float | None:
    """Look up a single team percentile at runtime."""
    p = processed_path("metric_percentiles")
    if not p.exists():
        return None
    df = pl.read_parquet(p).filter(
        (pl.col("entity_type") == "team")
        & (pl.col("entity_id") == team)
        & (pl.col("season") == season)
        & (pl.col("metric") == metric)
    )
    if df.is_empty():
        return None
    return df["percentile"][0]


def get_team_season_percentiles(team: str, season: int) -> dict[str, float]:
    """Return all percentiles for a team-season as {metric: percentile}."""
    p = processed_path("metric_percentiles")
    if not p.exists():
        return {}
    df = pl.read_parquet(p).filter(
        (pl.col("entity_type") == "team")
        & (pl.col("entity_id") == team)
        & (pl.col("season") == season)
    )
    return {row["metric"]: row["percentile"] for row in df.iter_rows(named=True)}
