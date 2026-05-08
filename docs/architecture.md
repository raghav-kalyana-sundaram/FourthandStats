# Architecture

> Placeholder — populated after Phase 0 is complete.

## Pipeline overview

```
nflreadpy (Python)
    ↓ download.py
data/raw/nflverse/*.parquet  (per dataset, per season)
    ↓ schema.py (DuckDB views: pbp_raw, schedules_raw, ...)
    ↓ transform.py + team_metrics.py + player_metrics.py
data/processed/*.parquet  (team_season_summary, player_season_summary, play_index, ...)
    ↓ schema.py (DuckDB views: team_season_summary, player_weekly_summary, ...)
    ↓ percentiles.py + ratings.py + identity.py
data/processed/metric_percentiles.parquet + team_identity.parquet
    ↓ queries/ (DuckDB query helpers)
    ↓ ui/ (Streamlit screens)
User
```

## Key design decisions

- **Parquet-first storage**: all data lives as columnar parquet files on disk; DuckDB reads them in place without loading into memory
- **Pre-computation**: all ratings, percentiles, and identity labels are computed at rebuild time, not on page load
- **Atomic rebuild**: new outputs written to `.tmp/` directory and swapped only after validation passes
- **Single DuckDB file**: `football.duckdb` holds only view definitions — the actual data stays in parquet; the DB can be deleted and recreated from parquet at any time
