# Model Scope

## Problem definition

This repository solves a **historical research problem**:

> Given only information available after the 2024 season and before the 2025 season, which wide receivers would have been surfaced as likely 2025 breakout candidates?

The objective is to validate prior-season signals against next-season outcomes in a timestamp-safe way.

## What this repository is

This repository is a:

- research environment
- backtesting framework
- signal-validation engine
- candidate-ranking and validation-reporting scaffold

## What this repository is not

This repository is **not**:

- a live weekly projection engine
- a DFS optimizer
- a rest-of-season ranking tool
- a production API
- a training pipeline for PR1

## Signal validation vs. point projection

### Signal validation

Signal validation asks:

- Did a player exhibit measurable indicators before the breakout happened?
- Were those indicators observable at the time?
- If we ranked players using those indicators, did future breakouts appear near the top?

The output is generally:

- ranked candidates
- labeled outcomes
- evaluation summaries
- cohort-level insights

### Point projection

Point projection asks:

- How many fantasy points will a player score?
- What is the expected distribution of weekly or seasonal production?
- How should players be ordered for drafts or weekly start/sit decisions?

That is **outside PR1 scope**.

## V1 research boundary

PR1 constrains the problem to keep the foundation rigorous:

- only WRs
- only 2024 feature inputs
- only 2025 outcomes
- only timestamp-safe features that would be known before the 2025 season
- only mock data and placeholder scoring in code

## Design principles

1. **No future leakage**: every feature must be available by the ranking timestamp.
2. **Honest scaffolding**: placeholder behavior must be clearly labeled.
3. **Deterministic outputs**: mock research runs should be reproducible.
4. **Modularity**: labels, features, scoring, backtests, and reporting must be separable.
5. **Future extensibility**: later PRs can add real ingestion, ARC-derived features, role-opportunity features, and richer reporting.
