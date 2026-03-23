# WR Public Findings: 2022 to 2023

## Executive summary

For the 2022 to 2023 WR retrospective, `balanced_conservative` finished as the best overall recipe and the winning recipe family was `base`. The season-pair review logged 0 hits, 1 false positives, and 0 false negatives.

## Best overall recipe and family

- Best overall recipe: `balanced_conservative`.
- Winning family: `base`.
- Best base recipe: `balanced_conservative`.
- Best cohort-aware recipe: `cohort_balanced`.
- Best role-aware recipe: `role_balanced`.

## Did cohort / role context help?

- Cohort over base: Matched (best cohort-aware recipe vs. best base recipe matched on the published comparison metrics).
- Role over base: Matched (best role-aware recipe vs. best base recipe matched on the published comparison metrics).
- Role over cohort: Matched (best role-aware recipe vs. best cohort-aware recipe matched on the published comparison metrics).

## Notable player hits

| notable_rank | player_name | team | case_type | candidate_rank | signal_score | feature_ppg | outcome_ppg | actual_minus_expected_ppg | breakout_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Notable player misses

| notable_rank | player_name | team | miss_type | candidate_rank | signal_score | feature_ppg | outcome_ppg | actual_minus_expected_ppg | breakout_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Alpha Receiver | AAA | false_positive | 1 | 36.04 | 18.0 | 17.0 | 0.10 | no_breakout_trigger |

## Public-safe signal takeaways

- The best overall recipe came from the `base` family, with `balanced_conservative` winning under the published recipe-selection rule.
- Among the top exported candidates, the average public-safe role signal was 39.17 and the average cohort signal was 0.00.
- The selected notable hits averaged n/a outcome PPG, compared with 17.00 for the selected notable misses.
- The season-pair case study recorded 0 hits, 1 false positives, and 0 false negatives.

## Limitations and cautions

- This pack is retrospective only and uses existing validated/exported artifacts without rescoring.
- Recipe-family improvement checks are inferences from published comparison deltas, not new experiments.
- Notable hits and misses follow a deterministic ranking rule and are examples, not an exhaustive narrative.
- Public formatting intentionally simplifies the lower-level scoring details and omits internal scaffolding.
