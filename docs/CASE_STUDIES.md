# WR Case Studies

PR7 adds a deterministic season-pair reporting layer that turns the existing WR validation, recipe comparison, and candidate ranking outputs into a readable case study.

## Purpose

The case-study layer answers questions like:

- Which WRs did the model surface for a given feature season?
- Which actual breakouts did that surfaced list catch?
- Which players became false positives or false negatives under the documented surfaced cutoff?
- Which deterministic recipe won the comparison run that fed the case study?

This layer is retrospective reporting only. It does not train a model, create live projections, or claim predictive certainty.

## Inputs

`signal-validation build-wr-case-study` expects the existing deterministic artifacts from earlier PRs:

- enriched validation dataset: `outputs/validation_reports/wr_validation_dataset_enriched.csv`
- recipe comparison summary: `outputs/validation_reports/wr_recipe_comparison_summary.json`
- per-recipe candidate rankings directory: `outputs/candidate_rankings`

The case-study builder loads the `best_recipe` block from the comparison summary, then reads that recipe's candidate ranking file from `outputs/candidate_rankings/wr_candidate_rankings_<recipe_name>.csv`.

## CLI

```bash
signal-validation build-wr-case-study \
  --validation-dataset outputs/validation_reports/wr_validation_dataset_enriched.csv \
  --comparison-summary outputs/validation_reports/wr_recipe_comparison_summary.json \
  --candidate-dir outputs/candidate_rankings \
  --output-dir outputs/case_studies \
  --feature-season 2024 \
  --outcome-season 2025
```

## Artifacts

For a season pair `<feature_season> -> <outcome_season>`, the command writes:

- `outputs/case_studies/wr_breakout_case_study_<feature_season>_to_<outcome_season>.md`
- `outputs/case_studies/wr_breakout_hits_<feature_season>_to_<outcome_season>.csv`
- `outputs/case_studies/wr_breakout_false_positives_<feature_season>_to_<outcome_season>.csv`
- `outputs/case_studies/wr_breakout_false_negatives_<feature_season>_to_<outcome_season>.csv`
- `outputs/case_studies/wr_recipe_winner_<feature_season>_to_<outcome_season>.json`
- `outputs/case_studies/wr_signal_patterns_<feature_season>_to_<outcome_season>.md`

## How the best recipe is sourced

The case-study module does **not** re-run recipe selection logic on its own.

Instead it:

1. reads `best_recipe.recipe_name` and `best_recipe.scoring_version` from the comparison summary;
2. validates that the recipe still exists locally in `src/scoring/recipes.py`;
3. loads that recipe's candidate ranking CSV from the candidate rankings directory; and
4. uses the same local recipe definition to recompute inspectable component signals for the requested season pair.

This keeps the report tied to the deterministic comparison outputs while still allowing component-level pattern summaries.

## Hit / false-positive / false-negative definitions

By default, a player is considered **surfaced** when they appear inside the best recipe's top 20 ranks for the requested feature season.

Within the requested season pair:

- **Actual breakout**: `breakout_label_default == true` and `has_valid_outcome == true`
- **Hit**: surfaced candidate who is also an actual breakout
- **False positive**: surfaced candidate with a valid outcome who is **not** an actual breakout
- **False negative**: actual breakout with a valid outcome whose rank falls **outside** the surfaced cutoff

Rows with missing outcomes are excluded from hit/miss accounting and are called out in the markdown report.

## Signal-pattern summaries

The signal-pattern markdown is deterministic and inspectable. It includes simple aggregates such as:

- average score and component values for surfaced candidates, actual breakouts, hits, false positives, and false negatives;
- breakout-reason counts among hits; and
- explicit miss-pattern counts, such as below-hit-average usage or efficiency and non-positive actual-minus-expected PPG among false positives.

## Limitations of season-pair reporting

- The report depends on label definitions already established in the WR breakout label engine.
- The surfaced cutoff is a reporting choice; changing it changes hit/miss counts.
- Season-pair reports only evaluate rows with valid outcomes for that exact feature-season / outcome-season pair.
- The case study is meant for factual retrospective analysis, not certainty claims about future player outcomes.
