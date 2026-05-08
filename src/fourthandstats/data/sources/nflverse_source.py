"""nflverse source adapter — wraps nflreadpy and returns Polars DataFrames."""

from __future__ import annotations

import polars as pl


def fetch_pbp(seasons: list[int]) -> pl.DataFrame:
    import nflreadpy as nfl
    return nfl.load_pbp(seasons=seasons)


def fetch_schedules(seasons: list[int]) -> pl.DataFrame:
    import nflreadpy as nfl
    return nfl.load_schedules(seasons=seasons)


def fetch_rosters(seasons: list[int]) -> pl.DataFrame:
    import nflreadpy as nfl
    return nfl.load_rosters(seasons=seasons)


def fetch_player_stats(seasons: list[int]) -> pl.DataFrame:
    import nflreadpy.load_stats as ls
    return ls.load_player_stats(seasons=seasons, summary_level="week")


def fetch_snap_counts(seasons: list[int]) -> pl.DataFrame:
    import nflreadpy as nfl
    return nfl.load_snap_counts(seasons=seasons)


def fetch_injuries(seasons: list[int]) -> pl.DataFrame:
    import nflreadpy as nfl
    return nfl.load_injuries(seasons=seasons)


def fetch_depth_charts(seasons: list[int]) -> pl.DataFrame:
    import nflreadpy as nfl
    return nfl.load_depth_charts(seasons=seasons)


def fetch_participation(seasons: list[int]) -> pl.DataFrame:
    import nflreadpy as nfl
    return nfl.load_participation(seasons=seasons)


def fetch_combine(seasons: list[int]) -> pl.DataFrame:
    import nflreadpy as nfl
    return nfl.load_combine(seasons=seasons)


def fetch_draft_picks(seasons: list[int]) -> pl.DataFrame:
    import nflreadpy as nfl
    return nfl.load_draft_picks(seasons=seasons)


def fetch_players_meta() -> pl.DataFrame:
    import nflreadpy as nfl
    return nfl.load_players()


def fetch_teams_meta() -> pl.DataFrame:
    import nflreadpy as nfl
    return nfl.load_teams()


def get_current_season() -> int:
    import nflreadpy as nfl
    return nfl.get_current_season()


def get_current_week() -> int:
    import nflreadpy as nfl
    return nfl.get_current_week()
