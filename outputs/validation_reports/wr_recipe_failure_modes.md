# WR Recipe Failure Modes

Side-by-side deterministic comparison of how each recipe missed breakout labels or elevated false positives.

Best recipe under the documented rule: `balanced_conservative`.

## Metric table

| recipe_name | p@10 | p@20 | p@30 | r@10 | r@20 | r@30 | avg breakout rank | median breakout rank | fp top20 | fn outside30 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| balanced_conservative | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 1 | 0 |
| baseline_v1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 1 | 0 |
| efficiency_heavy | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 1 | 0 |
| upside_chaser | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 1 | 0 |
| usage_heavy | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | 1 | 0 |

## balanced_conservative

- precision@20: 0.0000
- recall@20: 0.0000
- false positives in top 20: 1
- false negatives outside top 30: 0

### Top false positives

| feature_season | rank | player_id | player_name | score | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- |
| 2022 | 1 | wr_alpha | Alpha Receiver | 36.0378 | no_breakout_trigger |

### Top false negatives

_No rows in this category._

## baseline_v1

- precision@20: 0.0000
- recall@20: 0.0000
- false positives in top 20: 1
- false negatives outside top 30: 0

### Top false positives

| feature_season | rank | player_id | player_name | score | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- |
| 2022 | 1 | wr_alpha | Alpha Receiver | 46.3279 | no_breakout_trigger |

### Top false negatives

_No rows in this category._

## efficiency_heavy

- precision@20: 0.0000
- recall@20: 0.0000
- false positives in top 20: 1
- false negatives outside top 30: 0

### Top false positives

| feature_season | rank | player_id | player_name | score | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- |
| 2022 | 1 | wr_alpha | Alpha Receiver | 45.6326 | no_breakout_trigger |

### Top false negatives

_No rows in this category._

## upside_chaser

- precision@20: 0.0000
- recall@20: 0.0000
- false positives in top 20: 1
- false negatives outside top 30: 0

### Top false positives

| feature_season | rank | player_id | player_name | score | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- |
| 2022 | 1 | wr_alpha | Alpha Receiver | 45.0068 | no_breakout_trigger |

### Top false negatives

_No rows in this category._

## usage_heavy

- precision@20: 0.0000
- recall@20: 0.0000
- false positives in top 20: 1
- false negatives outside top 30: 0

### Top false positives

| feature_season | rank | player_id | player_name | score | breakout_reason |
| ---: | ---: | --- | --- | ---: | --- |
| 2022 | 1 | wr_alpha | Alpha Receiver | 46.3839 | no_breakout_trigger |

### Top false negatives

_No rows in this category._
