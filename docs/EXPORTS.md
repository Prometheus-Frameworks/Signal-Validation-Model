# WR Downstream Exports

PR9 adds deterministic downstream export adapters so other repos can consume Signal-Validation-Model outputs without manually reading markdown reports.

## Intended consumers

- **Primary target:** TIBER Fantasy style downstream ranking or workflow repos.
- **Also suitable for:** notebooks, schedulers, CI checks, or other machine-consumption pipelines that need stable JSON/CSV contracts.
- **Not for:** live scoring, online inference, or any workflow that expects the export layer to rescore players or relabel outcomes.

## Export command

```bash
signal-validation export-wr-results \
  --validation-dataset outputs/validation_reports/wr_validation_dataset_role_enriched.csv \
  --comparison-summary outputs/validation_reports/wr_recipe_comparison_summary.json \
  --candidate-dir outputs/candidate_rankings \
  --case-study-dir outputs/case_studies \
  --output-dir outputs/exports \
  --feature-season 2024 \
  --outcome-season 2025
```

## Design rules

- Uses only existing validated artifacts.
- Does **not** rescore candidates in the export layer.
- Does **not** relabel breakouts in the export layer.
- Keeps explicit field names and explicit ordering.
- Emits boring, machine-friendly JSON and CSV contracts.

## Export artifacts

### `wr_breakout_candidates_latest.json`
Canonical candidate board for the selected season pair.

**Purpose**
- Feed downstream ranking boards.
- Preserve best-recipe rank order, final score, component scores, and cohort/role context in one JSON artifact.

**Stable fields**
- `player_id`
- `player_name`
- `feature_season`
- `outcome_season`
- `best_recipe_name`
- `candidate_rank`
- `final_signal_score`
- `breakout_label_default`
- `breakout_reason`
- `component_scores`
- `cohort_context`
- `role_context`
- `source_artifacts`

### `wr_best_recipe_summary.json`
Machine-readable summary of the already-selected best recipe.

**Purpose**
- Tell downstream consumers which recipe won.
- Surface the selection rule and top evaluation metrics without parsing the full comparison report.

**Stable fields**
- `best_recipe_name`
- `recipe_family`
- `best_recipe_selection_rule`
- `key_metrics`
- `scoring_version`
- `generated_at`
- `source_artifacts`

### `wr_case_study_summary_<feature_season>_to_<outcome_season>.json`
Compact season-pair export distilled from case-study outputs.

**Purpose**
- Provide machine-readable hit / miss counts for retrospective validation slices.
- Expose the most important names from the season-pair report without requiring markdown parsing.

**Stable fields**
- `feature_season`
- `outcome_season`
- `best_recipe_name`
- `hit_count`
- `false_positive_count`
- `false_negative_count`
- `top_flagged_names`
- `actual_breakout_names`
- `hit_names`
- `false_positive_names`
- `false_negative_names`
- `generated_at`
- `source_artifacts`

### `wr_player_signal_cards_<feature_season>.csv`
Flat player-level export for the selected feature season.

**Purpose**
- Give downstream tools a simple table that can be joined, filtered, or loaded directly.
- Preserve stable field ordering for CSV consumers.

**Stable field order**
1. `player_id`
2. `player_name`
3. `feature_season`
4. `outcome_season`
5. `feature_team`
6. `best_recipe_name`
7. `candidate_rank`
8. `final_signal_score`
9. `breakout_label_default`
10. `breakout_reason`
11. `usage_signal`
12. `efficiency_signal`
13. `development_signal`
14. `stability_signal`
15. `cohort_signal`
16. `role_signal`
17. `penalty_signal`
18. `career_year`
19. `career_year_bucket`
20. `age_bucket`
21. `cohort_key`
22. `cohort_player_count`
23. `feature_ppg`
24. `feature_finish`
25. `feature_targets_per_game`
26. `feature_target_share`
27. `expected_ppg_baseline`
28. `route_participation_season_avg`
29. `target_share_season_avg`
30. `air_yard_share_season_avg`
31. `routes_consistency_index`
32. `target_earning_index`
33. `opportunity_concentration_score`
34. `has_valid_outcome`

### `export_manifest.json`
Manifest describing the export batch.

**Purpose**
- Let downstream repos discover artifacts and confirm record counts / field order.
- Keep input source references explicit.

**Stable fields**
- `feature_season`
- `outcome_season`
- `best_recipe_name`
- `generated_at`
- `artifacts`
- `input_artifacts`
- `season_pair_summary`

## Stable vs. revision-prone contract areas

### Stable in PR9
- Artifact filenames listed above.
- CSV field order for `wr_player_signal_cards_<feature_season>.csv`.
- The meaning of `candidate_rank`, `final_signal_score`, and the explicit component score columns.
- The export-layer rule that inputs come from validated upstream artifacts only.

### Subject to future revision
- Additional optional fields in JSON payloads.
- Additional export adapters for other positions or consumers.
- Additional manifest metadata such as content digests or compatibility tags.

Future revisions should prefer additive changes over renames or silent semantic shifts.
