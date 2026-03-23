# WR Cohort Baseline Examples

The examples below show deterministic cohort-relative context derived only from earlier feature seasons.

## Rows with historical cohort coverage
| feature_season | player_id | career_year_bucket | age_bucket | cohort_count | expected_ppg | feature_minus_expected | outcome_minus_expected |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: |
| 2024 | 00-0035976 | yr1 | age_unknown | 383 | 7.0553 | -4.8220 | n/a |
| 2024 | 00-0036463 | yr1 | age_unknown | 383 | 7.0553 | -5.7053 | n/a |
| 2024 | 00-0037231 | yr1 | age_unknown | 383 | 7.0553 | -3.6803 | n/a |
| 2024 | 00-0037422 | yr1 | age_unknown | 383 | 7.0553 | -5.1553 | n/a |
| 2024 | 00-0037524 | yr1 | age_unknown | 383 | 7.0553 | 4.8447 | n/a |
| 2024 | 00-0038359 | yr1 | age_unknown | 383 | 7.0553 | -4.9886 | n/a |
| 2024 | 00-0038477 | yr1 | age_unknown | 383 | 7.0553 | -1.0553 | n/a |
| 2024 | 00-0038507 | yr1 | age_unknown | 383 | 7.0553 | -5.5053 | n/a |

## Rows without historical cohort coverage
| feature_season | player_id | career_year_bucket | age_bucket | cohort_count | expected_ppg | feature_minus_expected | outcome_minus_expected |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: |
| 2020 | 00-0022921 | yr1 | age_unknown | 0 | n/a | n/a | n/a |
| 2020 | 00-0025396 | yr1 | age_unknown | 0 | n/a | n/a | n/a |
| 2020 | 00-0026035 | yr1 | age_unknown | 0 | n/a | n/a | n/a |
| 2020 | 00-0026189 | yr1 | age_unknown | 0 | n/a | n/a | n/a |
| 2020 | 00-0027150 | yr1 | age_unknown | 0 | n/a | n/a | n/a |

## Positive outcome-vs-cohort deltas
| feature_season | player_id | career_year_bucket | age_bucket | cohort_count | expected_ppg | feature_minus_expected | outcome_minus_expected |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: |
| 2023 | 00-0037837 | yr1 | age_unknown | 335 | 7.0838 | -3.3195 | 0.0221 |
| 2023 | 00-0038543 | yr1 | age_unknown | 335 | 7.0838 | 1.7280 | 7.7986 |
| 2023 | 00-0038544 | yr1 | age_unknown | 335 | 7.0838 | -1.5544 | 4.5629 |
| 2023 | 00-0038559 | yr1 | age_unknown | 335 | 7.0838 | 1.7239 | 0.6975 |
| 2023 | 00-0038563 | yr1 | age_unknown | 335 | 7.0838 | -1.5607 | 0.5221 |
