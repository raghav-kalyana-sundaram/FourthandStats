"""DuckDB schema — creates the database and registers views over parquet files.

The DuckDB file (football.duckdb) stores only view definitions.
All actual data lives in parquet files under data/raw/ and data/processed/.
The DB can be deleted and recreated at any time via build_schema().
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from fourthandstats.utils.logging import get_logger
from fourthandstats.utils.paths import PROCESSED_DIR, RAW_DIR, processed_path

logger = get_logger(__name__)

_DB_PATH = RAW_DIR.parent.parent / "data" / "processed" / "football.duckdb"


def _db_path() -> Path:
    from fourthandstats.utils.paths import PROJECT_ROOT
    return PROJECT_ROOT / "data" / "processed" / "football.duckdb"


def get_connection(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection.

    read_only=True for app queries (safe for concurrent reads).
    read_only=False for rebuild operations (single writer).
    """
    db = _db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db), read_only=read_only)


def _glob(dataset: str, pattern: str = "*.parquet") -> str:
    """Return a glob path string for DuckDB read_parquet."""
    p = RAW_DIR / dataset / pattern
    return str(p)


def build_schema() -> None:
    """Create (or recreate) all views in the DuckDB file.

    Safe to call multiple times — views are replaced with CREATE OR REPLACE.
    """
    db = _db_path()
    db.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(db)) as con:
        # ------------------------------------------------------------------
        # Raw views — point directly at parquet files via glob
        # ------------------------------------------------------------------

        # Play-by-play (one parquet per season, glob merges them)
        pbp_glob = _glob("pbp")
        if not list((RAW_DIR / "pbp").glob("*.parquet")):
            logger.warning("No PBP parquets found — pbp_raw view will be empty")
        con.execute(f"""
            CREATE OR REPLACE VIEW pbp_raw AS
            SELECT * FROM read_parquet('{pbp_glob}')
        """)

        for dataset in ("schedules", "rosters", "player_stats", "snap_counts",
                        "injuries", "depth_charts", "participation"):
            g = _glob(dataset)
            view = f"{dataset}_raw"
            files = list((RAW_DIR / dataset).glob("*.parquet")) if (RAW_DIR / dataset).exists() else []
            if files:
                con.execute(f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_parquet('{g}')")
                logger.debug("Created view %s", view)
            else:
                logger.debug("Skipping %s (no parquets on disk yet)", view)

        # Static metadata views
        players_path = str(RAW_DIR / "players_meta" / "players_meta.parquet")
        teams_path = str(RAW_DIR / "teams_meta" / "teams_meta.parquet")

        if Path(players_path).exists():
            con.execute(f"CREATE OR REPLACE VIEW players_meta AS SELECT * FROM read_parquet('{players_path}')")
        if Path(teams_path).exists():
            con.execute(f"CREATE OR REPLACE VIEW teams_meta AS SELECT * FROM read_parquet('{teams_path}')")

        # ------------------------------------------------------------------
        # Processed views — point at derived parquets (built by transform.py)
        # ------------------------------------------------------------------

        for table in (
            "team_season_summary",
            "team_weekly_summary",
            "player_season_summary",
            "player_weekly_summary",
            "play_index",
            "metric_percentiles",
            "team_identity",
        ):
            p = processed_path(table)
            if p.exists():
                con.execute(
                    f"CREATE OR REPLACE VIEW {table} AS SELECT * FROM read_parquet('{p}')"
                )
                logger.debug("Created processed view %s", table)

        logger.info("DuckDB schema built: %s", db)


def rebuild_processed_views() -> None:
    """Refresh processed views after a metrics rebuild."""
    build_schema()


def table_exists(name: str) -> bool:
    """Return True if a view or table with this name exists in the DB."""
    try:
        with get_connection(read_only=True) as con:
            result = con.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?", [name]
            ).fetchone()
            return (result[0] if result else 0) > 0
    except Exception:
        return False


def query(sql: str, read_only: bool = True) -> "duckdb.DuckDBPyRelation":
    """Execute a SQL query and return the relation (use .df() or .pl() to fetch)."""
    con = get_connection(read_only=read_only)
    return con.sql(sql)
