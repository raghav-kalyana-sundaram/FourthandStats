"""Data transformation — builds derived metric tables from raw parquets.

All heavy computation runs in DuckDB SQL (fast columnar execution).
Results are written to parquet under data/processed/.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from fourthandstats.utils.logging import get_logger
from fourthandstats.utils.paths import PROCESSED_DIR, RAW_DIR, processed_path

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _pbp_glob() -> str:
    return str(RAW_DIR / "pbp" / "*.parquet")


def _write_atomic(rel: duckdb.DuckDBPyRelation, dest: Path) -> int:
    """Write a DuckDB relation to parquet atomically. Returns row count."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".parquet.tmp")
    df = rel.pl()
    df.write_parquet(str(tmp))
    tmp.rename(dest)
    return len(df)


# ---------------------------------------------------------------------------
# Team-level derived tables
# ---------------------------------------------------------------------------

_TEAM_SEASON_SQL = """
WITH plays AS (
    SELECT *,
        CASE
            WHEN play_type = 'pass' OR sack = 1.0 THEN 'pass'
            WHEN play_type = 'run' THEN 'rush'
            ELSE NULL
        END AS play_category,
        CASE
            WHEN play_type = 'run'  AND yards_gained >= 12 THEN 1
            WHEN play_type = 'pass' AND yards_gained >= 16 THEN 1
            ELSE 0
        END AS is_explosive
    FROM read_parquet('{pbp_glob}')
    WHERE play_type IN ('pass', 'run')
      AND posteam IS NOT NULL
),
off_stats AS (
    SELECT
        posteam                     AS team,
        season,
        COUNT(DISTINCT game_id)     AS games,
        COUNT(*)                    AS off_plays,
        AVG(epa)                    AS off_epa_per_play,
        AVG(success)                AS off_success_rate,
        AVG(is_explosive)           AS explosive_play_rate,
        -- Pass
        AVG(CASE WHEN play_category = 'pass' THEN epa END)     AS pass_epa_per_play,
        AVG(CASE WHEN play_category = 'pass' THEN success END) AS pass_success_rate,
        AVG(CASE WHEN play_category = 'pass' THEN is_explosive END) AS explosive_play_rate_pass,
        -- Rush
        AVG(CASE WHEN play_category = 'rush' THEN epa END)     AS rush_epa_per_play,
        AVG(CASE WHEN play_category = 'rush' THEN success END) AS rush_success_rate,
        AVG(CASE WHEN play_category = 'rush' THEN is_explosive END) AS explosive_play_rate_rush,
        -- Third down
        AVG(CASE WHEN down = 3 THEN third_down_converted END)  AS third_down_success_rate,
        -- Red zone (inside opp 20)
        AVG(CASE WHEN yardline_100 <= 20 THEN epa END)         AS red_zone_epa_per_play,
        -- Turnovers committed (negative EPA events)
        SUM(CASE WHEN (interception = 1 OR fumble_lost = 1) THEN epa ELSE 0 END) AS turnover_epa_committed,
        COUNT(CASE WHEN interception = 1 OR fumble_lost = 1 THEN 1 END) AS turnovers_committed,
        -- Pass rate
        AVG(CASE WHEN play_category = 'pass' THEN 1.0 ELSE 0.0 END) AS pass_rate,
        -- Air yards / aDOT
        AVG(CASE WHEN play_category = 'pass' THEN air_yards END) AS adot
    FROM plays
    GROUP BY posteam, season
),
def_stats AS (
    SELECT
        defteam                     AS team,
        season,
        AVG(epa)                    AS def_epa_per_play_allowed,
        AVG(success)                AS def_success_rate_allowed,
        AVG(is_explosive)           AS explosive_play_rate_allowed,
        AVG(CASE WHEN play_category = 'pass' THEN epa END)     AS pass_epa_per_play_allowed,
        AVG(CASE WHEN play_category = 'rush' THEN epa END)     AS rush_epa_per_play_allowed,
        AVG(CASE WHEN play_category = 'pass' THEN success END) AS pass_success_rate_allowed,
        AVG(CASE WHEN play_category = 'rush' THEN success END) AS rush_success_rate_allowed,
        AVG(CASE WHEN play_category = 'pass' THEN is_explosive END) AS explosive_play_rate_pass_allowed,
        AVG(CASE WHEN play_category = 'rush' THEN is_explosive END) AS explosive_play_rate_rush_allowed,
        AVG(CASE WHEN down = 3 THEN third_down_converted END)  AS third_down_success_rate_allowed,
        AVG(CASE WHEN yardline_100 <= 20 THEN epa END)         AS red_zone_epa_per_play_allowed,
        SUM(CASE WHEN (interception = 1 OR fumble_lost = 1) THEN epa ELSE 0 END) AS turnover_epa_forced,
        COUNT(CASE WHEN interception = 1 OR fumble_lost = 1 THEN 1 END) AS turnovers_forced
    FROM plays
    GROUP BY defteam, season
)
SELECT
    o.team,
    o.season,
    o.games,
    o.off_plays,
    -- Offense
    ROUND(o.off_epa_per_play, 4)          AS off_epa_per_play,
    ROUND(o.off_success_rate, 4)          AS off_success_rate,
    ROUND(o.explosive_play_rate, 4)       AS explosive_play_rate,
    ROUND(o.pass_epa_per_play, 4)         AS pass_epa_per_play,
    ROUND(o.pass_success_rate, 4)         AS pass_success_rate,
    ROUND(o.explosive_play_rate_pass, 4)  AS explosive_play_rate_pass,
    ROUND(o.rush_epa_per_play, 4)         AS rush_epa_per_play,
    ROUND(o.rush_success_rate, 4)         AS rush_success_rate,
    ROUND(o.explosive_play_rate_rush, 4)  AS explosive_play_rate_rush,
    ROUND(o.third_down_success_rate, 4)   AS third_down_success_rate,
    ROUND(o.red_zone_epa_per_play, 4)     AS red_zone_epa_per_play,
    ROUND(o.turnover_epa_committed, 4)    AS turnover_epa_committed,
    o.turnovers_committed,
    ROUND(o.pass_rate, 4)                 AS pass_rate,
    ROUND(o.adot, 2)                      AS adot,
    -- Defense
    ROUND(d.def_epa_per_play_allowed, 4)       AS def_epa_per_play_allowed,
    ROUND(d.def_success_rate_allowed, 4)       AS def_success_rate_allowed,
    ROUND(d.explosive_play_rate_allowed, 4)    AS explosive_play_rate_allowed,
    ROUND(d.pass_epa_per_play_allowed, 4)      AS pass_epa_per_play_allowed,
    ROUND(d.rush_epa_per_play_allowed, 4)      AS rush_epa_per_play_allowed,
    ROUND(d.pass_success_rate_allowed, 4)      AS pass_success_rate_allowed,
    ROUND(d.rush_success_rate_allowed, 4)      AS rush_success_rate_allowed,
    ROUND(d.explosive_play_rate_pass_allowed, 4) AS explosive_play_rate_pass_allowed,
    ROUND(d.explosive_play_rate_rush_allowed, 4) AS explosive_play_rate_rush_allowed,
    ROUND(d.third_down_success_rate_allowed, 4)  AS third_down_success_rate_allowed,
    ROUND(d.red_zone_epa_per_play_allowed, 4)    AS red_zone_epa_per_play_allowed,
    ROUND(d.turnover_epa_forced, 4)              AS turnover_epa_forced,
    d.turnovers_forced,
    -- Net EPA
    ROUND(o.off_epa_per_play - d.def_epa_per_play_allowed, 4) AS net_epa_per_play
FROM off_stats o
JOIN def_stats d ON o.team = d.team AND o.season = d.season
ORDER BY o.season, o.team
"""

_TEAM_WEEKLY_SQL = """
WITH plays AS (
    SELECT *,
        CASE
            WHEN play_type = 'pass' OR sack = 1.0 THEN 'pass'
            WHEN play_type = 'run' THEN 'rush'
            ELSE NULL
        END AS play_category,
        CASE
            WHEN play_type = 'run'  AND yards_gained >= 12 THEN 1
            WHEN play_type = 'pass' AND yards_gained >= 16 THEN 1
            ELSE 0
        END AS is_explosive
    FROM read_parquet('{pbp_glob}')
    WHERE play_type IN ('pass', 'run')
      AND posteam IS NOT NULL
),
off_w AS (
    SELECT
        posteam AS team, season, week,
        COUNT(*) AS off_plays,
        AVG(epa) AS off_epa_per_play,
        AVG(success) AS off_success_rate,
        AVG(is_explosive) AS explosive_play_rate,
        AVG(CASE WHEN play_category='pass' THEN epa END) AS pass_epa_per_play,
        AVG(CASE WHEN play_category='rush' THEN epa END) AS rush_epa_per_play,
        AVG(CASE WHEN play_category='pass' THEN success END) AS pass_success_rate,
        AVG(CASE WHEN play_category='rush' THEN success END) AS rush_success_rate
    FROM plays
    GROUP BY posteam, season, week
),
def_w AS (
    SELECT
        defteam AS team, season, week,
        AVG(epa) AS def_epa_per_play_allowed,
        AVG(success) AS def_success_rate_allowed,
        AVG(is_explosive) AS explosive_play_rate_allowed,
        AVG(CASE WHEN play_category='pass' THEN epa END) AS pass_epa_per_play_allowed,
        AVG(CASE WHEN play_category='rush' THEN epa END) AS rush_epa_per_play_allowed
    FROM plays
    GROUP BY defteam, season, week
)
SELECT
    o.team, o.season, o.week, o.off_plays,
    ROUND(o.off_epa_per_play, 4) AS off_epa_per_play,
    ROUND(o.off_success_rate, 4) AS off_success_rate,
    ROUND(o.explosive_play_rate, 4) AS explosive_play_rate,
    ROUND(o.pass_epa_per_play, 4) AS pass_epa_per_play,
    ROUND(o.rush_epa_per_play, 4) AS rush_epa_per_play,
    ROUND(o.pass_success_rate, 4) AS pass_success_rate,
    ROUND(o.rush_success_rate, 4) AS rush_success_rate,
    ROUND(d.def_epa_per_play_allowed, 4) AS def_epa_per_play_allowed,
    ROUND(d.def_success_rate_allowed, 4) AS def_success_rate_allowed,
    ROUND(d.explosive_play_rate_allowed, 4) AS explosive_play_rate_allowed,
    ROUND(d.pass_epa_per_play_allowed, 4) AS pass_epa_per_play_allowed,
    ROUND(d.rush_epa_per_play_allowed, 4) AS rush_epa_per_play_allowed,
    ROUND(o.off_epa_per_play - d.def_epa_per_play_allowed, 4) AS net_epa_per_play
FROM off_w o
JOIN def_w d ON o.team = d.team AND o.season = d.season AND o.week = d.week
ORDER BY o.season, o.week, o.team
"""


# ---------------------------------------------------------------------------
# Player-level derived tables
# ---------------------------------------------------------------------------

_PLAYER_SEASON_SQL = """
WITH pbp_qb AS (
    SELECT
        passer_player_id AS player_id,
        passer_player_name AS player_name,
        posteam AS team,
        season,
        COUNT(*) AS dropbacks,
        SUM(pass_attempt) AS pass_attempts,
        SUM(complete_pass) AS completions,
        SUM(CASE WHEN complete_pass = 1 THEN yards_gained ELSE 0 END) AS pass_yards,
        SUM(CASE WHEN touchdown = 1 AND (pass = 1 OR sack = 1) THEN 1 ELSE 0 END) AS pass_tds,
        SUM(interception) AS interceptions,
        SUM(sack) AS sacks_taken,
        AVG(epa) AS epa_per_dropback,
        AVG(CASE WHEN pass_attempt = 1 THEN cpoe END) AS cpoe,
        AVG(success) AS pass_success_rate,
        AVG(air_yards) AS adot,
        SUM(air_yards) AS total_air_yards
    FROM read_parquet('{pbp_glob}')
    WHERE (pass = 1 OR sack = 1)
      AND passer_player_id IS NOT NULL
      AND play_type IN ('pass', 'run')
    GROUP BY passer_player_id, passer_player_name, posteam, season
),
pbp_rb AS (
    SELECT
        rusher_player_id AS player_id,
        rusher_player_name AS player_name,
        posteam AS team,
        season,
        COUNT(*) AS carries,
        SUM(yards_gained) AS rush_yards,
        SUM(CASE WHEN touchdown = 1 AND rush = 1 THEN 1 ELSE 0 END) AS rush_tds,
        AVG(epa) AS rush_epa_per_carry,
        AVG(success) AS rush_success_rate,
        AVG(CASE WHEN yards_gained >= 12 THEN 1.0 ELSE 0.0 END) AS explosive_rate_rush
    FROM read_parquet('{pbp_glob}')
    WHERE rush = 1
      AND rusher_player_id IS NOT NULL
    GROUP BY rusher_player_id, rusher_player_name, posteam, season
),
pbp_rec AS (
    SELECT
        receiver_player_id AS player_id,
        receiver_player_name AS player_name,
        posteam AS team,
        season,
        COUNT(*) AS targets,
        SUM(complete_pass) AS receptions,
        SUM(CASE WHEN complete_pass = 1 THEN yards_gained ELSE 0 END) AS rec_yards,
        SUM(CASE WHEN touchdown = 1 AND complete_pass = 1 THEN 1 ELSE 0 END) AS rec_tds,
        AVG(air_yards) AS adot,
        SUM(air_yards) AS total_air_yards,
        AVG(CASE WHEN yards_gained >= 16 THEN 1.0 ELSE 0.0 END) AS explosive_rate_rec
    FROM read_parquet('{pbp_glob}')
    WHERE pass_attempt = 1
      AND receiver_player_id IS NOT NULL
    GROUP BY receiver_player_id, receiver_player_name, posteam, season
),
-- Team totals for share calculations
team_targets AS (
    SELECT posteam AS team, season, COUNT(*) AS team_targets, SUM(air_yards) AS team_air_yards
    FROM read_parquet('{pbp_glob}')
    WHERE pass_attempt = 1 AND posteam IS NOT NULL
    GROUP BY posteam, season
)
SELECT
    COALESCE(q.player_id, rb.player_id, r.player_id) AS player_id,
    COALESCE(q.player_name, rb.player_name, r.player_name) AS player_name,
    COALESCE(q.team, rb.team, r.team) AS team,
    COALESCE(q.season, rb.season, r.season) AS season,
    -- QB
    q.dropbacks,
    q.pass_attempts,
    q.completions,
    ROUND(q.pass_yards, 0) AS pass_yards,
    q.pass_tds,
    q.interceptions,
    q.sacks_taken,
    ROUND(q.epa_per_dropback, 4) AS epa_per_dropback,
    ROUND(q.cpoe, 2) AS cpoe,
    ROUND(q.pass_success_rate, 4) AS pass_success_rate,
    ROUND(q.adot, 2) AS adot_qb,
    ROUND(q.total_air_yards, 0) AS air_yards_qb,
    -- RB
    rb.carries,
    ROUND(rb.rush_yards, 0) AS rush_yards,
    rb.rush_tds,
    ROUND(rb.rush_epa_per_carry, 4) AS rush_epa_per_carry,
    ROUND(rb.rush_success_rate, 4) AS rush_success_rate,
    ROUND(rb.explosive_rate_rush, 4) AS explosive_rate_rush,
    -- WR/TE receiver
    r.targets,
    ROUND(r.receptions, 0) AS receptions,
    ROUND(r.rec_yards, 0) AS rec_yards,
    r.rec_tds,
    ROUND(r.adot, 2) AS adot_rec,
    ROUND(r.total_air_yards, 0) AS total_air_yards,
    ROUND(r.explosive_rate_rec, 4) AS explosive_rate_rec,
    -- Share metrics (require team totals join)
    ROUND(CAST(r.targets AS DOUBLE) / NULLIF(tt.team_targets, 0), 4) AS target_share,
    ROUND(CAST(r.total_air_yards AS DOUBLE) / NULLIF(tt.team_air_yards, 0), 4) AS air_yards_share
FROM pbp_qb q
FULL OUTER JOIN pbp_rb rb ON q.player_id = rb.player_id AND q.season = rb.season
FULL OUTER JOIN pbp_rec r  ON COALESCE(q.player_id, rb.player_id) = r.player_id
                           AND COALESCE(q.season, rb.season) = r.season
LEFT JOIN team_targets tt  ON COALESCE(q.team, rb.team, r.team) = tt.team
                           AND COALESCE(q.season, rb.season, r.season) = tt.season
WHERE COALESCE(q.player_id, rb.player_id, r.player_id) IS NOT NULL
ORDER BY COALESCE(q.season, rb.season, r.season), COALESCE(q.team, rb.team, r.team)
"""

_PLAY_INDEX_SQL = """
SELECT
    game_id,
    CAST(play_id AS INTEGER)         AS play_id,
    season,
    week,
    season_type,
    posteam,
    defteam,
    CAST(qtr AS INTEGER)             AS qtr,
    end_clock_time                   AS clock_time,
    CAST(down AS INTEGER)            AS down,
    ydstogo,
    yardline_100,
    yards_gained,
    play_type,
    "desc",
    epa,
    wpa,
    CAST(success AS INTEGER)         AS success,
    CAST(pass AS INTEGER)            AS pass,
    CAST(rush AS INTEGER)            AS rush,
    passer_player_id,
    passer_player_name,
    rusher_player_id,
    rusher_player_name,
    receiver_player_id,
    receiver_player_name,
    CAST(touchdown AS INTEGER)       AS touchdown,
    CAST(interception AS INTEGER)    AS interception,
    CAST(fumble_lost AS INTEGER)     AS fumble_lost,
    score_differential,
    -- Derived helper columns
    CASE
        WHEN yardline_100 <= 20  THEN 'opp_red_zone'
        WHEN yardline_100 <= 50  THEN 'opp_field'
        WHEN yardline_100 <= 80  THEN 'own_field'
        ELSE 'own_red_zone'
    END AS field_zone,
    CASE
        WHEN ydstogo BETWEEN 1 AND 3 THEN 'short'
        WHEN ydstogo BETWEEN 4 AND 7 THEN 'medium'
        ELSE 'long'
    END AS distance_bucket,
    CASE
        WHEN score_differential > 8  THEN 'leading_big'
        WHEN score_differential > 0  THEN 'leading'
        WHEN score_differential = 0  THEN 'tied'
        WHEN score_differential >= -8 THEN 'trailing'
        ELSE 'trailing_big'
    END AS score_state
FROM read_parquet('{pbp_glob}')
WHERE play_type IN ('pass', 'run', 'punt', 'field_goal', 'kickoff', 'extra_point', 'qb_kneel', 'qb_spike', 'no_play')
  AND game_id IS NOT NULL
ORDER BY season, week, game_id, play_id
"""


# ---------------------------------------------------------------------------
# Public build functions
# ---------------------------------------------------------------------------


def build_team_season_summary() -> int:
    """Build team_season_summary.parquet. Returns row count."""
    logger.info("Building team_season_summary...")
    pbp_glob = _pbp_glob()
    sql = _TEAM_SEASON_SQL.format(pbp_glob=pbp_glob)
    with duckdb.connect(":memory:") as con:
        rel = con.sql(sql)
        rows = _write_atomic(rel, processed_path("team_season_summary"))
    logger.info("team_season_summary: %d rows", rows)
    return rows


def build_team_weekly_summary() -> int:
    """Build team_weekly_summary.parquet. Returns row count."""
    logger.info("Building team_weekly_summary...")
    pbp_glob = _pbp_glob()
    sql = _TEAM_WEEKLY_SQL.format(pbp_glob=pbp_glob)
    with duckdb.connect(":memory:") as con:
        rel = con.sql(sql)
        rows = _write_atomic(rel, processed_path("team_weekly_summary"))
    logger.info("team_weekly_summary: %d rows", rows)
    return rows


def build_player_season_summary() -> int:
    """Build player_season_summary.parquet. Returns row count."""
    logger.info("Building player_season_summary...")
    pbp_glob = _pbp_glob()
    sql = _PLAYER_SEASON_SQL.format(pbp_glob=pbp_glob)
    with duckdb.connect(":memory:") as con:
        rel = con.sql(sql)
        rows = _write_atomic(rel, processed_path("player_season_summary"))
    logger.info("player_season_summary: %d rows", rows)
    return rows


def build_play_index() -> int:
    """Build play_index.parquet. Returns row count."""
    logger.info("Building play_index...")
    pbp_glob = _pbp_glob()
    sql = _PLAY_INDEX_SQL.format(pbp_glob=pbp_glob)
    with duckdb.connect(":memory:") as con:
        rel = con.sql(sql)
        rows = _write_atomic(rel, processed_path("play_index"))
    logger.info("play_index: %d rows", rows)
    return rows


def build_all_tables() -> dict[str, int]:
    """Build all derived tables. Returns {table_name: row_count}."""
    results: dict[str, int] = {}

    results["team_season_summary"] = build_team_season_summary()
    results["team_weekly_summary"] = build_team_weekly_summary()
    results["player_season_summary"] = build_player_season_summary()
    results["play_index"] = build_play_index()

    return results
