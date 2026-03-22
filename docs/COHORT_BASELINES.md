# Cohort Baselines

PR6 adds deterministic cohort-baseline enrichment for the canonical WR validation dataset so the repo can compare plain prior-season recipes against cohort-aware recipes.

## Why cohort-relative signals matter

Plain prior-season scoring can tell us whether a player looked good in isolation, but it does not answer whether that prior season was strong **for a similar type of player**. Cohort-relative fields add historical peer expectations so the repo can ask:

- did the player already outperform the historical next-season expectation for similar WRs,
- did the player have more room to grow than the average peer, and
- do cohort-aware recipes rank breakouts better than base recipes that ignore peer context.

## Bucket definitions

Cohorts are defined with explicit deterministic buckets:

1. `position`
   - fixed to `WR` in this repository.
2. `career_year_bucket`
   - `yr1`: first recorded WR feature season for the player.
   - `yr2`: second recorded WR feature season.
   - `yr3`: third recorded WR feature season.
   - `yr4_plus`: fourth or later recorded WR feature season.
3. `age_bucket`
   - `age_21_or_younger`: age on Sept. 1 is less than 22.0 when available.
   - `age_22_to_24`: age is at least 22.0 and less than 25.0 when available.
   - `age_25_to_27`: age is at least 25.0 and less than 28.0 when available.
   - `age_28_plus`: age is at least 28.0 when available.
   - `age_unknown`: the current processed WR tables do not contain age, so rows are assigned to an explicit unknown-age bucket.

In the current repo data, `age_bucket` is therefore deterministic but usually resolves to `age_unknown`. That keeps the grouping logic explicit and forward-compatible without inventing missing age data.

## How expectations are calculated

For each row in `wr_validation_dataset.csv`:

1. assign the row to a deterministic cohort key: `position|career_year_bucket|age_bucket`.
2. gather only historical validation rows from the **same cohort** with `feature_season < current feature_season`.
3. compute cohort expectations from those historical peers:
   - `expected_ppg_from_cohort`: mean of historical `outcome_ppg`.
   - `expected_finish_from_cohort`: mean of historical `outcome_finish` when available.
   - `cohort_player_count`: distinct historical players contributing to that cohort expectation.
4. derive row-level deltas:
   - `feature_ppg_minus_cohort_expected`
   - `outcome_ppg_minus_cohort_expected`
   - `actual_minus_cohort_expected_ppg`

The enrichment is intentionally transparent: simple grouping, simple means, and no model fitting.

## Leakage guardrails

The cohort-baseline workflow enforces the same no-future-leakage posture as the earlier PRs:

- cohort expectations for feature season `S` use only historical rows with `feature_season < S`.
- the grouping key uses only feature-side identity metadata (`position`, deterministic career-year bucket, and age bucket when present).
- outcome fields are used only to build **historical** next-season expectations, never from the current row's future outcome.
- cohort-aware recipe scoring still consumes only feature-season fields plus the historically-derived cohort expectation columns.

## Limitations

- The current processed WR tables do not ship age, so `age_bucket` defaults to `age_unknown` unless future adapters add age to the processed feature table.
- Small cohorts can have sparse history early in the timeline. In those cases `cohort_player_count` can be `0` and expectation columns remain blank.
- `expected_finish_from_cohort` is a simple average rank, which is stable enough for deterministic inspection but should not be over-interpreted as a probabilistic forecast.
- Cohort quality depends on the historical sample already present in the repo; no external data source is required in PR6.

## CLI

Generate the enriched artifacts with:

```bash
signal-validation enrich-wr-cohorts \
  --processed-dir data/processed \
  --validation-dataset outputs/validation_reports/wr_validation_dataset.csv \
  --output-dir outputs/validation_reports
```

Then compare base and cohort-aware recipes on the same enriched dataset:

```bash
signal-validation compare-wr-recipes \
  --validation-dataset outputs/validation_reports/wr_validation_dataset_enriched.csv \
  --output-dir outputs
```
