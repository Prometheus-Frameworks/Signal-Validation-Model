# Feature Schema

## Philosophy

Features in this repository must represent information that would have been available after the feature season ended and before the outcome season began.

For PR1, that means **2024-derived features used to rank 2025 breakout candidates**.

## Proposed v1 feature groups

### Identity and timestamp fields

- `player_id`
- `player_name`
- `position`
- `feature_season`
- `target_outcome_season`
- `data_through_season`
- `prior_team`
- `age_on_sept_1`

### Usage and opportunity fields

- `games_played`
- `routes_run`
- `targets`
- `target_share`
- `air_yards_share`
- `first_read_target_share`
- `red_zone_target_share`

### Efficiency and play-quality fields

- `yards_per_route_run`
- `explosive_play_rate`

### Baseline production fields

- `feature_season_ppr_points`
- `feature_season_ppr_points_per_game`

## Explicit exclusions for PR1

The following are excluded from PR1 code and should not be introduced as feature inputs in this scaffold:

- any 2025 realized performance field
- injury outcomes that were only known during or after 2025
- post-draft or in-season information beyond the designated ranking timestamp
- manually leaked labels disguised as feature columns

## Interface-level leakage rule

Every feature row must satisfy:

- `target_outcome_season = feature_season + 1`
- `data_through_season <= feature_season`

This is enforced in schema validation in PR1.
