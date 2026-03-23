# TIBER-Data adapter

## Purpose

This repository now treats `Prometheus-Frameworks/TIBER-Data` as the preferred upstream for canonical WR historical/current raw inputs.

The intended long-term repo boundary is:

```text
TIBER-Data -> Signal-Validation-Model -> TIBER-Fantasy
```

- **TIBER-Data** owns deterministic football ingest and downstream-facing data access/export patterns.
- **Signal-Validation-Model** consumes those stable WR player-week inputs, validates/buckets/scores them, and publishes deterministic research outputs.
- **TIBER-Fantasy** is the future product/UI layer and should consume promoted outputs from this repo rather than acting as the raw-data authority.

## Preferred data flow

### Preferred source

`signal-validation build-real-wr-history` now prefers a **TIBER-Data export or read-only API** when one is explicitly configured.

Recommended deterministic path:

```bash
signal-validation build-real-wr-history \
  --source preferred \
  --tiber-export-path /path/to/tiber-data/wr_player_weekly_history.csv
```

Acceptable alternatives:

- `--tiber-export-path https://.../wr_player_weekly_history.json`
- `--tiber-api-url https://.../api/wr-player-weeks`

The adapter normalizes upstream rows into this repo's raw WR contract and writes:

- `data/raw/player_weekly_history.csv`
- `data/raw/player_weekly_history.provenance.json`

Then the normal downstream flow stays unchanged:

```bash
signal-validation build-wr-tables --input data/raw/player_weekly_history.csv
signal-validation build-wr-labels --processed-dir data/processed --output-dir outputs/validation_reports
signal-validation enrich-wr-cohorts --processed-dir data/processed --validation-dataset outputs/validation_reports/wr_validation_dataset.csv --output-dir outputs/validation_reports
signal-validation enrich-wr-role --processed-dir data/processed --validation-dataset outputs/validation_reports/wr_validation_dataset_enriched.csv --output-dir outputs/validation_reports
signal-validation compare-wr-recipes --validation-dataset outputs/validation_reports/wr_validation_dataset_role_enriched.csv --output-dir outputs
signal-validation build-wr-case-study --validation-dataset outputs/validation_reports/wr_validation_dataset_role_enriched.csv --comparison-summary outputs/validation_reports/wr_recipe_comparison_summary.json --candidate-dir outputs/candidate_rankings --output-dir outputs/case_studies --feature-season 2024 --outcome-season 2025
signal-validation export-wr-results --validation-dataset outputs/validation_reports/wr_validation_dataset_role_enriched.csv --comparison-summary outputs/validation_reports/wr_recipe_comparison_summary.json --candidate-dir outputs/candidate_rankings --case-study-dir outputs/case_studies --output-dir outputs/exports --feature-season 2024 --outcome-season 2025
signal-validation build-wr-public-report --exports-dir outputs/exports --case-study-dir outputs/case_studies --comparison-summary outputs/validation_reports/wr_recipe_comparison_summary.json --output-dir outputs/public --feature-season 2024 --outcome-season 2025
signal-validation build-wr-public-findings --public-dir outputs/public --comparison-summary outputs/validation_reports/wr_recipe_comparison_summary.json --case-study-dir outputs/case_studies --exports-dir outputs/exports --feature-season 2024 --outcome-season 2025
```

## Fallback behavior

The legacy `scripts/build_real_wr_data.py` path remains available as a bootstrap/fallback source.

```bash
signal-validation build-real-wr-history --source local-builder
```

Or, to prefer TIBER-Data while remaining explicit about fallback:

```bash
signal-validation build-real-wr-history --source preferred
```

Behavior is intentionally strict:

- `--source preferred`: try TIBER-Data first; if unavailable, print an explicit fallback message and use `local-builder`.
- `--source tiber-data`: require TIBER-Data; do **not** silently fall back.
- `--source local-builder`: use the existing `nfl_data_py` builder directly.

## Provenance rules

Every `build-real-wr-history` run writes a provenance sidecar JSON with:

- `source_type` (`tiber-data-export`, `tiber-data-api`, or `local-builder`)
- `source_location` (artifact path/URL, endpoint, or script path)
- `row_count`
- `seasons`
- `used_fallback`
- `fallback_reason` when fallback occurred

The command also prints a console summary so source switching is never hidden.

## Normalization contract

The adapter normalizes at least these required raw columns:

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

It also preserves optional fields when present and valid:

- `games`
- `active`
- `snap_share`
- `route_participation`
- `target_share`
- `air_yard_share`

Deterministic ordering is enforced as:

1. `season`
2. `week`
3. `player_name`
4. `player_id`

Duplicate `(player_id, season, week)` rows are rejected.

## 2024 -> 2025 season-pair handling

If the supplied TIBER-Data input already contains completed 2025 weekly rows, downstream canonical tables and labels will naturally treat `2024 -> 2025` as a completed retrospective pair instead of a missing-outcome pair.

Signal-Validation-Model no longer needs to behave as if it must independently discover whether the latest season exists. It should consume whatever completed season coverage TIBER-Data has promoted.

## Limitations

- This PR adds a formal adapter, but it does **not** add TIBER-Fantasy integration.
- No UI work is included.
- No scoring changes are introduced beyond field normalization/provenance.
- The adapter currently supports deterministic CSV/JSON exports and JSON API payloads. If TIBER-Data later standardizes another artifact shape, extend the adapter explicitly rather than silently remapping data.
- The local builder remains useful for bootstrap workflows, but it is no longer the preferred architectural upstream when TIBER-Data is available.
