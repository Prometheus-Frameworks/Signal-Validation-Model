# WR Label Engine

PR3 adds a deterministic label engine for **WR season-N -> season-N+1** validation.

## Inputs and canonical join

The label engine reads only these processed tables:

- `data/processed/wr_feature_seasons.csv`
- `data/processed/wr_outcome_seasons.csv`

They are joined on:

- `player_id`
- `feature_season`
- `outcome_season`

The join is a **left join from feature rows to outcome rows**.

That means every prior-season feature row remains in the validation dataset, even when the next-season outcome row is missing. Missing next-season rows are marked with:

- `has_valid_outcome = false`
- `breakout_reason = missing_outcome`
- breakout labels set to `false`

## Canonical output fields

The joined validation dataset includes stable support fields for PR4 and later evaluation work:

- `feature_season`
- `outcome_season`
- `feature_ppg`
- `outcome_ppg`
- `ppg_delta_next_season`
- `feature_finish`
- `outcome_finish`
- `finish_delta_next_season`
- `expected_ppg_baseline`
- `actual_minus_expected_ppg`
- `breakout_reason`
- `is_new_fantasy_starter`
- `has_valid_outcome`

Additional stable context columns such as team, games played, targets per game, and label booleans are also written to the output CSV.

## Deterministic finish rules

`feature_finish` and `outcome_finish` are computed within each season using only season-local data.

Ordering is:

1. higher `ppg`
2. higher `total_ppr`
3. ascending `player_id`

This gives the repository an explicit and reproducible answer for top-24 cutoff questions, including ties at the boundary.

## Label definitions

### `breakout_label_default`

The default WR breakout label is `true` when the player has a valid outcome and **any** of the following deterministic triggers fires:

1. **Top-24 jump**: next-season finish is top 24 and prior-season finish was not top 24.
2. **PPG jump**: next-season `outcome_ppg - feature_ppg > 3.0`.
3. **Beat expected baseline**: next-season `actual_minus_expected_ppg > 2.0`.

Reason priority is deterministic:

1. `top24_jump`
2. `ppg_jump`
3. `beat_expected_baseline`
4. `no_breakout_trigger`
5. `missing_outcome`

### `breakout_label_ppg_jump`

`true` only when:

- `has_valid_outcome = true`, and
- `ppg_delta_next_season > 3.0`

The threshold is **strictly greater than** 3.0. Equality does not count as a breakout.

### `breakout_label_top24_jump`

`true` only when:

- `has_valid_outcome = true`, and
- `outcome_finish <= 24`, and
- `feature_finish > 24`

This also powers `is_new_fantasy_starter`, which marks a player who newly enters the fantasy-starter range.

## Expected PPG baseline

The baseline is intentionally simple, explicit, and non-ML.

```text
expected_ppg_baseline =
    0.7 * feature_ppg
  + 0.2 * feature_targets_per_game
  + 10.0 * feature_target_share
```

Where:

- `feature_target_share` comes from `avg_target_share` in `wr_feature_seasons.csv`
- missing target share is treated as `0.0`

This baseline is not meant to be a projection model. It is just a deterministic benchmark for asking whether next-season scoring materially exceeded a role-aware prior-season expectation.

## Why breakout is multi-definition

There is no single universally correct breakout definition.

Different analysts care about different outcomes:

- fantasy starter emergence
- raw scoring growth
- outperformance versus prior role expectations

This repository therefore keeps:

- one **canonical default** label for broad validation work, and
- alternate deterministic variants for sensitivity analysis

That design is meant to help PR4 score and rank candidates against more than one outcome framing without changing the raw processed tables.

## Leakage guardrails

The label engine follows strict no-leakage boundaries:

- all candidate inputs come from `wr_feature_seasons.csv`
- all realized outcomes come from `wr_outcome_seasons.csv`
- labels are built only after the feature/outcome join
- no outcome-season columns are fed back into the feature table
- no ML training or learned weights are used
- missing outcomes remain explicit instead of being imputed as successes

## Limitations

The deterministic baseline is intentionally limited:

- it does not model aging, team changes, injuries, or quarterback context
- it does not use ADP, market expectations, or depth-chart information
- it cannot distinguish sustainable skill growth from one-season variance
- its weights are hand-set research constants, not learned parameters

That is acceptable for PR3 because the goal is to create an honest, reproducible validation target surface—not to claim predictive accuracy.

## CLI

Build WR labels and validation artifacts with:

```bash
signal-validation build-wr-labels \
  --processed-dir data/processed \
  --output-dir outputs/validation_reports
```

This writes:

- `outputs/validation_reports/wr_breakout_labels.csv`
- `outputs/validation_reports/wr_validation_dataset.csv`
- `outputs/validation_reports/wr_label_summary.json`
- `outputs/validation_reports/wr_label_examples.md`
