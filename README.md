# FourthandStats

A local-first NFL analytics workbench for team identity, player comparison, play-by-play exploration, and instant visualizations. Runs entirely on your machine — no cloud, no accounts, no subscriptions.

---

## What it does

FourthandStats pulls open-source NFL data (via [nflverse](https://nflverse.nflverse.com/)) and builds a set of rich, pre-computed analytics tables you can slice, filter, and explore through a dense, analyst-first Streamlit UI.

- **Team Matrix** — compare every team across EPA, success rate, explosiveness, situational performance, and composite ratings in one scrollable heatmap table
- **Team Board** — deep-dive on a single team's offensive and defensive identity, with evidence trails linking every label back to specific metrics
- **Player Matrix** — position-aware player rankings with heatmap formatting, percentile context, and minimum-sample thresholds
- **Player Board** — production, efficiency, usage, recent form, and team context for any player
- **Compare Board** — edge-matrix comparison of two teams or two players across all key dimensions
- **Visual Lab** — build custom scatter, bar, line, and heatmap charts from any metric combination
- **Play Explorer** — filter and inspect individual plays from the full play-by-play dataset

---

## Screenshots

> _Coming after MVP UI is complete._

---

## Quick start

```bash
# 1. Clone and enter the repo
git clone https://github.com/<your-username>/FourthandStats.git
cd FourthandStats

# 2. Create a virtual environment (uses uv to avoid macOS pip/ensurepip issues)
# Install uv first if needed: brew install uv
uv venv --python 3.11 .venv
source .venv/bin/activate       # macOS / Linux
# .\.venv\Scripts\activate      # Windows

# 3. Install dependencies
uv pip install -r requirements.txt

# 4. Download NFL data (2024–2025 seasons takes ~2–5 min on first run)
python scripts/update_data.py --seasons 2024 2025

# 5. Build metrics and derived tables
python scripts/rebuild_metrics.py

# 6. Validate the data
python scripts/validate_data.py

# 7. Launch the app
python app.py
# or: streamlit run app.py
```

The app opens at **http://localhost:8501** by default.

---

## Data sources

All data comes from the [nflverse](https://nflverse.nflverse.com/) project via [nflreadpy](https://nflreadpy.nflverse.com/):

| Dataset | Coverage | Notes |
|---|---|---|
| Play-by-play (`pbp`) | 1999–present | Core source for EPA, WPA, success rate |
| Schedules | 1999–present | Game results, home/away, scores |
| Rosters | 2001–present | Player-team-season mapping |
| Player stats (weekly) | 1999–present | Aggregated box scores |
| Snap counts | ~2012–present | Offensive + defensive snap shares |
| Injuries | 2009–present | Weekly injury reports |
| Depth charts | 2001–present | Position depth by week |
| Participation | Limited | Personnel groupings (availability varies) |
| Players metadata | All-time | IDs, bio, position |
| Teams metadata | All-time | Abbreviations, names, colors |
| Combine | 1987–present | Athletic testing results |
| Draft picks | 1985–present | Round, pick, team, position |

nflverse data is open-source and free for non-commercial use. See [nflverse licensing](https://github.com/nflverse/nflverse-data).

---

## Architecture

```
FourthandStats/
├── app.py                     # Streamlit entry point
├── config/                    # YAML config + metric definitions
├── data/
│   ├── raw/nflverse/          # Downloaded parquet files (gitignored)
│   ├── processed/             # Derived metric tables (gitignored)
│   ├── cache/                 # Query cache (gitignored)
│   └── manifests/             # Data + build manifests (committed)
├── src/fourthandstats/
│   ├── data/                  # Download, transform, schema, quality, manifest
│   ├── metrics/               # Team metrics, player metrics, ratings, percentiles
│   ├── queries/               # DuckDB query helpers per domain
│   ├── simulations/           # Future: matchup + season simulators
│   ├── ui/                    # Streamlit screen modules
│   └── utils/                 # Paths, logging, time helpers
├── scripts/                   # CLI tools: update_data, rebuild, validate, export
├── tests/                     # pytest test suite
├── saved_views/               # User-saved filter + column configurations
├── exports/                   # Chart PNGs, CSV exports, HTML reports
└── docs/                      # Architecture, metric definitions, methodology
```

The pipeline is:

```
nflreadpy → raw parquet → DuckDB views → derived metric parquets → DuckDB views → Streamlit
```

All heavy computation (EPA aggregation, percentiles, ratings) happens at rebuild time, not on page load.

---

## Metrics

Key metrics derived from play-by-play EPA:

- **EPA/play** — expected points added per offensive play
- **Success Rate** — % of plays that were successful by down-and-distance standard
- **Explosive Play Rate** — % of plays gaining 12+ yards (rush) or 16+ yards (pass)
- **Composite Ratings** — weighted percentile composites for offense, defense, passing, rushing, explosiveness, situational, recent form, and overall
- **Team Identity Labels** — rule-based tags like `PASS+ / RUN- / EXP+ / REDZONE~`

See `docs/metric_definitions.md` for the full glossary with formulas and source columns.

---

## Example workflows

**Find the most efficient passing offenses in 2024:**
1. Open Team Matrix
2. Filter: Season = 2024, Regular Season only
3. Sort by Pass EPA/play descending
4. Click any row to open Team Board

**Compare two defenses:**
1. Open Team Matrix, multi-select two teams
2. Click "Compare Teams" → Compare Board opens

**Explore 3rd-and-long plays for a team:**
1. Open Play Explorer
2. Filter: Team = SEA, Down = 3, Distance Bucket = Long
3. Sort by EPA descending

---

## How to update data

```bash
# Update current season only
python scripts/update_data.py --current-season

# Specific seasons
python scripts/update_data.py --seasons 2023 2024 2025

# Full historical range
python scripts/update_data.py --seasons 1999-2025

# Then rebuild metrics
python scripts/rebuild_metrics.py

# Or do both at once
python scripts/rebuild_all.py
```

---

## Simulations roadmap

Future phases will add:

- **Matchup simulator** — Monte Carlo game simulation using team ratings + variance
- **Season simulator** — projected standings and playoff odds
- **Playoff bracket simulator**
- **What-if team simulator** — swap roster components and re-simulate

See `docs/simulation_methodology.md` for the planned approach.

---

## Limitations

- **Defensive player stats** are limited by available free data. Tackles and box-score stats are available; pressures and coverage are not in free nflverse data. Player grades in this domain are low-confidence and flagged.
- **Pre-2012 seasons** lack snap count data, limiting usage metrics for early seasons.
- **Participation data** (personnel groupings) has spotty availability and is used opportunistically.
- **EPA is model-dependent** — the nflverse EPA model is well-validated but has known edge cases (e.g., end-of-half situations, garbage time).
- **All data is local** — no live score updates, no real-time feed. Run `update_data.py` after each week.

---

## License

MIT — see [LICENSE](LICENSE).
