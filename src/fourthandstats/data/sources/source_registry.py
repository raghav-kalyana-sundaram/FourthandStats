"""Source registry — maps dataset names to their fetch functions and metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import polars as pl

from fourthandstats.data.sources import nflverse_source as nfl


@dataclass
class SourceDef:
    name: str
    seasonal: bool  # True = one parquet per season; False = single static file
    fetch_fn: Callable  # callable that returns pl.DataFrame
    # For seasonal datasets, fetch_fn receives list[int]; for static, no args.
    min_season: Optional[int] = None  # earliest reliable season (informational)
    description: str = ""


REGISTRY: dict[str, SourceDef] = {
    "pbp": SourceDef(
        name="pbp",
        seasonal=True,
        fetch_fn=nfl.fetch_pbp,
        min_season=1999,
        description="Play-by-play",
    ),
    "schedules": SourceDef(
        name="schedules",
        seasonal=True,
        fetch_fn=nfl.fetch_schedules,
        min_season=1999,
        description="Game schedules and results",
    ),
    "rosters": SourceDef(
        name="rosters",
        seasonal=True,
        fetch_fn=nfl.fetch_rosters,
        min_season=2001,
        description="Season rosters",
    ),
    "player_stats": SourceDef(
        name="player_stats",
        seasonal=True,
        fetch_fn=nfl.fetch_player_stats,
        min_season=1999,
        description="Weekly player stats",
    ),
    "snap_counts": SourceDef(
        name="snap_counts",
        seasonal=True,
        fetch_fn=nfl.fetch_snap_counts,
        min_season=2012,
        description="Offensive and defensive snap counts",
    ),
    "injuries": SourceDef(
        name="injuries",
        seasonal=True,
        fetch_fn=nfl.fetch_injuries,
        min_season=2009,
        description="Weekly injury reports",
    ),
    "depth_charts": SourceDef(
        name="depth_charts",
        seasonal=True,
        fetch_fn=nfl.fetch_depth_charts,
        min_season=2001,
        description="Depth charts by week",
    ),
    "participation": SourceDef(
        name="participation",
        seasonal=True,
        fetch_fn=nfl.fetch_participation,
        description="Personnel/participation data (spotty coverage)",
    ),
    "combine": SourceDef(
        name="combine",
        seasonal=True,
        fetch_fn=nfl.fetch_combine,
        min_season=1987,
        description="NFL combine measurements",
    ),
    "draft_picks": SourceDef(
        name="draft_picks",
        seasonal=True,
        fetch_fn=nfl.fetch_draft_picks,
        min_season=1985,
        description="Draft pick history",
    ),
    "players_meta": SourceDef(
        name="players_meta",
        seasonal=False,
        fetch_fn=nfl.fetch_players_meta,
        description="Player metadata (IDs, bio, position)",
    ),
    "teams_meta": SourceDef(
        name="teams_meta",
        seasonal=False,
        fetch_fn=nfl.fetch_teams_meta,
        description="Team metadata (abbreviations, names, divisions)",
    ),
}

# Default MVP datasets — only what's needed to build initial metrics
MVP_DATASETS = ["pbp", "schedules", "rosters", "player_stats", "snap_counts",
                "players_meta", "teams_meta"]

ALL_DATASETS = list(REGISTRY.keys())


def get_source(name: str) -> SourceDef:
    if name not in REGISTRY:
        raise KeyError(f"Unknown dataset '{name}'. Available: {ALL_DATASETS}")
    return REGISTRY[name]
