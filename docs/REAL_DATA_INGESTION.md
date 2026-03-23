# Real WR data ingestion

## Purpose

PR12 adds a simple, inspectable builder for a real raw historical WR weekly file at `data/raw/player_weekly_history.csv`.

The builder intentionally uses `nfl_data_py.import_weekly_data()` as the primary source and does **not** aggregate play-by-play data in this flow.

## Source

Primary source:

- `nfl_data_py.import_weekly_data([2020, 2021, 2022, 2023, 2024], ...)`

Underlying nflverse weekly player-stat files are season-partitioned parquet releases that `nfl_data_py` reads through `import_weekly_data()`.

## Column mapping

The raw output file is written to the repository's historical ingestion contract in `docs/DATA_CONTRACT.md`.

| Output column | nfl_data_py weekly column | Notes |
| --- | --- | --- |
| `player_id` | `player_id` | Direct mapping. |
| `player_name` | `player_name` | Direct mapping. |
| `team` | `recent_team` | Current team value from the weekly feed. |
| `season` | `season` | Filtered to `2020`-`2024`. |
| `week` | `week` | Preserved as the weekly index from the source. |
| `position` | `position` | Filtered to `WR` only. |
| `fantasy_points_ppr` | `fantasy_points_ppr` | Direct mapping. |
| `targets` | `targets` | Direct mapping. |
| `receptions` | `receptions` | Direct mapping. |
| `receiving_yards` | `receiving_yards` | Direct mapping. |
| `receiving_tds` | `receiving_tds` | Direct mapping. |
| `games` | `games` if present | Left blank when unavailable in the weekly feed. |
| `snap_share` | `snap_share` if present | Left blank when unavailable. |
| `route_participation` | `route_participation` if present | Left blank when unavailable. |
| `target_share` | `target_share` if present | Left blank when unavailable. |
| `air_yard_share` | `air_yard_share` if present | Left blank when unavailable. |

## Assumptions

- The build reads regular-season weekly data only when a `season_type` column is present.
- Optional columns are preserved only when they are actually present in the weekly source returned by `nfl_data_py`.
- Missing optional values stay blank. The script does not fabricate market-share or participation metrics.
- Duplicate `(player_id, season, week)` rows are treated as a hard validation error.
- Output ordering is deterministic: `season`, `week`, `player_name`, `player_id`.

## Validation checks

The builder enforces the following before writing the CSV:

- required output columns exist in the expected order,
- only WR rows are present,
- seasons are limited to `2020`-`2024`,
- no duplicate `(player_id, season, week)` keys remain,
- `targets >= receptions`,
- no negative `targets`, `receptions`, or `receiving_tds`, and
- optional share columns remain within `[0.0, 1.0]` when populated.

## Build command

```bash
python scripts/build_real_wr_data.py
```

Optional custom output path:

```bash
python scripts/build_real_wr_data.py --output /tmp/player_weekly_history.csv
```

## Expected follow-on command

After the raw CSV is built, the repository pipeline should ingest it with:

```bash
signal-validation build-wr-tables --input data/raw/player_weekly_history.csv
```
