# WR Recipe Failure Modes

Side-by-side deterministic comparison of how each recipe missed breakout labels or elevated false positives.

Best recipe under the documented rule: `role_balanced`.
Best base recipe: `upside_chaser`.
Best cohort-aware recipe: `cohort_balanced`.
Best role-aware recipe: `role_balanced`.

## Metric table

| recipe_name | family | p@10 | p@20 | p@30 | r@10 | r@20 | r@30 | avg breakout rank | median breakout rank | fp top20 | fn outside30 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| balanced_conservative | base | 0.6500 | 0.4875 | 0.5250 | 0.1140 | 0.1711 | 0.2763 | 87.2632 | 81.5000 | 41 | 165 |
| baseline_v1 | base | 0.6000 | 0.5000 | 0.4874 | 0.1053 | 0.1754 | 0.2544 | 88.9167 | 83.0000 | 40 | 170 |
| cohort_balanced | cohort | 0.5385 | 0.5063 | 0.4622 | 0.0921 | 0.1754 | 0.2412 | 88.3465 | 81.0000 | 39 | 173 |
| cohort_upside | cohort | 0.5385 | 0.4937 | 0.4661 | 0.0921 | 0.1711 | 0.2412 | 90.5219 | 79.0000 | 40 | 173 |
| efficiency_heavy | base | 0.5500 | 0.4937 | 0.4786 | 0.0965 | 0.1711 | 0.2456 | 92.2982 | 87.5000 | 40 | 172 |
| role_balanced | role | 0.5385 | 0.5190 | 0.4790 | 0.0921 | 0.1798 | 0.2500 | 88.2412 | 82.0000 | 38 | 171 |
| role_upside | role | 0.5128 | 0.5190 | 0.4831 | 0.0877 | 0.1798 | 0.2500 | 90.1272 | 84.5000 | 38 | 171 |
| upside_chaser | base | 0.5250 | 0.5063 | 0.4831 | 0.0921 | 0.1754 | 0.2500 | 91.9167 | 88.5000 | 39 | 171 |
| usage_heavy | base | 0.5000 | 0.4875 | 0.5042 | 0.0877 | 0.1711 | 0.2632 | 87.8509 | 81.5000 | 41 | 168 |

## balanced_conservative

- family: base
- precision@20: 0.4875
- recall@20: 0.1711
- false positives in top 20: 41
- false negatives outside top 30: 165

### Top false positives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 1 | 00-0031428 | A.Robinson | 49.6290 | false  no_breakout_trigger |
| 2020 | 2 | 00-0032211 | T.Lockett | 48.5715 | false  no_breakout_trigger |
| 2020 | 3 | 00-0030564 | D.Hopkins | 47.8453 | false  no_breakout_trigger |
| 2020 | 4 | 00-0035640 | D.Metcalf | 47.6900 | false  no_breakout_trigger |
| 2020 | 5 | 00-0031588 | S.Diggs | 47.5315 | false  no_breakout_trigger |
| 2020 | 8 | 00-0033040 | T.Hill | 45.2540 | false  no_breakout_trigger |
| 2020 | 9 | 00-0034837 | C.Ridley | 45.2383 | false  no_breakout_trigger |
| 2020 | 10 | 00-0031381 | D.Adams | 45.1364 | false  no_breakout_trigger |
| 2020 | 13 | 00-0030279 | K.Allen | 44.1341 | false  no_breakout_trigger |
| 2020 | 15 | 00-0031544 | A.Cooper | 42.8170 | false  no_breakout_trigger |

### Top false negatives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 31 | 00-0036410 | T.Higgins | 32.4585 | true  top24_jump |
| 2020 | 38 | 00-0034411 | R.Gage | 28.2531 | true  beat_expected_baseline |
| 2020 | 40 | 00-0035662 | M.Brown | 27.9769 | true  beat_expected_baseline |
| 2020 | 46 | 00-0027793 | A.Brown | 24.4349 | true  beat_expected_baseline |
| 2020 | 49 | 00-0036309 | D.Mooney | 23.7120 | true  ppg_jump |
| 2020 | 52 | 00-0033536 | M.Williams | 22.6172 | true  top24_jump |
| 2020 | 56 | 00-0034775 | C.Kirk | 21.2122 | true  beat_expected_baseline |
| 2020 | 61 | 00-0034983 | H.Renfrow | 19.7973 | true  top24_jump |
| 2020 | 64 | 00-0033307 | K.Bourne | 18.8246 | true  beat_expected_baseline |
| 2020 | 65 | 00-0027942 | A.Green | 18.7623 | true  beat_expected_baseline |

## baseline_v1

- family: base
- precision@20: 0.5000
- recall@20: 0.1754
- false positives in top 20: 40
- false negatives outside top 30: 170

### Top false positives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 1 | 00-0031588 | S.Diggs | 53.4927 | false  no_breakout_trigger |
| 2020 | 2 | 00-0031381 | D.Adams | 53.3320 | false  no_breakout_trigger |
| 2020 | 3 | 00-0030564 | D.Hopkins | 53.2083 | false  no_breakout_trigger |
| 2020 | 4 | 00-0031428 | A.Robinson | 53.1812 | false  no_breakout_trigger |
| 2020 | 5 | 00-0033040 | T.Hill | 51.9253 | false  no_breakout_trigger |
| 2020 | 6 | 00-0032211 | T.Lockett | 51.6559 | false  no_breakout_trigger |
| 2020 | 7 | 00-0034837 | C.Ridley | 51.3345 | false  no_breakout_trigger |
| 2020 | 8 | 00-0035640 | D.Metcalf | 51.1459 | false  no_breakout_trigger |
| 2020 | 10 | 00-0030279 | K.Allen | 50.3593 | false  no_breakout_trigger |
| 2020 | 14 | 00-0035676 | A.Brown | 46.9641 | false  no_breakout_trigger |

### Top false negatives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 34 | 00-0036410 | T.Higgins | 34.4688 | true  top24_jump |
| 2020 | 38 | 00-0027793 | A.Brown | 31.3193 | true  beat_expected_baseline |
| 2020 | 40 | 00-0034411 | R.Gage | 28.7603 | true  beat_expected_baseline |
| 2020 | 42 | 00-0035662 | M.Brown | 28.2852 | true  beat_expected_baseline |
| 2020 | 51 | 00-0033536 | M.Williams | 24.2314 | true  top24_jump |
| 2020 | 52 | 00-0036309 | D.Mooney | 23.7333 | true  ppg_jump |
| 2020 | 54 | 00-0034775 | C.Kirk | 22.6130 | true  beat_expected_baseline |
| 2020 | 66 | 00-0034983 | H.Renfrow | 19.1789 | true  top24_jump |
| 2020 | 68 | 00-0033307 | K.Bourne | 19.0168 | true  beat_expected_baseline |
| 2020 | 69 | 00-0027942 | A.Green | 18.6452 | true  beat_expected_baseline |

## cohort_balanced

- family: cohort
- precision@20: 0.5063
- recall@20: 0.1754
- false positives in top 20: 39
- false negatives outside top 30: 173

### Top false positives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 1 | 00-0031588 | S.Diggs | 45.7540 | false  no_breakout_trigger |
| 2020 | 2 | 00-0030564 | D.Hopkins | 45.4852 | false  no_breakout_trigger |
| 2020 | 3 | 00-0031381 | D.Adams | 45.1962 | false  no_breakout_trigger |
| 2020 | 4 | 00-0031428 | A.Robinson | 45.0987 | false  no_breakout_trigger |
| 2020 | 5 | 00-0033040 | T.Hill | 44.2496 | false  no_breakout_trigger |
| 2020 | 6 | 00-0032211 | T.Lockett | 43.8329 | false  no_breakout_trigger |
| 2020 | 7 | 00-0034837 | C.Ridley | 43.7791 | false  no_breakout_trigger |
| 2020 | 8 | 00-0035640 | D.Metcalf | 43.5271 | false  no_breakout_trigger |
| 2020 | 10 | 00-0030279 | K.Allen | 42.5883 | false  no_breakout_trigger |
| 2020 | 14 | 00-0035676 | A.Brown | 39.8392 | false  no_breakout_trigger |

### Top false negatives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 34 | 00-0036410 | T.Higgins | 29.6948 | true  top24_jump |
| 2020 | 39 | 00-0034411 | R.Gage | 25.3582 | true  beat_expected_baseline |
| 2020 | 40 | 00-0027793 | A.Brown | 25.0559 | true  beat_expected_baseline |
| 2020 | 42 | 00-0035662 | M.Brown | 24.9772 | true  beat_expected_baseline |
| 2020 | 51 | 00-0033536 | M.Williams | 21.0854 | true  top24_jump |
| 2020 | 52 | 00-0036309 | D.Mooney | 20.9952 | true  ppg_jump |
| 2020 | 54 | 00-0034775 | C.Kirk | 19.6872 | true  beat_expected_baseline |
| 2020 | 62 | 00-0034983 | H.Renfrow | 17.0755 | true  top24_jump |
| 2020 | 65 | 00-0033307 | K.Bourne | 16.7556 | true  beat_expected_baseline |
| 2020 | 67 | 00-0027942 | A.Green | 16.4920 | true  beat_expected_baseline |

## cohort_upside

- family: cohort
- precision@20: 0.4937
- recall@20: 0.1711
- false positives in top 20: 40
- false negatives outside top 30: 173

### Top false positives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 1 | 00-0031381 | D.Adams | 35.5571 | false  no_breakout_trigger |
| 2020 | 2 | 00-0033040 | T.Hill | 34.9675 | false  no_breakout_trigger |
| 2020 | 3 | 00-0031588 | S.Diggs | 34.2795 | false  no_breakout_trigger |
| 2020 | 4 | 00-0030564 | D.Hopkins | 33.5736 | false  no_breakout_trigger |
| 2020 | 5 | 00-0035640 | D.Metcalf | 33.2807 | false  no_breakout_trigger |
| 2020 | 6 | 00-0034837 | C.Ridley | 33.2459 | false  no_breakout_trigger |
| 2020 | 8 | 00-0032211 | T.Lockett | 33.0295 | false  no_breakout_trigger |
| 2020 | 10 | 00-0031428 | A.Robinson | 32.8046 | false  no_breakout_trigger |
| 2020 | 11 | 00-0035676 | A.Brown | 32.1488 | false  no_breakout_trigger |
| 2020 | 12 | 00-0030279 | K.Allen | 31.6248 | false  no_breakout_trigger |

### Top false negatives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 34 | 00-0036410 | T.Higgins | 21.1629 | true  top24_jump |
| 2020 | 35 | 00-0027793 | A.Brown | 21.0387 | true  beat_expected_baseline |
| 2020 | 42 | 00-0035662 | M.Brown | 17.0521 | true  beat_expected_baseline |
| 2020 | 43 | 00-0034411 | R.Gage | 16.7114 | true  beat_expected_baseline |
| 2020 | 51 | 00-0033536 | M.Williams | 14.8069 | true  top24_jump |
| 2020 | 55 | 00-0034775 | C.Kirk | 13.9906 | true  beat_expected_baseline |
| 2020 | 59 | 00-0036309 | D.Mooney | 13.3220 | true  ppg_jump |
| 2020 | 67 | 00-0033307 | K.Bourne | 11.3567 | true  beat_expected_baseline |
| 2020 | 69 | 00-0034983 | H.Renfrow | 11.1723 | true  top24_jump |
| 2020 | 71 | 00-0035719 | D.Samuel | 10.9929 | true  top24_jump |

## efficiency_heavy

- family: base
- precision@20: 0.4937
- recall@20: 0.1711
- false positives in top 20: 40
- false negatives outside top 30: 172

### Top false positives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 1 | 00-0031381 | D.Adams | 54.2459 | false  no_breakout_trigger |
| 2020 | 2 | 00-0033040 | T.Hill | 54.0864 | false  no_breakout_trigger |
| 2020 | 5 | 00-0035640 | D.Metcalf | 50.1053 | false  no_breakout_trigger |
| 2020 | 6 | 00-0031588 | S.Diggs | 50.0195 | false  no_breakout_trigger |
| 2020 | 7 | 00-0035676 | A.Brown | 50.0174 | false  no_breakout_trigger |
| 2020 | 8 | 00-0032211 | T.Lockett | 48.9496 | false  no_breakout_trigger |
| 2020 | 9 | 00-0034837 | C.Ridley | 48.6539 | false  no_breakout_trigger |
| 2020 | 11 | 00-0030564 | D.Hopkins | 47.9363 | false  no_breakout_trigger |
| 2020 | 12 | 00-0033127 | W.Fuller | 47.6513 | false  no_breakout_trigger |
| 2020 | 13 | 00-0031428 | A.Robinson | 46.5828 | false  no_breakout_trigger |

### Top false negatives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 32 | 00-0033908 | C.Kupp | 36.4434 | true  top24_jump |
| 2020 | 35 | 00-0036410 | T.Higgins | 33.1423 | true  top24_jump |
| 2020 | 38 | 00-0027793 | A.Brown | 31.7418 | true  beat_expected_baseline |
| 2020 | 43 | 00-0035662 | M.Brown | 28.7781 | true  beat_expected_baseline |
| 2020 | 48 | 00-0034411 | R.Gage | 27.0370 | true  beat_expected_baseline |
| 2020 | 57 | 00-0036233 | D.Peoples-Jones | 25.4440 | true  beat_expected_baseline |
| 2020 | 59 | 00-0033536 | M.Williams | 25.3803 | true  top24_jump |
| 2020 | 60 | 00-0034775 | C.Kirk | 24.6225 | true  beat_expected_baseline |
| 2020 | 69 | 00-0034052 | B.Zylstra | 22.9273 | true  beat_expected_baseline |
| 2020 | 70 | 00-0032951 | L.Treadwell | 22.7818 | true  beat_expected_baseline |

## role_balanced

- family: role
- precision@20: 0.5190
- recall@20: 0.1798
- false positives in top 20: 38
- false negatives outside top 30: 171

### Top false positives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 1 | 00-0031588 | S.Diggs | 39.1852 | false  no_breakout_trigger |
| 2020 | 2 | 00-0031381 | D.Adams | 38.8741 | false  no_breakout_trigger |
| 2020 | 3 | 00-0030564 | D.Hopkins | 38.8010 | false  no_breakout_trigger |
| 2020 | 4 | 00-0033040 | T.Hill | 38.2131 | false  no_breakout_trigger |
| 2020 | 5 | 00-0031428 | A.Robinson | 38.0928 | false  no_breakout_trigger |
| 2020 | 6 | 00-0034837 | C.Ridley | 37.5097 | false  no_breakout_trigger |
| 2020 | 7 | 00-0032211 | T.Lockett | 37.2916 | false  no_breakout_trigger |
| 2020 | 8 | 00-0035640 | D.Metcalf | 37.2184 | false  no_breakout_trigger |
| 2020 | 10 | 00-0030279 | K.Allen | 36.1386 | false  no_breakout_trigger |
| 2020 | 12 | 00-0035676 | A.Brown | 34.4282 | false  no_breakout_trigger |

### Top false negatives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 34 | 00-0036410 | T.Higgins | 25.1090 | true  top24_jump |
| 2020 | 39 | 00-0034411 | R.Gage | 21.3600 | true  beat_expected_baseline |
| 2020 | 41 | 00-0035662 | M.Brown | 21.1718 | true  beat_expected_baseline |
| 2020 | 42 | 00-0027793 | A.Brown | 21.1152 | true  beat_expected_baseline |
| 2020 | 51 | 00-0033536 | M.Williams | 17.8325 | true  top24_jump |
| 2020 | 52 | 00-0036309 | D.Mooney | 17.7055 | true  ppg_jump |
| 2020 | 54 | 00-0034775 | C.Kirk | 16.7156 | true  beat_expected_baseline |
| 2020 | 63 | 00-0034983 | H.Renfrow | 14.6038 | true  top24_jump |
| 2020 | 64 | 00-0033307 | K.Bourne | 14.3074 | true  beat_expected_baseline |
| 2020 | 68 | 00-0027942 | A.Green | 13.6515 | true  beat_expected_baseline |

## role_upside

- family: role
- precision@20: 0.5190
- recall@20: 0.1798
- false positives in top 20: 38
- false negatives outside top 30: 171

### Top false positives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 1 | 00-0031381 | D.Adams | 31.2239 | false  no_breakout_trigger |
| 2020 | 2 | 00-0033040 | T.Hill | 30.9125 | false  no_breakout_trigger |
| 2020 | 3 | 00-0031588 | S.Diggs | 30.2469 | false  no_breakout_trigger |
| 2020 | 4 | 00-0035640 | D.Metcalf | 29.7924 | false  no_breakout_trigger |
| 2020 | 6 | 00-0030564 | D.Hopkins | 29.6694 | false  no_breakout_trigger |
| 2020 | 8 | 00-0032211 | T.Lockett | 29.5941 | false  no_breakout_trigger |
| 2020 | 9 | 00-0034837 | C.Ridley | 29.3610 | false  no_breakout_trigger |
| 2020 | 10 | 00-0031428 | A.Robinson | 29.2762 | false  no_breakout_trigger |
| 2020 | 11 | 00-0035676 | A.Brown | 28.6153 | false  no_breakout_trigger |
| 2020 | 13 | 00-0030279 | K.Allen | 27.8454 | false  no_breakout_trigger |

### Top false negatives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 34 | 00-0036410 | T.Higgins | 19.9933 | true  top24_jump |
| 2020 | 38 | 00-0027793 | A.Brown | 18.6569 | true  beat_expected_baseline |
| 2020 | 40 | 00-0035662 | M.Brown | 16.9376 | true  beat_expected_baseline |
| 2020 | 43 | 00-0034411 | R.Gage | 16.4179 | true  beat_expected_baseline |
| 2020 | 51 | 00-0033536 | M.Williams | 14.1044 | true  top24_jump |
| 2020 | 54 | 00-0034775 | C.Kirk | 12.7321 | true  beat_expected_baseline |
| 2020 | 61 | 00-0036309 | D.Mooney | 11.9199 | true  ppg_jump |
| 2020 | 66 | 00-0035719 | D.Samuel | 10.7962 | true  top24_jump |
| 2020 | 69 | 00-0033307 | K.Bourne | 10.2278 | true  beat_expected_baseline |
| 2020 | 70 | 00-0034983 | H.Renfrow | 10.1385 | true  top24_jump |

## upside_chaser

- family: base
- precision@20: 0.5063
- recall@20: 0.1754
- false positives in top 20: 39
- false negatives outside top 30: 171

### Top false positives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 1 | 00-0031381 | D.Adams | 48.9633 | false  no_breakout_trigger |
| 2020 | 2 | 00-0033040 | T.Hill | 48.2695 | false  no_breakout_trigger |
| 2020 | 3 | 00-0031588 | S.Diggs | 46.3272 | false  no_breakout_trigger |
| 2020 | 5 | 00-0034837 | C.Ridley | 44.9544 | false  no_breakout_trigger |
| 2020 | 7 | 00-0030564 | D.Hopkins | 44.8957 | false  no_breakout_trigger |
| 2020 | 8 | 00-0035640 | D.Metcalf | 44.8382 | false  no_breakout_trigger |
| 2020 | 9 | 00-0035676 | A.Brown | 44.2728 | false  no_breakout_trigger |
| 2020 | 10 | 00-0032211 | T.Lockett | 44.1026 | false  no_breakout_trigger |
| 2020 | 11 | 00-0031428 | A.Robinson | 43.2545 | false  no_breakout_trigger |
| 2020 | 13 | 00-0030279 | K.Allen | 42.0053 | false  no_breakout_trigger |

### Top false negatives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 34 | 00-0036410 | T.Higgins | 30.4630 | true  top24_jump |
| 2020 | 36 | 00-0027793 | A.Brown | 29.7836 | true  beat_expected_baseline |
| 2020 | 41 | 00-0035662 | M.Brown | 26.1267 | true  beat_expected_baseline |
| 2020 | 43 | 00-0034411 | R.Gage | 25.1323 | true  beat_expected_baseline |
| 2020 | 52 | 00-0033536 | M.Williams | 22.3488 | true  top24_jump |
| 2020 | 55 | 00-0034775 | C.Kirk | 20.5084 | true  beat_expected_baseline |
| 2020 | 63 | 00-0035719 | D.Samuel | 18.7692 | true  top24_jump |
| 2020 | 65 | 00-0036309 | D.Mooney | 18.6514 | true  ppg_jump |
| 2020 | 71 | 00-0034521 | A.Lazard | 16.7284 | true  beat_expected_baseline |
| 2020 | 72 | 00-0033307 | K.Bourne | 16.6784 | true  beat_expected_baseline |

## usage_heavy

- family: base
- precision@20: 0.4875
- recall@20: 0.1711
- false positives in top 20: 41
- false negatives outside top 30: 168

### Top false positives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 1 | 00-0031588 | S.Diggs | 58.1959 | false  no_breakout_trigger |
| 2020 | 2 | 00-0031381 | D.Adams | 57.5089 | false  no_breakout_trigger |
| 2020 | 3 | 00-0030564 | D.Hopkins | 56.3654 | false  no_breakout_trigger |
| 2020 | 4 | 00-0030279 | K.Allen | 54.9742 | false  no_breakout_trigger |
| 2020 | 5 | 00-0031428 | A.Robinson | 54.4102 | false  no_breakout_trigger |
| 2020 | 6 | 00-0034837 | C.Ridley | 53.1563 | false  no_breakout_trigger |
| 2020 | 7 | 00-0033040 | T.Hill | 52.0304 | false  no_breakout_trigger |
| 2020 | 8 | 00-0032211 | T.Lockett | 50.4107 | false  no_breakout_trigger |
| 2020 | 10 | 00-0035640 | D.Metcalf | 49.7520 | false  no_breakout_trigger |
| 2020 | 12 | 00-0035659 | T.McLaurin | 47.0824 | false  no_breakout_trigger |

### Top false negatives

| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- | --- |
| 2020 | 32 | 00-0036410 | T.Higgins | 35.0704 | true  top24_jump |
| 2020 | 39 | 00-0034411 | R.Gage | 30.9568 | true  beat_expected_baseline |
| 2020 | 43 | 00-0035662 | M.Brown | 29.2280 | true  beat_expected_baseline |
| 2020 | 45 | 00-0027793 | A.Brown | 28.2621 | true  beat_expected_baseline |
| 2020 | 48 | 00-0036309 | D.Mooney | 25.4616 | true  ppg_jump |
| 2020 | 51 | 00-0033536 | M.Williams | 24.2899 | true  top24_jump |
| 2020 | 56 | 00-0027942 | A.Green | 22.4628 | true  beat_expected_baseline |
| 2020 | 57 | 00-0034775 | C.Kirk | 21.9989 | true  beat_expected_baseline |
| 2020 | 64 | 00-0034983 | H.Renfrow | 18.7856 | true  top24_jump |
| 2020 | 66 | 00-0033307 | K.Bourne | 18.2448 | true  beat_expected_baseline |
