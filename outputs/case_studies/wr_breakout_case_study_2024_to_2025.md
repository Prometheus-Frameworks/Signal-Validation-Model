# WR Breakout Case Study: 2024 to 2025

## Executive summary

- Best recipe from the comparison summary: `role_balanced` (`wr_signal_score_role_balanced_v1`).
- Evaluated 0 of 227 rows for this season pair; 227 rows were excluded because the outcome season is missing.
- Using a surfaced cutoff of top 20, the model produced 0 hits, 0 false positives, and 0 false negatives.
- Actual breakout count for 2025: 0. Hit-rate within surfaced candidates: n/a.
- Breakout reasons represented among hits: none.

## Best recipe for this season pair

- Recipe selection is sourced from the deterministic recipe comparison summary, not from the case-study layer.
- Primary metric: `precision_at_20`.
- Tie-breakers: recall_at_20, lowest_average_breakout_rank, recipe_name.
- Pair-level comparison metrics copied from the summary: precision@20=0.5190, recall@20=0.1798, average breakout rank=88.2412.

## Top flagged candidates from `role_balanced`

_No rows in this category._

## Actual breakouts

_No rows in this category._

## Correctly surfaced breakouts

_No rows in this category._

## False positives

_No rows in this category._

## False negatives

_No rows in this category._

## Key signal patterns in hits vs misses

- Average usage signal — hits: n/a, false positives: n/a, false negatives: n/a.
- Average efficiency signal — hits: n/a, false positives: n/a, false negatives: n/a.
- Average development signal — hits: n/a, false positives: n/a, false negatives: n/a.
- Average actual-minus-expected PPG — hits: n/a, false positives: n/a, false negatives: n/a.
- False-positive miss pattern counts: below-hit-average usage=n/a, below-hit-average efficiency=n/a, non-positive actual-minus-expected PPG=n/a.

## Limitations / cautions

- This report is a deterministic retrospective validation slice, not a live projection engine or a claim of predictive certainty.
- Hits, false positives, and false negatives are defined relative to the surfaced cutoff of top 20; changing that cutoff changes the case-study counts.
- Breakout labels come from the existing label engine and inherit its threshold definitions and simplifications.
- If the validation dataset has missing outcome rows for the requested pair, those players are excluded from hit/miss accounting rather than guessed forward.
