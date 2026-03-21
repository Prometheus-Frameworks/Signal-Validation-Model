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
- breakout label engine overhauls

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
signal-validation run-scaffold
signal-validation build-wr-tables --input data/raw/player_weekly_history.csv
```

The historical ingestion command writes deterministic canonical outputs to `data/processed/` by default:

- `wr_player_weeks.csv`
- `wr_player_seasons.csv`
- `wr_feature_seasons.csv`
- `wr_outcome_seasons.csv`

The scaffold command still writes deterministic mock outputs to:

- `outputs/candidate_rankings/`
- `outputs/validation_reports/`

## Documentation

- `docs/MODEL_SCOPE.md`
- `docs/BREAKOUT_LABELS.md`
- `docs/FEATURE_SCHEMA.md`
- `docs/BACKTEST_PROTOCOL.md`
- `docs/DATA_CONTRACT.md`
- `docs/CANONICAL_TABLES.md`

## Current status

This repository now provides:

- the original mock backtest scaffold for placeholder research flow testing,
- deterministic CSV ingestion for historical WR player-week data,
- canonical processed tables that separate prior-season inputs from next-season outcomes.

It still does **not** make production or predictive claims.
