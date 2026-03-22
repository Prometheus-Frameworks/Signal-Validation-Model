# WR Role and Opportunity Enrichment

## Purpose

PR8 adds a deterministic role-and-opportunity layer so the repository can test a clear research question:

> Do prior-season role and opportunity features improve breakout candidate ranking quality beyond the existing base and cohort-aware recipes?

The implementation lives in `src/enrichment/wr_role_opportunity.py` and writes artifacts that can feed directly into the existing scoring and recipe-comparison framework.

## Inputs

The enrichment step uses only canonical prior-season WR tables that already exist in the repository:

- `data/processed/wr_player_weeks.csv`
- `data/processed/wr_player_seasons.csv`
- a validation dataset, typically `outputs/validation_reports/wr_validation_dataset_enriched.csv`

No next-season outcomes are used to compute the role fields themselves.

## Output artifacts

Running the PR8 command writes:

- `outputs/validation_reports/wr_validation_dataset_role_enriched.csv`
- `outputs/validation_reports/wr_role_enrichment_summary.json`
- `outputs/validation_reports/wr_role_examples.md`

## CLI

```bash
signal-validation enrich-wr-role \
  --processed-dir data/processed \
  --validation-dataset outputs/validation_reports/wr_validation_dataset_enriched.csv \
  --output-dir outputs/validation_reports
```

## Role/opportunity fields

### `route_participation_season_avg`

The player's feature-season average route participation from the canonical season table.

Interpretation: a higher value means the player was on the field for more of the team's dropback routes.

### `target_share_season_avg`

The player's feature-season average target share from the canonical season table.

Interpretation: a higher value means the player already commanded a larger slice of team targets.

### `air_yard_share_season_avg`

The player's feature-season average air-yard share from the canonical season table.

Interpretation: this helps distinguish shallow complementary volume from more concentrated downfield opportunity.

### `routes_consistency_index`

Computed from feature-season weekly route participation values only:

```text
mean_route_participation = average(route_participation)
mean_absolute_deviation = average(abs(route_participation_week - mean_route_participation))
routes_consistency_index = clip(1 - mean_absolute_deviation / mean_route_participation, 0, 1)
```

Interpretation: players with steadier route involvement across weeks score higher.

This field is left blank when fewer than two weekly route-participation observations are available.

### `target_earning_index`

```text
target_earning_index = target_share_season_avg / route_participation_season_avg
```

Interpretation: among the routes a player actually ran, how effectively did he convert that route presence into team target share?

This field is blank when either input is missing or when route participation is zero.

### `opportunity_concentration_score`

A weighted average of the available prior-season concentration inputs:

```text
opportunity_concentration_score =
  weighted_average(
    route_participation_season_avg * 0.40,
    target_share_season_avg * 0.35,
    air_yard_share_season_avg * 0.25
  )
```

If one or more inputs are missing, the score is re-normalized across only the fields that are present.

Interpretation: this is a compact summary of whether a player already owned a concentrated passing-game role.

## Why these fields may matter for breakout detection

Breakout candidates are often not purely random. Before a next-season fantasy jump, a player may already show some combination of:

- strong route participation,
- sticky target command,
- a meaningful air-yard role,
- consistent weekly usage, and
- evidence that targets were earned efficiently once the player was on the field.

This PR does **not** claim those relationships are predictive in production. It only adds an honest, explicit way to test them historically inside the repo's existing comparison harness.

## Leakage guardrails

The implementation keeps the same no-leakage posture as earlier PRs:

- only feature-season weekly and season tables are used,
- no next-season outcome columns are referenced while deriving the role fields,
- no model fitting or learned weights are introduced,
- formulas and thresholds stay explicit in source control, and
- missing source columns stay blank rather than being fabricated.

## Limitations

- The repo can only compute role fields that are honestly supported by existing canonical columns.
- Some historical rows may lack route participation, target share, or air-yard share inputs; in those cases the derived role fields remain blank rather than guessed.
- `routes_consistency_index` depends on weekly route-participation coverage and is unavailable when too few weekly observations exist.
- The `opportunity_concentration_score` is a deterministic heuristic summary, not a trained model.
- The current implementation intentionally avoids tight runtime coupling to any external role-model repository.

## Relationship to recipe families

PR8 extends the scoring framework with a `role_signal` component family.

- Base recipes keep `role_signal` at zero weight.
- Cohort-aware recipes also keep `role_signal` at zero weight.
- Role-aware recipes such as `role_balanced` and `role_upside` assign non-zero weights to the PR8 fields.

That lets recipe comparison answer whether role-aware recipes outperform the base and cohort-aware families on the same labeled validation dataset.
