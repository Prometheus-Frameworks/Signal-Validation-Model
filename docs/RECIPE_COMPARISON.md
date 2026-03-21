# WR Recipe Comparison Framework

## What a recipe is

A recipe is an explicit deterministic configuration for the WR signal score.

Each recipe defines:

- the final component weights used to combine `usage`, `efficiency`, `development`, `stability`, and `penalty` signals,
- the internal sub-weights inside each component family, and
- the threshold ranges used when raw feature-season values are normalized onto a `0-100` scale.

Recipes live in `src/scoring/recipes.py` so the assumptions stay transparent, feature-only, and easy to edit.

## Included recipes

PR5 compares these named recipes side by side:

- `baseline_v1`
- `usage_heavy`
- `efficiency_heavy`
- `balanced_conservative`
- `upside_chaser`

The `baseline_v1` recipe preserves the PR4 score as the benchmark. The other recipes intentionally shift emphasis in small, readable ways rather than introducing new hidden logic.

## How recipes differ

All recipes reuse the same deterministic component engine from `src/scoring/wr_signal_score.py`.

They differ only through explicit configuration:

- **`baseline_v1`** keeps the PR4 balance between usage, efficiency, development, and stability.
- **`usage_heavy`** leans harder on targets per game, target share, and games played.
- **`efficiency_heavy`** gives more credit to PPR per target and players who beat their scoring context efficiently.
- **`balanced_conservative`** raises the penalty for fragile profiles and already-elite seasons.
- **`upside_chaser`** gives more credit to development headroom and softens some conservative penalties.

Because the framework keeps one shared component engine, recipe comparisons isolate the effect of changing explicit weights and thresholds.

## CLI

Run the comparison from the repository root:

```bash
signal-validation compare-wr-recipes \
  --validation-dataset outputs/validation_reports/wr_validation_dataset.csv \
  --output-dir outputs
```

## Output artifacts

The comparison command writes:

- `outputs/validation_reports/wr_recipe_comparison_summary.json`
- `outputs/validation_reports/wr_recipe_comparison_table.csv`
- `outputs/validation_reports/wr_best_recipe_candidates.md`
- `outputs/validation_reports/wr_recipe_failure_modes.md`
- `outputs/candidate_rankings/wr_candidate_rankings_<recipe>.csv` for each recipe

## Comparison metrics

Each recipe is evaluated against the same PR3 breakout labels using:

- `recipe_name`
- `candidate_count`
- `breakout_count`
- `precision@10`, `precision@20`, `precision@30`
- `recall@10`, `recall@20`, `recall@30`
- `average breakout rank`
- `median breakout rank`
- `false positives in top 20`
- `false negatives outside top 30`

Interpretation:

- **Precision@N** asks how many top-ranked candidates were actual labeled breakouts.
- **Recall@N** asks how many labeled breakouts were surfaced inside the top `N` ranks.
- **Average / median breakout rank** show where actual breakouts landed overall.
- **False positives in top 20** show how many high-ranked names failed to break out.
- **False negatives outside top 30** show how many actual breakouts the recipe buried.

## How the best recipe is selected

The framework chooses one best recipe with a documented deterministic rule:

1. highest `precision@20`
2. if tied, highest `recall@20`
3. if still tied, lowest `average breakout rank`
4. if still tied, alphabetical `recipe_name`

This rule is implemented in `src/scoring/recipe_comparison.py` and repeated in the summary artifact so the choice is reproducible.

## Why this exists before any ML layer

This framework exists before any ML work because it creates a disciplined baseline:

- every score recipe is human-readable,
- every comparison uses the same labeled validation dataset,
- failure modes can be inspected directly,
- leakage constraints remain easy to audit, and
- future ARC / role-opportunity / market-enriched recipes can plug into the same comparison harness.

It is still a historical validation tool, not a claim of predictive validity or a production projection system.
