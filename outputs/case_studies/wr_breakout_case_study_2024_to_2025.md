# WR Breakout Case Study: 2024 to 2025

## Executive summary

- Best recipe from the comparison summary: `role_balanced` (`wr_signal_score_role_balanced_v1`).
- Evaluated 0 of 227 rows for this season pair; 227 rows were excluded because the outcome season is missing.
- The 2024→2025 report is a forward-looking candidate board. Final hit/miss evaluation will be available once 2025 outcome data is complete.
- Outcome evaluation is pending because 0 of 227 rows currently have valid 2025 outcomes.
- Breakout reasons among surfaced candidates will be summarized after outcomes are complete.

## Best recipe for this season pair

- Recipe selection is sourced from the deterministic recipe comparison summary, not from the case-study layer.
- Primary metric: `precision_at_20`.
- Tie-breakers: recall_at_20, lowest_average_breakout_rank, recipe_name.
- Pair-level comparison metrics copied from the summary: precision@20=0.5190, recall@20=0.1798, average breakout rank=88.2412.

## Top flagged candidates from `role_balanced`

_No rows in this category._

## Actual breakouts

Outcomes pending: final 2025 breakout evaluation will appear here once valid outcome data is complete.

## Correctly surfaced breakouts

Outcomes pending: final 2025 breakout evaluation will appear here once valid outcome data is complete.

## False positives

Outcomes pending: final 2025 breakout evaluation will appear here once valid outcome data is complete.

## False negatives

Outcomes pending: final 2025 breakout evaluation will appear here once valid outcome data is complete.

## Key signal patterns in hits vs misses

- Outcome-based hit/miss signal comparisons are pending until 2025 outcome data is complete.
- Surfaced candidates currently form a forward-looking board rather than a completed retrospective evaluation.

## Limitations / cautions

- This report is a deterministic forward-looking candidate board until the requested outcome season is complete.
- Hits, false positives, and false negatives are defined relative to the surfaced cutoff of top 20; changing that cutoff changes the case-study counts.
- Breakout labels come from the existing label engine and inherit its threshold definitions and simplifications.
- If the validation dataset has missing outcome rows for the requested pair, those players are excluded from hit/miss accounting rather than guessed forward.
