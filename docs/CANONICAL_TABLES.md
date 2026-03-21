# Canonical WR processed tables

PR2 builds four deterministic CSV outputs under `data/processed/`.

## Output files

- `wr_player_weeks.csv`
- `wr_player_seasons.csv`
- `wr_feature_seasons.csv`
- `wr_outcome_seasons.csv`

## `wr_player_weeks.csv`

One row per `player_id + season + week`.

This table is the normalized WR-only weekly layer. It preserves weekly box-score fields plus optional participation/share columns when they were provided by the raw data source.

Key fields:

- player identity and team context
- season and week
- `week_is_active`
- weekly PPR points, targets, receptions, yards, touchdowns
- optional `snap_share`, `route_participation`, `target_share`, `air_yard_share`

## `wr_player_seasons.csv`

One row per `player_id + season`.

This table deterministically aggregates weekly rows into season rollups:

- `games_played`: count of active weeks
- `total_ppr` and `ppg`
- `spike_week_rate`: active-week rate where `ppr_points >= 20.0`
- `dud_week_rate`: active-week rate where `ppr_points < 5.0`
- volume totals and per-game rates for targets, receptions, yards, touchdowns
- optional averages for share and participation fields, based only on weeks where the optional metric was present

No breakout logic is embedded here; this is a canonical season summary table only.

## `wr_feature_seasons.csv`

One row per `player_id + season`, representing only prior-season inputs that are eligible for later signal research.

Guardrails:

- contains `target_outcome_season = season + 1`
- contains `data_through_season = season`
- contains no `outcome_*`, `label_*`, or future-derived columns
- contains only same-season descriptive metrics derived from `wr_player_seasons.csv`

This is the timestamp-safe feature surface for future PRs.

## `wr_outcome_seasons.csv`

One row per `player_id + feature_season + outcome_season` where `outcome_season = feature_season + 1`.

This table is a shifted evaluation table derived from season rows. Example:

- the 2024 season summary is emitted as `feature_season = 2023`, `outcome_season = 2024`

That shape lets future PRs cleanly join:

- `wr_feature_seasons.player_id`
- `wr_feature_seasons.season`

onto:

- `wr_outcome_seasons.player_id`
- `wr_outcome_seasons.feature_season`

without recomputing season alignment during labeling or reporting.

## Leakage guardrails

The pipeline enforces the following anti-leakage checks:

- WR-only filtering at ingestion time
- stable primary keys for weekly, season, feature, and outcome tables
- strict column ordering for deterministic outputs
- feature rows cannot include columns with `outcome`, `label`, or `future` in the name
- feature rows cannot reference data beyond their own season
- outcome rows must always point exactly one season ahead of the matching feature season

These tables intentionally separate inputs from evaluation targets so later PRs can build labels and validation reports without crossing timestamp boundaries.
