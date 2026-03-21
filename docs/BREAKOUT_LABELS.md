# Breakout Labels

This repository now contains **two different breakout-label contexts**:

1. the original PR1 scaffold placeholder rule used only by the mock backtest flow, and
2. the PR3 deterministic WR label engine used for canonical season-N -> season-N+1 validation outputs.

## Current canonical WR label engine

For real processed WR validation work, use:

- `src/labels/wr_breakouts.py`
- `docs/LABEL_ENGINE.md`

That engine joins `wr_feature_seasons.csv` to `wr_outcome_seasons.csv` and writes deterministic label artifacts under `outputs/validation_reports/`.

## Legacy scaffold placeholder label

The mock scaffold path still keeps a simple placeholder breakout rule in `src/labels/rules.py` so the original scaffold tests and demonstration flow continue to work.

That placeholder rule is intentionally limited and should be treated as a mock research stub, not the repository's canonical WR label definition.

## Why both exist

The scaffold rule remains useful for:

- preserving PR1 behavior
- keeping the mock backtest flow stable
- testing the repository's original end-to-end placeholder pipeline

The PR3 label engine exists for:

- real deterministic WR feature/outcome joins
- canonical validation dataset creation
- multi-definition breakout labeling with explicit leakage guardrails
