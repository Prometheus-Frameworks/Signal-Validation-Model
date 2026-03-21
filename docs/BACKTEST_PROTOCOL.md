# Backtest Protocol

## Goal

The backtest protocol ensures that the research workflow answers a fair historical question:

> If we stood at the start of the 2025 season with only prior information, how would a ranking system have scored 2025 WR breakout candidates?

## Timestamp-safe rules

1. **Feature freeze**: only information available through the end of the feature season may be used.
2. **One-step horizon**: PR1 validates `Y` features against `Y+1` outcomes.
3. **No label leakage**: breakout labels are created from the outcome season and never fed back into features.
4. **Deterministic ranking**: scaffold scoring must be reproducible on repeated runs.
5. **Separation of concerns**: feature creation, labeling, scoring, and report generation remain modular.

## PR1 placeholder workflow

1. Load mock 2024 WR feature rows.
2. Load mock 2025 WR outcome rows.
3. Assign proposed v1 breakout labels using placeholder rule logic.
4. Compute a deterministic placeholder breakout signal score from prior-season features.
5. Emit candidate rankings and validation summaries.

## Evaluation framing

PR1 does not attempt to prove predictive power. Instead, it demonstrates:

- repository structure
- schema boundaries
- timestamp-safe interfaces
- reproducible placeholder outputs

## Future protocol extensions

Later PRs may add:

- multiple seasons and rolling backtests
- cohort stratification
- precision/recall metrics by threshold
- calibration summaries
- feature provenance tracking
- richer artifact generation
