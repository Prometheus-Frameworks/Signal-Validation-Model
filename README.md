# Signal Validation Model

Signal Validation Model is a research-grade Python scaffold for validating whether **prior-season wide receiver signals** would have identified **next-season fantasy football breakouts**.

## Repository purpose

This repository is **not** a live projection engine, ranking app, or production forecasting service. It is a historical signal-validation and backtesting system designed to answer questions like:

- Which prior-season indicators were available before the next season began?
- Would those signals have identified future breakout wide receivers?
- How should candidate rankings and validation summaries be produced without future leakage?

PR1 intentionally ships an honest scaffold:

- typed schemas for research tables
- timestamp-safe placeholder backtest flow
- mock data only
- deterministic placeholder scoring
- example output artifacts
- tests for validation, leakage boundaries, and determinism

No predictive-power claims are made in this scaffold.

## V1 scope

V1 is limited to:

- **Position:** Wide receivers (WR)
- **Feature season:** 2024
- **Outcome season:** 2025
- **Goal:** Validate whether prior-season signals could have surfaced next-season breakout candidates

See the detailed scope and methodology documents in `docs/`:

- `docs/MODEL_SCOPE.md`
- `docs/BREAKOUT_LABELS.md`
- `docs/FEATURE_SCHEMA.md`
- `docs/BACKTEST_PROTOCOL.md`

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
signal-validation run-scaffold
```

The scaffold command writes deterministic mock outputs to:

- `outputs/candidate_rankings/`
- `outputs/validation_reports/`

## Current status

This repository currently provides a **scaffold-only** implementation. The CLI and backtest pipeline are runnable, but they operate on mock data and placeholder research logic intended to support future PRs.
