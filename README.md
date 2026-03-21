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
- **Ingestion:** local CSV files under `data/raw/` or another explicit path
- **Processed outputs:** canonical weekly, season, feature-season, and outcome-season tables

Still out of scope:

- projection generation
- ML training
- live APIs or databases
- role/opportunity integrations
- breakout label engine APIs beyond deterministic WR validation outputs

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
signal-validation run-scaffold
signal-validation build-wr-tables --input data/raw/player_weekly_history.csv
signal-validation build-wr-labels --processed-dir data/processed --output-dir outputs/validation_reports
signal-validation score-wr-candidates --validation-dataset outputs/validation_reports/wr_validation_dataset.csv --output-dir outputs
signal-validation compare-wr-recipes --validation-dataset outputs/validation_reports/wr_validation_dataset.csv --output-dir outputs
```

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

The WR recipe comparison command writes deterministic PR5 artifacts to:

- `outputs/validation_reports/wr_recipe_comparison_summary.json`
- `outputs/validation_reports/wr_recipe_comparison_table.csv`
- `outputs/validation_reports/wr_best_recipe_candidates.md`
- `outputs/validation_reports/wr_recipe_failure_modes.md`
- `outputs/candidate_rankings/wr_candidate_rankings_<recipe>.csv`

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

## Current status

This repository now provides:

- the original mock backtest scaffold for placeholder research flow testing,
- deterministic CSV ingestion for historical WR player-week data,
- canonical processed tables that separate prior-season inputs from next-season outcomes,
- deterministic WR breakout labels and validation artifacts built from those canonical tables,
- deterministic WR signal scoring and candidate ranking artifacts evaluated against the PR3 breakout labels.
- deterministic WR recipe comparison artifacts that evaluate multiple explicit score recipes side by side.

It still does **not** make production or predictive claims.
