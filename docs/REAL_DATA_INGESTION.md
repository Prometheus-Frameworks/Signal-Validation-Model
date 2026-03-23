# Real WR data ingestion

## Purpose

Signal-Validation-Model now supports two explicit raw-input paths for WR weekly history:

1. **Preferred:** a formal `TIBER-Data` adapter that consumes a stable export or read-only API.
2. **Fallback/bootstrap:** the existing local `nfl_data_py` builder in `scripts/build_real_wr_data.py`.

The repository should now align around:

```text
TIBER-Data -> Signal-Validation-Model -> TIBER-Fantasy
```

See `docs/TIBER_DATA_ADAPTER.md` for architecture, provenance, and fallback behavior.

## Preferred command

```bash
signal-validation build-real-wr-history --source preferred --tiber-export-path /path/to/tiber-data/wr_player_weekly_history.csv
```

This writes:

- `data/raw/player_weekly_history.csv`
- `data/raw/player_weekly_history.provenance.json`

Then ingest the normalized raw CSV into canonical processed tables:

```bash
signal-validation build-wr-tables --input data/raw/player_weekly_history.csv
```

## Fallback/bootstrap command

```bash
signal-validation build-real-wr-history --source local-builder
```

This path still uses `nfl_data_py.import_weekly_data(...)` and remains available for bootstrap or local recovery workflows.

## Column mapping

Both paths ultimately write the same raw contract described in `docs/DATA_CONTRACT.md`.

Required output columns:

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

Optional passthrough columns when present:

- `games`
- `active`
- `snap_share`
- `route_participation`
- `target_share`
- `air_yard_share`

## Validation and provenance

The ingestion flow enforces:

- duplicate `(player_id, season, week)` rejection,
- WR-only rows,
- deterministic ordering, and
- explicit provenance recording.

The provenance sidecar records:

- `source_type`
- `source_location`
- `row_count`
- `seasons`
- `used_fallback`
- `fallback_reason` when fallback occurs

## Local builder note

The local builder is retained intentionally, but it is no longer the preferred architectural source when a TIBER-Data artifact or endpoint is available.
