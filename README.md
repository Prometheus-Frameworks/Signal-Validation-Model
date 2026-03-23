# Signal Validation Model

Signal Validation Model is a research-grade Python scaffold for validating whether **prior-season wide receiver signals** would have identified **next-season fantasy football breakouts**.

## Repository purpose

This repository is **not** a live projection engine, ranking app, or production forecasting service. It is a historical signal-validation and backtesting system designed to answer questions like:

- Which prior-season indicators were available before the next season began?
- Would those signals have identified future breakout wide receivers?
- How should candidate rankings and validation summaries be produced without future leakage?

PR1 intentionally shipped an honest scaffold:

- typed schemas for research tables
- timestamp-safe placeholder backtest flow
- mock data only
- deterministic placeholder scoring
- example output artifacts
- tests for validation, leakage boundaries, and determinism

PR2 extends the repository with deterministic historical WR ingestion and canonical processed research tables while preserving the same no-leakage boundaries.

PR3 adds a deterministic WR label engine and joined validation dataset for season-over-season breakout evaluation.

No predictive-power claims are made in this repository.

## Current scope

The repository remains limited to:

- **Position:** Wide receivers (WR)
- **Research posture:** historical validation only
- **Ingestion:** preferred TIBER-Data exports/APIs normalized into `data/raw/`, with an explicit local-builder fallback
- **Processed outputs:** canonical weekly, season, feature-season, and outcome-season tables

Still out of scope:

- projection generation
- ML training
- live APIs or databases
- breakout label engine APIs beyond deterministic WR validation outputs

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
signal-validation run-scaffold
signal-validation build-real-wr-history --source preferred --tiber-export-path /path/to/tiber-data/wr_player_weekly_history.csv
signal-validation build-wr-tables --input data/raw/player_weekly_history.csv
signal-validation build-wr-labels --processed-dir data/processed --output-dir outputs/validation_reports
signal-validation enrich-wr-cohorts --processed-dir data/processed --validation-dataset outputs/validation_reports/wr_validation_dataset.csv --output-dir outputs/validation_reports
signal-validation enrich-wr-role --processed-dir data/processed --validation-dataset outputs/validation_reports/wr_validation_dataset_enriched.csv --output-dir outputs/validation_reports
signal-validation compare-wr-recipes --validation-dataset outputs/validation_reports/wr_validation_dataset_role_enriched.csv --output-dir outputs
signal-validation build-wr-case-study --validation-dataset outputs/validation_reports/wr_validation_dataset_role_enriched.csv --comparison-summary outputs/validation_reports/wr_recipe_comparison_summary.json --candidate-dir outputs/candidate_rankings --output-dir outputs/case_studies --feature-season 2024 --outcome-season 2025
```

## Real data build

Preferred path:

```bash
signal-validation build-real-wr-history --source preferred --tiber-export-path /path/to/tiber-data/wr_player_weekly_history.csv
signal-validation build-wr-tables --input data/raw/player_weekly_history.csv
```

Fallback/bootstrap path:

```bash
signal-validation build-real-wr-history --source local-builder
signal-validation build-wr-tables --input data/raw/player_weekly_history.csv
```

The TIBER-Data adapter writes `data/raw/player_weekly_history.csv` plus `data/raw/player_weekly_history.provenance.json`, preserves optional columns when supplied, and prints the exact source used so the repository never switches sources silently.

The legacy `scripts/build_real_wr_data.py` path remains available for direct bootstrap use and also supports `--seasons` when an explicit fallback season list is needed.

See `docs/REAL_DATA_INGESTION.md` and `docs/TIBER_DATA_ADAPTER.md` for source mapping, validation rules, provenance, and architecture.

The historical ingestion command writes deterministic canonical outputs to `data/processed/` by default:

- `wr_player_weeks.csv`
- `wr_player_seasons.csv`
- `wr_feature_seasons.csv`
- `wr_outcome_seasons.csv`

The WR label command writes deterministic validation artifacts to:

- `outputs/validation_reports/wr_validation_dataset.csv`
- `outputs/validation_reports/wr_breakout_labels.csv`
- `outputs/validation_reports/wr_label_summary.json`
- `outputs/validation_reports/wr_label_examples.md`

The WR scoring command writes deterministic PR4 artifacts to:

- `outputs/candidate_rankings/wr_candidate_rankings.csv`
- `outputs/candidate_rankings/wr_signal_component_scores.csv`
- `outputs/validation_reports/wr_signal_validation_summary.json`
- `outputs/validation_reports/wr_top_candidates.md`
- `outputs/validation_reports/wr_false_positives.md`
- `outputs/validation_reports/wr_false_negatives.md`

The WR recipe comparison command writes deterministic PR5/PR6 artifacts to:

- `outputs/validation_reports/wr_recipe_comparison_summary.json`
- `outputs/validation_reports/wr_recipe_comparison_table.csv`
- `outputs/validation_reports/wr_best_recipe_candidates.md`
- `outputs/validation_reports/wr_recipe_failure_modes.md`
- `outputs/candidate_rankings/wr_candidate_rankings_<recipe>.csv`

The WR role enrichment command writes deterministic PR8 artifacts to:

- `outputs/validation_reports/wr_validation_dataset_role_enriched.csv`
- `outputs/validation_reports/wr_role_enrichment_summary.json`
- `outputs/validation_reports/wr_role_examples.md`

The WR case-study command writes deterministic PR7 artifacts to:

- `outputs/case_studies/wr_breakout_case_study_<feature>_to_<outcome>.md`
- `outputs/case_studies/wr_breakout_hits_<feature>_to_<outcome>.csv`
- `outputs/case_studies/wr_breakout_false_positives_<feature>_to_<outcome>.csv`
- `outputs/case_studies/wr_breakout_false_negatives_<feature>_to_<outcome>.csv`
- `outputs/case_studies/wr_recipe_winner_<feature>_to_<outcome>.json`
- `outputs/case_studies/wr_signal_patterns_<feature>_to_<outcome>.md`

The scaffold command still writes deterministic mock outputs to:

- `outputs/candidate_rankings/`
- `outputs/validation_reports/`

## Documentation

- `docs/MODEL_SCOPE.md`
- `docs/BREAKOUT_LABELS.md`
- `docs/LABEL_ENGINE.md`
- `docs/FEATURE_SCHEMA.md`
- `docs/SIGNAL_SCORE.md`
- `docs/RECIPE_COMPARISON.md`
- `docs/BACKTEST_PROTOCOL.md`
- `docs/DATA_CONTRACT.md`
- `docs/CANONICAL_TABLES.md`
- `docs/REAL_DATA_INGESTION.md`
- `docs/TIBER_DATA_ADAPTER.md`
- `docs/COHORT_BASELINES.md`
- `docs/ROLE_ENRICHMENT.md`
- `docs/CASE_STUDIES.md`

## Current status

This repository now provides:

- the original mock backtest scaffold for placeholder research flow testing,
- deterministic CSV ingestion for historical WR player-week data,
- canonical processed tables that separate prior-season inputs from next-season outcomes,
- deterministic WR breakout labels and validation artifacts built from those canonical tables,
- deterministic cohort-baseline enrichment artifacts for cohort-aware recipe variants,
- deterministic role-and-opportunity enrichment artifacts for role-aware recipe variants,
- deterministic WR recipe comparison artifacts that evaluate multiple explicit score recipes side by side, and
- deterministic season-pair WR case studies that convert the ranking and label outputs into human-readable hit/miss reports.

It still does **not** make production or predictive claims.
