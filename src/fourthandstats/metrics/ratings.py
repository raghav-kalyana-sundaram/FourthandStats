"""Composite rating calculations — weighted percentile composites (0–100 scale).

Weights are loaded from config/rating_weights.yaml and fully configurable.
"""

from __future__ import annotations

import yaml
import polars as pl

from fourthandstats.utils.logging import get_logger
from fourthandstats.utils.paths import CONFIG_DIR, processed_path

logger = get_logger(__name__)


def _load_weights() -> dict:
    path = CONFIG_DIR / "rating_weights.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def _weighted_avg(percentiles: dict[str, float], weights: dict[str, float]) -> float:
    """Compute a weighted average of available percentiles.

    Missing metrics are skipped and weights renormalized.
    """
    total_w = 0.0
    total_v = 0.0
    for metric, weight in weights.items():
        if metric in percentiles and percentiles[metric] is not None:
            w = abs(weight)  # weights can be negative (e.g. sack_rate penalizes)
            sign = 1 if weight >= 0 else -1
            # For negative-weight metrics: lower value = better = higher percentile already handled
            total_v += w * percentiles[metric]
            total_w += w
    if total_w == 0:
        return 0.0
    return round(total_v / total_w, 1)


def build_team_ratings() -> int:
    """Compute composite ratings for all team-seasons.

    Appends rating columns to team_season_summary and rewrites it.
    Returns row count.
    """
    weights = _load_weights()
    src = processed_path("team_season_summary")
    pct_src = processed_path("metric_percentiles")

    if not src.exists() or not pct_src.exists():
        logger.error("team_season_summary or metric_percentiles not found")
        return 0

    teams_df = pl.read_parquet(src)
    pct_df = pl.read_parquet(pct_src).filter(pl.col("entity_type") == "team")

    # Build a lookup: {(team, season): {metric: percentile}}
    pct_lookup: dict[tuple, dict[str, float]] = {}
    for row in pct_df.iter_rows(named=True):
        key = (row["entity_id"], row["season"])
        pct_lookup.setdefault(key, {})[row["metric"]] = row["percentile"]

    rating_configs = {
        "off_rating": weights.get("offensive_rating", {}),
        "def_rating": weights.get("defensive_rating", {}),
        "pass_off_rating": weights.get("passing_offense_rating", {}),
        "rush_off_rating": weights.get("rushing_offense_rating", {}),
        "pass_def_rating": weights.get("passing_defense_rating", {}),
        "rush_def_rating": weights.get("rushing_defense_rating", {}),
        "explosiveness_rating": weights.get("explosiveness_rating", {}),
        "explosive_prevention_rating": weights.get("explosive_prevention_rating", {}),
        "situational_rating": weights.get("situational_rating", {}),
        "recent_form_rating": weights.get("recent_form_rating", {}),
    }

    rows = []
    for row in teams_df.iter_rows(named=True):
        key = (row["team"], row["season"])
        pcts = pct_lookup.get(key, {})
        entry = dict(row)
        for rating_name, w in rating_configs.items():
            entry[rating_name] = _weighted_avg(pcts, w)

        # Overall = weighted avg of off/def/situational/recent
        overall_w = weights.get("overall_rating", {})
        entry["overall_rating"] = _weighted_avg(
            {
                "offensive_rating": entry.get("off_rating", 0.0),
                "defensive_rating": entry.get("def_rating", 0.0),
                "situational_rating": entry.get("situational_rating", 0.0),
                "recent_form_rating": entry.get("recent_form_rating", 0.0),
            },
            overall_w,
        )
        rows.append(entry)

    out = pl.DataFrame(rows)
    out.write_parquet(str(src))
    logger.info("Team ratings added to team_season_summary (%d rows)", len(out))
    return len(out)
