from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.scoring.recipe_comparison import BEST_RECIPE_RULE, compare_wr_recipes, select_best_recipe
from src.scoring.recipes import DEFAULT_RECIPE, RECIPES, SignalRecipe, validate_recipe
from src.scoring.wr_signal_score import _score_candidate, build_scored_candidates


REQUIRED_COLUMNS = [
    "player_id",
    "player_name",
    "feature_season",
    "outcome_season",
    "position",
    "feature_team",
    "outcome_team",
    "has_valid_outcome",
    "feature_games_played",
    "outcome_games_played",
    "feature_total_ppr",
    "outcome_total_ppr",
    "feature_ppg",
    "outcome_ppg",
    "ppg_delta_next_season",
    "feature_finish",
    "outcome_finish",
    "finish_delta_next_season",
    "feature_targets_per_game",
    "outcome_targets_per_game",
    "feature_target_share",
    "expected_ppg_baseline",
    "career_year",
    "career_year_bucket",
    "age_bucket",
    "cohort_key",
    "cohort_player_count",
    "expected_ppg_from_cohort",
    "expected_finish_from_cohort",
    "feature_ppg_minus_cohort_expected",
    "outcome_ppg_minus_cohort_expected",
    "actual_minus_cohort_expected_ppg",
    "actual_minus_expected_ppg",
    "is_new_fantasy_starter",
    "breakout_reason",
    "breakout_label_default",
    "breakout_label_ppg_jump",
    "breakout_label_top24_jump",
]


def _base_dataset_row(player_id: str, player_name: str, feature_season: int) -> dict[str, object]:
    return {
        "player_id": player_id,
        "player_name": player_name,
        "feature_season": feature_season,
        "outcome_season": feature_season + 1,
        "position": "WR",
        "feature_team": "TST",
        "outcome_team": "TST",
        "has_valid_outcome": True,
        "feature_games_played": 17,
        "outcome_games_played": 17,
        "feature_total_ppr": 170.0,
        "outcome_total_ppr": 170.0,
        "feature_ppg": 10.0,
        "outcome_ppg": 10.0,
        "ppg_delta_next_season": 0.0,
        "feature_finish": 24,
        "outcome_finish": 24,
        "finish_delta_next_season": 0,
        "feature_targets_per_game": 7.0,
        "outcome_targets_per_game": 7.0,
        "feature_target_share": 0.20,
        "expected_ppg_baseline": 11.4,
        "career_year": 2,
        "career_year_bucket": "yr2",
        "age_bucket": "age_unknown",
        "cohort_key": "WR|yr2|age_unknown",
        "cohort_player_count": 4,
        "expected_ppg_from_cohort": 9.2,
        "expected_finish_from_cohort": 29.0,
        "feature_ppg_minus_cohort_expected": 0.8,
        "outcome_ppg_minus_cohort_expected": 0.8,
        "actual_minus_cohort_expected_ppg": 0.8,
        "actual_minus_expected_ppg": -1.4,
        "is_new_fantasy_starter": False,
        "breakout_reason": "no_breakout_trigger",
        "breakout_label_default": False,
        "breakout_label_ppg_jump": False,
        "breakout_label_top24_jump": False,
    }


def _write_validation_dataset(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        for row in rows:
            payload = {}
            for field in REQUIRED_COLUMNS:
                value = row.get(field)
                if isinstance(value, bool):
                    payload[field] = "true" if value else "false"
                elif value is None:
                    payload[field] = ""
                elif isinstance(value, float):
                    payload[field] = f"{value:.4f}"
                else:
                    payload[field] = value
            writer.writerow(payload)


def _comparison_fixture_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    breakout_ranks = {2, 6, 11, 28}
    for rank in range(1, 33):
        row = _base_dataset_row(f"wr_cmp_{rank:02d}", f"Compare {rank:02d}", 2024)
        row["feature_targets_per_game"] = round(10.2 - rank * 0.19, 4)
        row["feature_target_share"] = round(0.31 - rank * 0.004, 4)
        row["feature_ppg"] = round(17.0 - rank * 0.25, 4)
        row["feature_total_ppr"] = round(row["feature_ppg"] * 17, 4)
        row["feature_finish"] = rank
        row["expected_ppg_baseline"] = round(row["feature_ppg"] + (1.8 if rank in breakout_ranks else 0.3), 4)
        row["breakout_label_default"] = rank in breakout_ranks
        row["breakout_reason"] = "top24_jump" if rank in breakout_ranks else "no_breakout_trigger"
        rows.append(row)
    return rows


def test_recipe_outputs_are_deterministic() -> None:
    row = _base_dataset_row("wr_same", "Same", 2024)

    first = _score_candidate(row, recipe=RECIPES["usage_heavy"])
    second = _score_candidate(row, recipe=RECIPES["usage_heavy"])

    assert first == second


def test_recipe_scoring_ignores_outcome_columns() -> None:
    base = _base_dataset_row("wr_leak", "Leak Test", 2024)
    leaked = {
        **base,
        "outcome_ppg": 99.9,
        "outcome_total_ppr": 999.9,
        "ppg_delta_next_season": 89.9,
        "finish_delta_next_season": 23,
        "actual_minus_expected_ppg": 88.5,
        "breakout_label_default": True,
        "breakout_reason": "top24_jump",
    }

    base_score = _score_candidate(base, recipe=RECIPES["efficiency_heavy"])
    leaked_score = _score_candidate(leaked, recipe=RECIPES["efficiency_heavy"])

    assert base_score["wr_signal_score"] == leaked_score["wr_signal_score"]
    assert base_score["efficiency_signal"] == leaked_score["efficiency_signal"]
    assert base_score["development_signal"] == leaked_score["development_signal"]


def test_recipe_comparison_metrics_and_artifacts_are_generated(tmp_path: Path) -> None:
    dataset_path = tmp_path / "validation" / "wr_validation_dataset.csv"
    _write_validation_dataset(dataset_path, _comparison_fixture_rows())

    artifacts = compare_wr_recipes(dataset_path, output_dir=tmp_path / "outputs")

    summary = json.loads(artifacts.summary_path.read_text(encoding="utf-8"))
    comparison_rows = list(csv.DictReader(artifacts.comparison_table_path.open(encoding="utf-8", newline="")))
    best_candidates = artifacts.best_candidates_path.read_text(encoding="utf-8")
    failure_modes = artifacts.failure_modes_path.read_text(encoding="utf-8")

    assert artifacts.summary_path.exists()
    assert artifacts.comparison_table_path.exists()
    assert artifacts.best_candidates_path.exists()
    assert artifacts.failure_modes_path.exists()
    assert set(artifacts.per_recipe_candidate_paths) == set(RECIPES)
    assert len(comparison_rows) == len(RECIPES)
    assert summary["best_recipe_rule"] == BEST_RECIPE_RULE
    assert summary["best_recipe"]["recipe_name"] in RECIPES
    assert summary["best_base_recipe"]["recipe_name"] in RECIPES
    assert summary["best_cohort_recipe"]["recipe_name"] in RECIPES
    assert summary["best_role_recipe"]["recipe_name"] in RECIPES
    assert summary["cohort_vs_base_delta"] is not None
    assert summary["role_vs_base_delta"] is not None
    assert "# WR Best Recipe Candidates" in best_candidates
    assert "# WR Recipe Failure Modes" in failure_modes
    for recipe_name, path in artifacts.per_recipe_candidate_paths.items():
        assert path.exists()
        rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
        assert rows[0]["rank"] == "1"
        assert recipe_name in str(path)


def test_recipe_comparison_metrics_match_fixture_expectations(tmp_path: Path) -> None:
    dataset_path = tmp_path / "validation" / "wr_validation_dataset.csv"
    _write_validation_dataset(dataset_path, _comparison_fixture_rows())

    artifacts = compare_wr_recipes(dataset_path, output_dir=tmp_path / "outputs")
    comparison_rows = list(csv.DictReader(artifacts.comparison_table_path.open(encoding="utf-8", newline="")))
    baseline_row = next(row for row in comparison_rows if row["recipe_name"] == "baseline_v1")

    assert baseline_row["recipe_family"] == "base"
    assert baseline_row["candidate_count"] == "32"
    assert baseline_row["breakout_count"] == "4"
    assert baseline_row["precision_at_10"] == "0.3000"
    assert baseline_row["precision_at_20"] == "0.1500"
    assert baseline_row["precision_at_30"] == "0.1333"
    assert baseline_row["recall_at_10"] == "0.7500"
    assert baseline_row["recall_at_20"] == "0.7500"
    assert baseline_row["recall_at_30"] == "1.0000"
    assert baseline_row["average_breakout_rank"] == "9.0000"
    assert baseline_row["median_breakout_rank"] == "4.5000"
    assert baseline_row["false_positives_in_top_20"] == "17"
    assert baseline_row["false_negatives_outside_top_30"] == "0"


def test_best_recipe_selection_is_stable_on_ties(tmp_path: Path) -> None:
    rows = [_base_dataset_row("wr_a", "A", 2024), _base_dataset_row("wr_b", "B", 2024)]
    scored = build_scored_candidates(rows, recipe=DEFAULT_RECIPE)
    result_a = type("Result", (), {"recipe": RECIPES["baseline_v1"], "metrics": {
        "precision_at_20": 0.5, "recall_at_20": 1.0, "average_breakout_rank": 5.0
    }, "scored_candidates": scored})
    result_b = type("Result", (), {"recipe": RECIPES["usage_heavy"], "metrics": {
        "precision_at_20": 0.5, "recall_at_20": 1.0, "average_breakout_rank": 5.0
    }, "scored_candidates": scored})

    selected = select_best_recipe([result_b, result_a])

    assert selected.recipe.name == "baseline_v1"


def test_recipe_config_validation_rejects_bad_weights() -> None:
    bad_recipe = SignalRecipe(
        name="bad",
        description="bad",
        scoring_version="bad",
        component_weights={**DEFAULT_RECIPE.component_weights, "penalty_signal": 0.1},
        usage_weights=DEFAULT_RECIPE.usage_weights,
        efficiency_weights=DEFAULT_RECIPE.efficiency_weights,
        development_weights=DEFAULT_RECIPE.development_weights,
        stability_weights=DEFAULT_RECIPE.stability_weights,
        cohort_weights=DEFAULT_RECIPE.cohort_weights,
        role_weights=DEFAULT_RECIPE.role_weights,
        penalty_weights=DEFAULT_RECIPE.penalty_weights,
        thresholds=DEFAULT_RECIPE.thresholds,
    )

    with pytest.raises(ValueError, match="penalty_signal"):
        validate_recipe(bad_recipe)
