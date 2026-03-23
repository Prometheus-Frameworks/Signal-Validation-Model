# WR Public Findings: 2024 to 2025

## Executive summary

For the 2024 to 2025 WR retrospective, `role_balanced` finished as the best overall recipe and the winning recipe family was `role`. The season-pair review logged 0 hits, 0 false positives, and 0 false negatives.

## Best overall recipe and family

- Best overall recipe: `role_balanced`.
- Winning family: `role`.
- Best base recipe: `upside_chaser`.
- Best cohort-aware recipe: `cohort_balanced`.
- Best role-aware recipe: `role_balanced`.

## Did cohort / role context help?

- Cohort over base: Improved (precision/recall were flat and average breakout rank improved by +3.57).
- Role over base: Improved (precision@20 improved by +0.01).
- Role over cohort: Improved (precision@20 improved by +0.01).

## Notable player hits

| notable_rank | player_name | team | case_type | candidate_rank | signal_score | feature_ppg | outcome_ppg | actual_minus_expected_ppg | breakout_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Notable player misses

| notable_rank | player_name | team | miss_type | candidate_rank | signal_score | feature_ppg | outcome_ppg | actual_minus_expected_ppg | breakout_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Public-safe signal takeaways

- The best overall recipe came from the `role` family, with `role_balanced` winning under the published recipe-selection rule.
- Among the top exported candidates, the average public-safe role signal was 0.00 and the average cohort signal was 100.00.
- The selected notable hits averaged n/a outcome PPG, compared with n/a for the selected notable misses.
- The season-pair case study recorded 0 hits, 0 false positives, and 0 false negatives.

## Limitations and cautions

- This pack is retrospective only and uses existing validated/exported artifacts without rescoring.
- Recipe-family improvement checks are inferences from published comparison deltas, not new experiments.
- Notable hits and misses follow a deterministic ranking rule and are examples, not an exhaustive narrative.
- Public formatting intentionally simplifies the lower-level scoring details and omits internal scaffolding.
