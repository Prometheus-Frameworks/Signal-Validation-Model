# Historical WR raw data contract

PR2 introduces deterministic CSV ingestion for historical wide receiver player-week research data.

## Supported input location

The CLI expects a CSV path, and `data/raw/` is the default staging location for checked-in or manually provided source files.

Example:

```bash
signal-validation build-wr-tables --input data/raw/player_weekly_history.csv
```

## Required columns

The raw CSV must include these headers:

- `player_id`
- `player_name`
- `team`
- `season`
- `week`
- `position`
- `fantasy_points_ppr`
- `targets`
- `receptions`
- `receiving_yards`
- `receiving_tds`

Rows with `position != WR` are rejected.

## Optional columns

The ingestion flow supports these optional headers when they are present:

- `games`
- `active`
- `snap_share`
- `route_participation`
- `target_share`
- `air_yard_share`

Blank optional values are preserved as missing values in the canonical weekly table. The pipeline never fabricates missing share metrics.

## Validation rules

- `season` must be between `1990` and `2100`.
- `week` must be between `1` and `18`.
- `targets`, `receptions`, and touchdowns cannot be negative.
- `receptions` cannot exceed `targets`.
- Share fields, when supplied, must be between `0.0` and `1.0`.
- Duplicate `(player_id, season, week)` rows are rejected.
- Only WR rows are accepted into canonical WR outputs.

## Active-game handling

`games` and `active` are optional. The canonical `week_is_active` flag is resolved as follows:

1. If `active` is present, it wins.
2. Else if `games` is present, `games > 0` is treated as active.
3. Else the row is treated as active because a weekly record exists.

This rule is intentionally simple and explicit so the pipeline remains honest about what the raw file actually supplied.

## Non-goals

This ingestion contract does **not**:

- infer unavailable market-share metrics,
- create breakout labels,
- train projections or ML models,
- define how upstream adapters fetch data from remote APIs or exported artifacts. That behavior now lives in `docs/TIBER_DATA_ADAPTER.md`.
