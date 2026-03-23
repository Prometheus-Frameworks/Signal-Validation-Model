# WR Public Findings

PR11 adds a deterministic public-facing findings/narrative pack for a single WR season pair.

## Purpose

The findings pack is a polished retrospective summary layer built on top of already validated WR artifacts.
It answers a public-safe version of this question:

> What did the model learn from this season pair, which recipe family performed best, where did cohort or role context help, and which players were the most notable hits and misses?

The generator does not retrain, rescore, relabel, or alter any underlying conclusions.

## CLI

```bash
signal-validation build-wr-public-findings \
  --public-dir outputs/public \
  --comparison-summary outputs/validation_reports/wr_recipe_comparison_summary.json \
  --case-study-dir outputs/case_studies \
  --exports-dir outputs/exports \
  --output-dir outputs/public \
  --feature-season 2024 \
  --outcome-season 2025
```

`--output-dir` is optional. If omitted, the command writes to `--public-dir`.

## Output artifacts

For a season pair `<feature_season> -> <outcome_season>`, the command writes:

- `outputs/public/wr_public_findings_<feature_season>_to_<outcome_season>.md`
- `outputs/public/wr_public_recipe_comparison_<feature_season>_to_<outcome_season>.csv`
- `outputs/public/wr_public_notable_hits_<feature_season>_to_<outcome_season>.csv`
- `outputs/public/wr_public_notable_misses_<feature_season>_to_<outcome_season>.csv`
- `outputs/public/wr_public_key_takeaways_<feature_season>_to_<outcome_season>.json`

## Allowed inputs

The findings pack uses only existing validated/exported artifacts:

- `outputs/validation_reports/wr_recipe_comparison_summary.json`
- `outputs/exports/wr_breakout_candidates_latest.json`
- `outputs/exports/wr_case_study_summary_<feature_season>_to_<outcome_season>.json`
- `outputs/case_studies/wr_breakout_hits_<feature_season>_to_<outcome_season>.csv`
- `outputs/case_studies/wr_breakout_false_positives_<feature_season>_to_<outcome_season>.csv`
- `outputs/case_studies/wr_breakout_false_negatives_<feature_season>_to_<outcome_season>.csv`

No hidden transformations are applied beyond deterministic formatting, sorting, and public-safe field selection.

## Required narrative sections

The main markdown report includes:

- concise executive summary
- best overall recipe and recipe family
- best base recipe
- best cohort-aware recipe
- best role-aware recipe
- whether cohort improved over base
- whether role improved over base and cohort
- notable player hits
- notable player misses
- public-safe signal takeaways
- limitations and cautions

## Deterministic notable-player rules

### Notable hits

Hits are selected from `wr_breakout_hits_<feature>_to_<outcome>.csv` and sorted by:

1. highest `actual_minus_expected_ppg`
2. highest `outcome_ppg`
3. best candidate rank
4. alphabetical player name

The findings pack writes the top `N` rows after that ordering.

### Notable misses

Misses are selected from both false-negative and false-positive case-study CSVs.

- The miss list reserves half its slots for false negatives.
- False negatives are sorted by highest `actual_minus_expected_ppg`, then highest `outcome_ppg`, then best rank, then player name.
- The miss list reserves the remaining half for false positives.
- False positives are sorted by lowest `actual_minus_expected_ppg`, then highest `wr_signal_score`, then best rank, then player name.
- If one miss type has fewer rows than its reserved share, the leftover slots are refilled by the remaining miss rows with the largest absolute `actual_minus_expected_ppg`.

This rule is explicit, deterministic, and public-safe.

## Interpretation notes

- Family-improvement statements are derived from the already published comparison deltas.
- A status can be `improved`, `declined`, `matched`, or `not_available`.
- The findings pack stays retrospective and should not be treated as a live forecasting system.
