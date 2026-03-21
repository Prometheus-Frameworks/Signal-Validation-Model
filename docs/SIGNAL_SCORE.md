# WR Signal Score

## Philosophy

PR4 adds a deterministic scoring layer that answers a narrow historical-validation question:

> Using only information available after the feature season ended, which WRs would this rules-based score have ranked as the strongest next-season breakout candidates?

The score is intentionally:

- deterministic,
- transparent,
- modular,
- editable, and
- designed for research validation before any future ML comparison layer.

It is **not** a claim of predictive accuracy, a live projection model, or a hidden black-box ranking system.

## Inputs

The scoring command reads the PR3 joined validation dataset:

- `outputs/validation_reports/wr_validation_dataset.csv`

The implementation lives in:

- `src/scoring/wr_signal_score.py`

## Feature-only scoring contract

The score uses only feature-season fields:

- `feature_games_played`
- `feature_total_ppr`
- `feature_ppg`
- `feature_finish`
- `feature_targets_per_game`
- `feature_target_share`
- `expected_ppg_baseline`

Outcome-season and delta columns may exist in the joined validation dataset, but the scoring path extracts a feature-only view before calculating component values. Changing outcome columns does not change the score.

## Component families

Each component is normalized onto a `0-100` scale with explicit clipping:

- `scale(value, floor, ceiling) = clip((value - floor) / (ceiling - floor), 0, 1) * 100`

### 1. Usage signal

Measures how much stable passing-game opportunity a player already owned.

```text
usage_signal =
  0.55 * scale(feature_targets_per_game, 4.0, 10.0)
+ 0.45 * scale(feature_target_share, 0.12, 0.30)
```

### 2. Efficiency signal

Rewards productive per-target conversion and solid fantasy production on the feature-season workload.

```text
feature_ppg_per_target = feature_total_ppr / (feature_targets_per_game * feature_games_played)

efficiency_signal =
  0.60 * scale(feature_ppg_per_target, 0.8, 2.5)
+ 0.40 * scale(feature_ppg, 6.0, 18.0)
```

### 3. Development signal

Rewards players who were already near fantasy relevance while still showing room to outgrow their prior scoring baseline.

```text
development_signal =
  0.50 * scale(48 - feature_finish, 0.0, 36.0)
+ 0.50 * scale(expected_ppg_baseline - feature_ppg, 0.0, 4.0)
```

### 4. Stability signal

Rewards players who stayed on the field and banked a usable feature-season workload.

```text
stability_signal =
  0.65 * scale(feature_games_played, 8.0, 17.0)
+ 0.35 * scale(feature_total_ppr, 80.0, 260.0)
```

### 5. Penalty signal

Penalizes profiles that are poor breakout targets for this specific research question:

- players already finishing as top-12 WRs,
- players with shaky availability, and
- players with very thin target share.

```text
penalty_signal =
  0.60 * scale(12 - feature_finish, 0.0, 12.0)
+ 0.25 * scale(11 - feature_games_played, 0.0, 11.0)
+ 0.15 * scale(0.14 - feature_target_share, 0.0, 0.14)
```

## Final score

```text
wr_signal_score =
  0.35 * usage_signal
+ 0.20 * efficiency_signal
+ 0.20 * development_signal
+ 0.15 * stability_signal
- 0.10 * penalty_signal
```

All weights are explicit constants in code so future PRs can compare alternative recipes without hidden logic.

## Tie-breaking rules

Players are ranked within each `feature_season` using this deterministic sort order:

1. higher `wr_signal_score`
2. higher `usage_signal`
3. higher `efficiency_signal`
4. higher `development_signal`
5. higher `stability_signal`
6. lower `penalty_signal`
7. alphabetical `player_id`

This guarantees stable reproducible ranks even when scores tie.

## Output artifacts

Running the PR4 command writes:

- `outputs/candidate_rankings/wr_candidate_rankings.csv`
- `outputs/candidate_rankings/wr_signal_component_scores.csv`
- `outputs/validation_reports/wr_signal_validation_summary.json`
- `outputs/validation_reports/wr_top_candidates.md`
- `outputs/validation_reports/wr_false_positives.md`
- `outputs/validation_reports/wr_false_negatives.md`

## Evaluation summary

The validation summary reports:

- candidate count
- evaluated candidate count
- breakout count
- precision@10 / @20 / @30
- recall@10 / @20 / @30
- average breakout rank
- median breakout rank
- false positives in top 20
- false negatives outside top 30

Top-N metrics are computed only on rows with valid next-season outcomes, while preserving the original within-season ranks assigned by the feature-only score.

## Why deterministic scoring comes before ML

A deterministic score is useful before any ML layer because it:

- proves the repo can rank candidates without leakage,
- exposes every assumption to review,
- creates a reproducible baseline for later comparisons,
- makes failure modes easy to inspect in false-positive and false-negative reports, and
- avoids overstating certainty before more sophisticated modeling is justified.
