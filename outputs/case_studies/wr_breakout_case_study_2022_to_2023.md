# WR Breakout Case Study: 2022 to 2023

## Executive summary

- Best recipe from the comparison summary: `balanced_conservative` (`wr_signal_score_balanced_conservative_v1`).
- Evaluated 1 of 2 rows for this season pair; 1 rows were excluded because the outcome season is missing.
- Using a surfaced cutoff of top 20, the model produced 0 hits, 1 false positives, and 0 false negatives.
- Actual breakout count for 2023: 0. Hit-rate within surfaced candidates: 0.0000.
- Breakout reasons represented among hits: none.

## Best recipe for this season pair

- Recipe selection is sourced from the deterministic recipe comparison summary, not from the case-study layer.
- Primary metric: `precision_at_20`.
- Tie-breakers: recall_at_20, lowest_average_breakout_rank, recipe_name.
- Pair-level comparison metrics copied from the summary: precision@20=0.0000, recall@20=0.0000, average breakout rank=n/a.

## Top flagged candidates from `balanced_conservative`

| rank | player_name | feature_team | score | breakout_label | breakout_reason |
| ---: | --- | --- | ---: | --- | --- |
| 1 | Alpha Receiver | AAA | 36.0378 | false | no_breakout_trigger |

## Actual breakouts

_No rows in this category._

## Correctly surfaced breakouts

_No rows in this category._

## False positives

| rank | player_name | feature_team | score | breakout_reason | outcome_ppg | outcome_finish | actual_minus_expected_ppg |
| ---: | --- | --- | ---: | --- | ---: | ---: | ---: |
| 1 | Alpha Receiver | AAA | 36.0378 | no_breakout_trigger | 17.0000 | 1 | 0.1000 |

## False negatives

_No rows in this category._

## Key signal patterns in hits vs misses

- Average usage signal — hits: n/a, false positives: 79.1667, false negatives: n/a.
- Average efficiency signal — hits: n/a, false positives: 80.4180, false negatives: n/a.
- Average development signal — hits: n/a, false positives: 50.0000, false negatives: n/a.
- Average actual-minus-expected PPG — hits: n/a, false positives: 0.1000, false negatives: n/a.
- False-positive miss pattern counts: below-hit-average usage=n/a, below-hit-average efficiency=n/a, non-positive actual-minus-expected PPG=0/1.

## Limitations / cautions

- This report is a deterministic retrospective validation slice, not a live projection engine or a claim of predictive certainty.
- Hits, false positives, and false negatives are defined relative to the surfaced cutoff of top 20; changing that cutoff changes the case-study counts.
- Breakout labels come from the existing label engine and inherit its threshold definitions and simplifications.
- If the validation dataset has missing outcome rows for the requested pair, those players are excluded from hit/miss accounting rather than guessed forward.
