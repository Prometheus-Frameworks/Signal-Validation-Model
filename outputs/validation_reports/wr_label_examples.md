# WR Breakout Label Examples

These examples are deterministic slices of the joined WR validation dataset.

## Default-label breakouts
| player_id | feature_season | outcome_season | feature_ppg | outcome_ppg | reason |
| --- | ---: | ---: | ---: | ---: | --- |
| 00-0026035 | 2020 | 2021 | 7.6000 | 8.6000 | beat_expected_baseline |
| 00-0027793 | 2020 | 2021 | 14.6375 | 17.3000 | beat_expected_baseline |
| 00-0027942 | 2020 | 2021 | 6.9563 | 9.8000 | beat_expected_baseline |
| 00-0030035 | 2020 | 2021 | 16.9333 | 15.3692 | beat_expected_baseline |
| 00-0030431 | 2020 | 2021 | 15.3187 | 15.2444 | beat_expected_baseline |

## Non-breakout rows with valid outcomes
| player_id | feature_season | outcome_season | feature_ppg | outcome_ppg | reason |
| --- | ---: | ---: | ---: | ---: | --- |
| 00-0026189 | 2020 | 2021 | 8.9600 | 5.4143 | no_breakout_trigger |
| 00-0027685 | 2020 | 2021 | 11.7714 | 9.4071 | no_breakout_trigger |
| 00-0027691 | 2020 | 2021 | 2.3667 | 2.4800 | no_breakout_trigger |
| 00-0027944 | 2020 | 2021 | 16.2333 | 8.0400 | no_breakout_trigger |
| 00-0028002 | 2020 | 2021 | 10.0100 | 8.6909 | no_breakout_trigger |

## Missing-outcome rows
| player_id | feature_season | outcome_season | feature_ppg | outcome_ppg | reason |
| --- | ---: | ---: | ---: | ---: | --- |
| 00-0022921 | 2020 | 2021 | 7.7615 |  | missing_outcome |
| 00-0025396 | 2020 | 2021 | 2.3333 |  | missing_outcome |
| 00-0027150 | 2020 | 2021 | 9.3700 |  | missing_outcome |
| 00-0027891 | 2020 | 2021 | 7.2100 |  | missing_outcome |
| 00-0027902 | 2020 | 2021 | 5.6750 |  | missing_outcome |
