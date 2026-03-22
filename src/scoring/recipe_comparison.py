"""Deterministic side-by-side comparison runner for explicit WR signal score recipes."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.scoring.recipes import RECIPES, SignalRecipe
from src.scoring.wr_signal_score import (
    RANKING_OUTPUT_COLUMNS,
    ScoredCandidate,
    build_scored_candidates,
    build_validation_summary,
    read_validation_dataset,
)

COMPARISON_TABLE_COLUMNS = [
    "recipe_name",
    "recipe_family",
    "candidate_count",
    "breakout_count",
    "precision_at_10",
    "precision_at_20",
    "precision_at_30",
    "recall_at_10",
    "recall_at_20",
    "recall_at_30",
    "average_breakout_rank",
    "median_breakout_rank",
    "false_positives_in_top_20",
    "false_negatives_outside_top_30",
]

BEST_RECIPE_RULE = {
    "primary_metric": "precision_at_20",
    "tie_breakers": ["recall_at_20", "lowest_average_breakout_rank", "recipe_name"],
    "description": (
        "Best recipe is selected by highest precision@20, then highest recall@20, "
        "then lowest average breakout rank, then alphabetical recipe name."
    ),
}


@dataclass(frozen=True)
class RecipeComparisonArtifacts:
    summary_path: Path
    comparison_table_path: Path
    best_candidates_path: Path
    failure_modes_path: Path
    per_recipe_candidate_paths: dict[str, Path]


@dataclass(frozen=True)
class RecipeRunResult:
    recipe: SignalRecipe
    scored_candidates: list[ScoredCandidate]
    metrics: dict[str, object]
    candidate_rankings_path: Path


def compare_wr_recipes(
    validation_dataset_path: str | Path,
    output_dir: str | Path = "outputs",
    recipes: Iterable[SignalRecipe] | None = None,
) -> RecipeComparisonArtifacts:
    dataset_path = Path(validation_dataset_path)
    output_dir = Path(output_dir)
    candidate_dir = output_dir / "candidate_rankings"
    report_dir = output_dir / "validation_reports"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    rows = read_validation_dataset(dataset_path)
    recipe_list = list(recipes or RECIPES.values())
    results = [
        _run_recipe(rows=rows, recipe=recipe, candidate_dir=candidate_dir)
        for recipe in sorted(recipe_list, key=lambda item: item.name)
    ]
    best_result = select_best_recipe(results)
    base_results = [result for result in results if _recipe_family(result.recipe.name) == "base"]
    cohort_results = [result for result in results if _recipe_family(result.recipe.name) == "cohort"]
    role_results = [result for result in results if _recipe_family(result.recipe.name) == "role"]
    best_base_result = select_best_recipe(base_results) if base_results else None
    best_cohort_result = select_best_recipe(cohort_results) if cohort_results else None
    best_role_result = select_best_recipe(role_results) if role_results else None

    summary_path = report_dir / "wr_recipe_comparison_summary.json"
    comparison_table_path = report_dir / "wr_recipe_comparison_table.csv"
    best_candidates_path = report_dir / "wr_best_recipe_candidates.md"
    failure_modes_path = report_dir / "wr_recipe_failure_modes.md"

    comparison_rows = [result.metrics for result in results]
    _write_csv(comparison_table_path, COMPARISON_TABLE_COLUMNS, comparison_rows)
    summary_path.write_text(
        json.dumps(
            {
                "position": "WR",
                "validation_dataset_path": str(dataset_path),
                "recipes_compared": [recipe.name for recipe in sorted(recipe_list, key=lambda item: item.name)],
                "best_recipe_rule": BEST_RECIPE_RULE,
                "best_recipe": {
                    "recipe_name": best_result.recipe.name,
                    "scoring_version": best_result.recipe.scoring_version,
                    "metrics": best_result.metrics,
                },
                "best_base_recipe": (
                    {
                        "recipe_name": best_base_result.recipe.name,
                        "scoring_version": best_base_result.recipe.scoring_version,
                        "metrics": best_base_result.metrics,
                    }
                    if best_base_result is not None
                    else None
                ),
                "best_cohort_recipe": (
                    {
                        "recipe_name": best_cohort_result.recipe.name,
                        "scoring_version": best_cohort_result.recipe.scoring_version,
                        "metrics": best_cohort_result.metrics,
                    }
                    if best_cohort_result is not None
                    else None
                ),
                "best_role_recipe": (
                    {
                        "recipe_name": best_role_result.recipe.name,
                        "scoring_version": best_role_result.recipe.scoring_version,
                        "metrics": best_role_result.metrics,
                    }
                    if best_role_result is not None
                    else None
                ),
                "cohort_vs_base_delta": (
                    _metric_delta(best_cohort_result.metrics, best_base_result.metrics)
                    if best_base_result is not None and best_cohort_result is not None
                    else None
                ),
                "role_vs_base_delta": (
                    _metric_delta(best_role_result.metrics, best_base_result.metrics)
                    if best_base_result is not None and best_role_result is not None
                    else None
                ),
                "role_vs_cohort_delta": (
                    _metric_delta(best_role_result.metrics, best_cohort_result.metrics)
                    if best_cohort_result is not None and best_role_result is not None
                    else None
                ),
                "recipe_metrics": comparison_rows,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    best_candidates_path.write_text(_build_best_recipe_markdown(best_result), encoding="utf-8")
    failure_modes_path.write_text(
        _build_failure_modes_markdown(
            results,
            best_recipe_name=best_result.recipe.name,
            best_base_recipe_name=best_base_result.recipe.name if best_base_result is not None else None,
            best_cohort_recipe_name=best_cohort_result.recipe.name if best_cohort_result is not None else None,
            best_role_recipe_name=best_role_result.recipe.name if best_role_result is not None else None,
        ),
        encoding="utf-8",
    )

    return RecipeComparisonArtifacts(
        summary_path=summary_path,
        comparison_table_path=comparison_table_path,
        best_candidates_path=best_candidates_path,
        failure_modes_path=failure_modes_path,
        per_recipe_candidate_paths={result.recipe.name: result.candidate_rankings_path for result in results},
    )


def select_best_recipe(results: Iterable[RecipeRunResult]) -> RecipeRunResult:
    ordered_results = list(results)
    if not ordered_results:
        raise ValueError("at least one recipe result is required")
    return sorted(ordered_results, key=_best_recipe_sort_key)[0]


def _best_recipe_sort_key(result: RecipeRunResult) -> tuple[float, float, float, str]:
    average_breakout_rank = result.metrics["average_breakout_rank"]
    if average_breakout_rank is None:
        average_breakout_rank = float("inf")
    return (
        -float(result.metrics["precision_at_20"]),
        -float(result.metrics["recall_at_20"]),
        float(average_breakout_rank),
        result.recipe.name,
    )


def _run_recipe(rows: list[dict[str, object]], recipe: SignalRecipe, candidate_dir: Path) -> RecipeRunResult:
    scored_candidates = build_scored_candidates(rows, recipe=recipe)
    summary = build_validation_summary(scored_candidates, recipe=recipe)
    metrics = {
        "recipe_name": recipe.name,
        "recipe_family": _recipe_family(recipe.name),
        "candidate_count": summary["candidate_count"],
        "breakout_count": summary["breakout_count"],
        "precision_at_10": summary["precision_at_10"],
        "precision_at_20": summary["precision_at_20"],
        "precision_at_30": summary["precision_at_30"],
        "recall_at_10": summary["recall_at_10"],
        "recall_at_20": summary["recall_at_20"],
        "recall_at_30": summary["recall_at_30"],
        "average_breakout_rank": summary["average_rank_of_actual_breakouts"],
        "median_breakout_rank": summary["median_rank_of_actual_breakouts"],
        "false_positives_in_top_20": summary["false_positives_in_top_20"],
        "false_negatives_outside_top_30": summary["false_negatives_outside_top_30"],
    }
    path = candidate_dir / f"wr_candidate_rankings_{recipe.name}.csv"
    _write_csv(path, RANKING_OUTPUT_COLUMNS, [row.ranking_row() for row in scored_candidates])
    return RecipeRunResult(
        recipe=recipe,
        scored_candidates=scored_candidates,
        metrics=metrics,
        candidate_rankings_path=path,
    )


def _build_best_recipe_markdown(best_result: RecipeRunResult) -> str:
    lines = [
        "# WR Best Recipe Candidates",
        "",
        f"Best recipe: `{best_result.recipe.name}`.",
        "",
        BEST_RECIPE_RULE["description"],
        "",
        f"Scoring version: `{best_result.recipe.scoring_version}`.",
        "",
    ]
    for feature_season in sorted({row.feature_season for row in best_result.scored_candidates}):
        season_rows = [
            row for row in best_result.scored_candidates if row.feature_season == feature_season and row.rank <= 20
        ]
        lines.extend(
            [
                f"## Feature season {feature_season} top 20",
                "",
                _markdown_candidates(season_rows),
                "",
            ]
        )
    return "\n".join(lines)


def _build_failure_modes_markdown(
    results: list[RecipeRunResult],
    best_recipe_name: str,
    best_base_recipe_name: str | None = None,
    best_cohort_recipe_name: str | None = None,
    best_role_recipe_name: str | None = None,
) -> str:
    lines = [
        "# WR Recipe Failure Modes",
        "",
        "Side-by-side deterministic comparison of how each recipe missed breakout labels or elevated false positives.",
        "",
        f"Best recipe under the documented rule: `{best_recipe_name}`.",
        (f"Best base recipe: `{best_base_recipe_name}`." if best_base_recipe_name is not None else "No base recipes were supplied."),
        (
            f"Best cohort-aware recipe: `{best_cohort_recipe_name}`."
            if best_cohort_recipe_name is not None
            else "No cohort-aware recipes were supplied."
        ),
        (
            f"Best role-aware recipe: `{best_role_recipe_name}`."
            if best_role_recipe_name is not None
            else "No role-aware recipes were supplied."
        ),
        "",
        "## Metric table",
        "",
        _markdown_metric_table(results),
        "",
    ]
    for result in results:
        false_positives = [
            row for row in result.scored_candidates if row.has_valid_outcome and row.rank <= 20 and not row.breakout_label_default
        ][:10]
        false_negatives = [
            row for row in result.scored_candidates if row.has_valid_outcome and row.breakout_label_default and row.rank > 30
        ][:10]
        lines.extend(
            [
                f"## {result.recipe.name}",
                "",
                f"- family: {_recipe_family(result.recipe.name)}",
                f"- precision@20: {result.metrics['precision_at_20']:.4f}",
                f"- recall@20: {result.metrics['recall_at_20']:.4f}",
                f"- false positives in top 20: {result.metrics['false_positives_in_top_20']}",
                f"- false negatives outside top 30: {result.metrics['false_negatives_outside_top_30']}",
                "",
                "### Top false positives",
                "",
                _markdown_candidates(false_positives, include_reason=True),
                "",
                "### Top false negatives",
                "",
                _markdown_candidates(false_negatives, include_reason=True),
                "",
            ]
        )
    return "\n".join(lines)


def _markdown_metric_table(results: list[RecipeRunResult]) -> str:
    lines = [
        "| recipe_name | family | p@10 | p@20 | p@30 | r@10 | r@20 | r@30 | avg breakout rank | median breakout rank | fp top20 | fn outside30 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in results:
        metrics = result.metrics
        average_rank = metrics["average_breakout_rank"]
        median_rank = metrics["median_breakout_rank"]
        lines.append(
            "| {recipe} | {family} | {p10:.4f} | {p20:.4f} | {p30:.4f} | {r10:.4f} | {r20:.4f} | {r30:.4f} | {avg} | {median} | {fp} | {fn} |".format(
                recipe=result.recipe.name,
                family=_recipe_family(result.recipe.name),
                p10=metrics["precision_at_10"],
                p20=metrics["precision_at_20"],
                p30=metrics["precision_at_30"],
                r10=metrics["recall_at_10"],
                r20=metrics["recall_at_20"],
                r30=metrics["recall_at_30"],
                avg=f"{average_rank:.4f}" if average_rank is not None else "n/a",
                median=f"{median_rank:.4f}" if median_rank is not None else "n/a",
                fp=metrics["false_positives_in_top_20"],
                fn=metrics["false_negatives_outside_top_30"],
            )
        )
    return "\n".join(lines)


def _markdown_candidates(rows: list[ScoredCandidate], include_reason: bool = False) -> str:
    if not rows:
        return "_No rows in this category._"
    if include_reason:
        header = "| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |"
        separator = "| ---: | ---: | --- | --- | ---: | --- | --- |"
    else:
        header = "| feature_season | rank | player_id | player_name | score | breakout_label |"
        separator = "| ---: | ---: | --- | --- | ---: | --- |"

    lines = [header, separator]
    for row in rows:
        line = (
            f"| {row.feature_season} | {row.rank} | {row.player_id} | {row.player_name} "
            f"| {row.wr_signal_score:.4f} | {'true' if row.breakout_label_default else 'false'} |"
        )
        if include_reason:
            line = line[:-1] + f" {row.breakout_reason} |"
        lines.append(line)
    return "\n".join(lines)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _serialize_value(row.get(field)) for field in fieldnames})


def _serialize_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return value


def _recipe_family(recipe_name: str) -> str:
    if recipe_name.startswith("cohort_"):
        return "cohort"
    if recipe_name.startswith("role_"):
        return "role"
    return "base"


def _metric_delta(cohort_metrics: dict[str, object], base_metrics: dict[str, object]) -> dict[str, float | None]:
    return {
        "precision_at_10_delta": round(float(cohort_metrics["precision_at_10"]) - float(base_metrics["precision_at_10"]), 4),
        "precision_at_20_delta": round(float(cohort_metrics["precision_at_20"]) - float(base_metrics["precision_at_20"]), 4),
        "precision_at_30_delta": round(float(cohort_metrics["precision_at_30"]) - float(base_metrics["precision_at_30"]), 4),
        "recall_at_10_delta": round(float(cohort_metrics["recall_at_10"]) - float(base_metrics["recall_at_10"]), 4),
        "recall_at_20_delta": round(float(cohort_metrics["recall_at_20"]) - float(base_metrics["recall_at_20"]), 4),
        "recall_at_30_delta": round(float(cohort_metrics["recall_at_30"]) - float(base_metrics["recall_at_30"]), 4),
        "average_breakout_rank_delta": _optional_metric_delta(
            cohort_metrics["average_breakout_rank"], base_metrics["average_breakout_rank"]
        ),
        "median_breakout_rank_delta": _optional_metric_delta(
            cohort_metrics["median_breakout_rank"], base_metrics["median_breakout_rank"]
        ),
    }


def _optional_metric_delta(left: object, right: object) -> float | None:
    if left is None or right is None:
        return None
    return round(float(left) - float(right), 4)
