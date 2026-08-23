# Late-veteran WR breakout v0 examples

These are research traces from the pinned observed-row population. They are not rankings or recommendations.

## Positive controls

| Player | Pair | Feature PPG | Feature target share | Outcome PPG | Outcome target share | Eligibility | Fantasy breakout | Role expansion | Archetype hit |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| Jauan Jennings | 2023→2024 | 3.96 | 0.0701 | 14.03 | 0.2203 | prior_history_incomplete | true | confirmed | true |
| Parker Washington | 2024→2025 | 6.93 | 0.0977 | 11.54 | 0.1737 | eligible | true | confirmed | true |

Jauan Jennings remains provisional because the promoted input begins in 2021 while his source-backed rookie year is 2020. Parker Washington has complete rookie-to-feature exposure in the pinned window.

## Reproducibly selected negative controls

Selection rule: primary-eligible non-hits, ordered by the fewest failed outcome components, normalized threshold shortfall, feature season, then player ID.

| Player | Pair | Feature PPG | Feature target share | Outcome PPG | Outcome target share | Eligibility | Fantasy breakout | Role expansion | Archetype hit |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| Jalen Tolbert | 2023→2024 | 4.34 | 0.0595 | 8.94 | 0.1270 | eligible | false | not_confirmed | false |
| Tutu Atwell | 2022→2023 | 5.27 | 0.0677 | 8.03 | 0.1207 | eligible | false | not_confirmed | false |

Two reproducible negative controls were available.

## Interpretation boundary

Outcome information is used only to label and select retrospective examples; it never changes feature-side eligibility.
