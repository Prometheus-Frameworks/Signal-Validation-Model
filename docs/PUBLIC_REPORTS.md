# WR Public Reports

PR10 adds a deterministic public-facing report pack generator for a single WR season pair.

## Purpose

The public layer turns already-validated research outputs into a readable report that can answer a simple retrospective question:

> Using feature-season 2024 information, which 2025 WR breakout candidates were surfaced, which calls were hits or misses, which recipe performed best, and which signals stood out?

This is a presentation layer only. It does not rescore players, relabel outcomes, or add hidden transformations.

## CLI

```bash
signal-validation build-wr-public-report \
  --exports-dir outputs/exports \
  --case-study-dir outputs/case_studies \
  --comparison-summary outputs/validation_reports/wr_recipe_comparison_summary.json \
  --output-dir outputs/public \
  --feature-season 2024 \
  --outcome-season 2025
```

## Public artifacts

For a season pair `<feature_season> -> <outcome_season>`, the command writes:

- `outputs/public/wr_public_breakout_report_<feature_season>_to_<outcome_season>.md`
- `outputs/public/wr_public_breakout_report_<feature_season>_to_<outcome_season>.json`
- `outputs/public/wr_public_top_candidates_<feature_season>_to_<outcome_season>.csv`
- `outputs/public/wr_public_hits_and_misses_<feature_season>_to_<outcome_season>.csv`
- `outputs/public/wr_public_methodology_summary.md`
- `outputs/public/wr_public_disclaimer.md`

## Source-of-truth inputs

The public pack uses only existing validated/exported outputs:

- `outputs/exports/wr_breakout_candidates_latest.json`
- `outputs/exports/wr_case_study_summary_<feature_season>_to_<outcome_season>.json`
- `outputs/case_studies/wr_breakout_hits_<feature_season>_to_<outcome_season>.csv`
- `outputs/case_studies/wr_breakout_false_positives_<feature_season>_to_<outcome_season>.csv`
- `outputs/case_studies/wr_breakout_false_negatives_<feature_season>_to_<outcome_season>.csv`
- `outputs/validation_reports/wr_recipe_comparison_summary.json`

The generator copies ordering and conclusions from those artifacts, then applies public-safe formatting only.

## What is included

- Title and requested season pair.
- Concise executive summary.
- Best recipe name and family.
- Top candidate board.
- Actual breakouts and correctly surfaced breakouts.
- Notable misses and false positives.
- Short signal takeaways from descriptive averages already present in source artifacts.
- Methodology summary and disclaimer artifacts.

## What is deliberately omitted

- Internal formula-note fields from component exports.
- Repo-debug fields and implementation scaffolding.
- Full threshold definitions or re-explanations of lower-level scoring internals.
- Any new scoring, relabeling, or confidence claims.

## Public-safe formatting rules

- Noisy numeric fields are rounded for readability.
- Only the most relevant public-facing columns are preserved in CSV outputs.
- Markdown sections and JSON keys are emitted in stable deterministic order.
- The tone stays factual, concise, and retrospective.

## Limitations

- This is retrospective validation reporting, not a live prediction system.
- Report conclusions inherit the upstream label definitions, surfaced-cutoff choices, and export scope.
- Public summaries are intentionally simplified, so they are easier to read but less detailed than internal research artifacts.
- Because the report is anchored to a single season pair, it should not be treated as a universal claim about future WR outcomes.
