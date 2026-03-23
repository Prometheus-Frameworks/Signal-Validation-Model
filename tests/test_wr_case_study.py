from __future__ import annotations

import csv
import json
from pathlib import Path

from src.cli import build_parser
from src.enrichment.wr_cohort_baselines import COHORT_DATASET_COLUMNS
from src.reporting.wr_case_study import build_wr_case_study, load_best_recipe_from_summary
from src.scoring.recipes import RECIPES
from src.scoring.wr_signal_score import RANKING_OUTPUT_COLUMNS, build_scored_candidates


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
        "actual_minus_expected_ppg": -1.4,
        "is_new_fantasy_starter": False,
        "breakout_reason": "no_breakout_trigger",
        "breakout_label_default": False,
        "breakout_label_ppg_jump": False,
        "breakout_label_top24_jump": False,
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
    }


def _case_study_fixture_rows(*, pending_outcomes: bool = False) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    season_2024 = [
        ("wr_2024_01", "Nova Star", 10.0, 0.30, 17.0, 5, 21.0, 12, "top24_jump", True, False, True, 3.5),
        ("wr_2024_02", "Volume Mirage", 9.4, 0.28, 15.8, 8, 15.8, 19, "no_breakout_trigger", False, False, False, -0.5),
        ("wr_2024_03", "Breakout Blaze", 8.9, 0.26, 14.7, 20, 19.2, 18, "ppg_jump", True, True, True, 3.7),
        ("wr_2024_04", "Solid Starter", 8.0, 0.24, 13.8, 22, 14.0, 25, "no_breakout_trigger", False, False, False, -0.4),
        ("wr_2024_05", "Hidden Surge", 7.1, 0.20, 11.0, 30, 16.0, 20, "beat_expected_baseline", True, True, True, 2.8),
        ("wr_2024_06", "Depth Option", 6.0, 0.18, 9.2, 40, 9.2, 39, "no_breakout_trigger", False, False, False, -0.8),
    ]
    for player_id, player_name, targets, share, feature_ppg, finish, outcome_ppg, outcome_finish, reason, breakout, ppg_jump, top24_jump, actual_minus_expected in season_2024:
        row = _base_dataset_row(player_id, player_name, 2024)
        row["feature_targets_per_game"] = targets
        row["feature_target_share"] = share
        row["feature_ppg"] = feature_ppg
        row["feature_total_ppr"] = round(feature_ppg * 17, 4)
        row["feature_finish"] = finish
        row["expected_ppg_baseline"] = round(outcome_ppg - actual_minus_expected, 4)
        if pending_outcomes:
            row["has_valid_outcome"] = False
            row["outcome_team"] = None
            row["outcome_games_played"] = None
            row["outcome_total_ppr"] = None
            row["outcome_ppg"] = None
            row["ppg_delta_next_season"] = None
            row["outcome_finish"] = None
            row["finish_delta_next_season"] = None
            row["outcome_targets_per_game"] = None
            row["actual_minus_expected_ppg"] = None
            row["breakout_reason"] = "missing_outcome"
            row["breakout_label_default"] = False
            row["breakout_label_ppg_jump"] = False
            row["breakout_label_top24_jump"] = False
        else:
            row["outcome_ppg"] = outcome_ppg
            row["outcome_total_ppr"] = round(outcome_ppg * 17, 4)
            row["outcome_finish"] = outcome_finish
            row["finish_delta_next_season"] = finish - outcome_finish
            row["ppg_delta_next_season"] = round(outcome_ppg - feature_ppg, 4)
            row["actual_minus_expected_ppg"] = actual_minus_expected
            row["breakout_reason"] = reason
            row["breakout_label_default"] = breakout
            row["breakout_label_ppg_jump"] = ppg_jump
            row["breakout_label_top24_jump"] = top24_jump
        rows.append(row)

    season_2023 = [
        ("wr_2023_01", "Prior Season One", 9.8, 0.29, 16.4, 9, 19.8, 17, "ppg_jump", True, True, True, 3.0),
        ("wr_2023_02", "Prior Season Two", 6.2, 0.18, 9.5, 38, 9.3, 36, "no_breakout_trigger", False, False, False, -0.6),
    ]
    for player_id, player_name, targets, share, feature_ppg, finish, outcome_ppg, outcome_finish, reason, breakout, ppg_jump, top24_jump, actual_minus_expected in season_2023:
        row = _base_dataset_row(player_id, player_name, 2023)
        row["feature_targets_per_game"] = targets
        row["feature_target_share"] = share
        row["feature_ppg"] = feature_ppg
        row["feature_total_ppr"] = round(feature_ppg * 17, 4)
        row["feature_finish"] = finish
        row["expected_ppg_baseline"] = round(outcome_ppg - actual_minus_expected, 4)
        row["outcome_ppg"] = outcome_ppg
        row["outcome_total_ppr"] = round(outcome_ppg * 17, 4)
        row["outcome_finish"] = outcome_finish
        row["finish_delta_next_season"] = finish - outcome_finish
        row["ppg_delta_next_season"] = round(outcome_ppg - feature_ppg, 4)
        row["actual_minus_expected_ppg"] = actual_minus_expected
        row["breakout_reason"] = reason
        row["breakout_label_default"] = breakout
        row["breakout_label_ppg_jump"] = ppg_jump
        row["breakout_label_top24_jump"] = top24_jump
        rows.append(row)

    return rows


def _write_validation_dataset(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COHORT_DATASET_COLUMNS)
        writer.writeheader()
        for row in rows:
            payload = {}
            for field in COHORT_DATASET_COLUMNS:
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


def _write_best_recipe_summary(path: Path, recipe_name: str = "baseline_v1") -> None:
    recipe = RECIPES[recipe_name]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "best_recipe": {
                    "recipe_name": recipe.name,
                    "scoring_version": recipe.scoring_version,
                    "metrics": {
                        "precision_at_20": 0.1500,
                        "recall_at_20": 1.0000,
                        "average_breakout_rank": 3.0000,
                    },
                },
                "best_recipe_rule": {
                    "primary_metric": "precision_at_20",
                    "tie_breakers": ["recall_at_20", "lowest_average_breakout_rank", "recipe_name"],
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_candidate_rankings(path: Path, rows: list[dict[str, object]], recipe_name: str = "baseline_v1") -> None:
    recipe = RECIPES[recipe_name]
    path.parent.mkdir(parents=True, exist_ok=True)
    scored = build_scored_candidates(rows, recipe=recipe)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RANKING_OUTPUT_COLUMNS)
        writer.writeheader()
        for row in [candidate.ranking_row() for candidate in scored]:
            payload = {}
            for field in RANKING_OUTPUT_COLUMNS:
                value = row.get(field)
                if isinstance(value, bool):
                    payload[field] = "true" if value else "false"
                elif isinstance(value, float):
                    payload[field] = f"{value:.4f}"
                else:
                    payload[field] = value
            writer.writerow(payload)


def _build_fixture_inputs(tmp_path: Path, *, pending_outcomes: bool = False) -> tuple[Path, Path, Path]:
    dataset_path = tmp_path / "validation" / "wr_validation_dataset_enriched.csv"
    summary_path = tmp_path / "validation" / "wr_recipe_comparison_summary.json"
    candidate_path = tmp_path / "candidate_rankings" / "wr_candidate_rankings_baseline_v1.csv"

    rows = _case_study_fixture_rows(pending_outcomes=pending_outcomes)
    _write_validation_dataset(dataset_path, rows)
    _write_best_recipe_summary(summary_path)
    _write_candidate_rankings(candidate_path, rows)
    return dataset_path, summary_path, candidate_path.parent


def test_best_recipe_loading_is_deterministic(tmp_path: Path) -> None:
    summary_path = tmp_path / "validation" / "wr_recipe_comparison_summary.json"
    _write_best_recipe_summary(summary_path)

    first = load_best_recipe_from_summary(summary_path)
    second = load_best_recipe_from_summary(summary_path)

    assert first == second
    assert first.recipe_name == "baseline_v1"
    assert first.scoring_version == RECIPES["baseline_v1"].scoring_version


def test_case_study_generation_writes_expected_artifacts(tmp_path: Path) -> None:
    dataset_path, summary_path, candidate_dir = _build_fixture_inputs(tmp_path)

    artifacts = build_wr_case_study(
        validation_dataset_path=dataset_path,
        comparison_summary_path=summary_path,
        candidate_dir=candidate_dir,
        output_dir=tmp_path / "case_studies",
        feature_season=2024,
        outcome_season=2025,
        surfaced_rank_cutoff=3,
    )

    assert artifacts.case_study_markdown_path.exists()
    assert artifacts.hits_csv_path.exists()
    assert artifacts.false_positives_csv_path.exists()
    assert artifacts.false_negatives_csv_path.exists()
    assert artifacts.winner_json_path.exists()
    assert artifacts.signal_patterns_markdown_path.exists()


def test_case_study_filters_to_requested_season_pair(tmp_path: Path) -> None:
    dataset_path, summary_path, candidate_dir = _build_fixture_inputs(tmp_path)

    artifacts = build_wr_case_study(
        validation_dataset_path=dataset_path,
        comparison_summary_path=summary_path,
        candidate_dir=candidate_dir,
        output_dir=tmp_path / "case_studies",
        feature_season=2024,
        outcome_season=2025,
        surfaced_rank_cutoff=3,
    )
    markdown = artifacts.case_study_markdown_path.read_text(encoding="utf-8")

    assert "Nova Star" in markdown
    assert "Hidden Surge" in markdown
    assert "Prior Season One" not in markdown
    assert "Prior Season Two" not in markdown


def test_case_study_classifies_hits_false_positives_and_false_negatives(tmp_path: Path) -> None:
    dataset_path, summary_path, candidate_dir = _build_fixture_inputs(tmp_path)

    artifacts = build_wr_case_study(
        validation_dataset_path=dataset_path,
        comparison_summary_path=summary_path,
        candidate_dir=candidate_dir,
        output_dir=tmp_path / "case_studies",
        feature_season=2024,
        outcome_season=2025,
        surfaced_rank_cutoff=3,
    )

    hits = list(csv.DictReader(artifacts.hits_csv_path.open(encoding="utf-8", newline="")))
    false_positives = list(csv.DictReader(artifacts.false_positives_csv_path.open(encoding="utf-8", newline="")))
    false_negatives = list(csv.DictReader(artifacts.false_negatives_csv_path.open(encoding="utf-8", newline="")))
    winner = json.loads(artifacts.winner_json_path.read_text(encoding="utf-8"))

    assert [row["player_name"] for row in hits] == ["Nova Star", "Breakout Blaze"]
    assert [row["player_name"] for row in false_positives] == ["Volume Mirage"]
    assert [row["player_name"] for row in false_negatives] == ["Hidden Surge"]
    assert winner["season_pair_summary"] == {
        "actual_breakout_count": 3,
        "false_negative_count": 1,
        "false_positive_count": 1,
        "hit_count": 2,
        "missing_outcome_rows": 0,
        "total_pair_rows": 6,
        "valid_outcome_rows": 6,
    }


def test_case_study_markdown_and_signal_patterns_are_stable_on_fixture(tmp_path: Path) -> None:
    dataset_path, summary_path, candidate_dir = _build_fixture_inputs(tmp_path)

    artifacts = build_wr_case_study(
        validation_dataset_path=dataset_path,
        comparison_summary_path=summary_path,
        candidate_dir=candidate_dir,
        output_dir=tmp_path / "case_studies",
        feature_season=2024,
        outcome_season=2025,
        surfaced_rank_cutoff=3,
    )

    case_study = artifacts.case_study_markdown_path.read_text(encoding="utf-8")
    signal_patterns = artifacts.signal_patterns_markdown_path.read_text(encoding="utf-8")

    assert "# WR Breakout Case Study: 2024 to 2025" in case_study
    assert "- Using a surfaced cutoff of top 3, the model produced 2 hits, 1 false positives, and 1 false negatives." in case_study
    assert "## Top flagged candidates from `baseline_v1`" in case_study
    assert "| 1 | Nova Star | TST |" in case_study
    assert "| 5 | Hidden Surge | TST |" in case_study
    assert "Average usage signal — hits:" in case_study
    assert "## Limitations / cautions" in case_study

    assert "# WR Signal Patterns: 2024 to 2025" in signal_patterns
    assert "| hits | 2 |" in signal_patterns
    assert "| false_positives | 1 |" in signal_patterns
    assert "| false_negatives | 1 |" in signal_patterns
    assert "| ppg_jump | 1 |" in signal_patterns
    assert "| top24_jump | 1 |" in signal_patterns
    assert "- Below-hit-average usage signal:" in signal_patterns


def test_case_study_uses_pending_outcome_wording_when_no_valid_outcomes_exist(tmp_path: Path) -> None:
    dataset_path, summary_path, candidate_dir = _build_fixture_inputs(tmp_path, pending_outcomes=True)

    artifacts = build_wr_case_study(
        validation_dataset_path=dataset_path,
        comparison_summary_path=summary_path,
        candidate_dir=candidate_dir,
        output_dir=tmp_path / "case_studies",
        feature_season=2024,
        outcome_season=2025,
        surfaced_rank_cutoff=3,
    )

    case_study = artifacts.case_study_markdown_path.read_text(encoding="utf-8")
    winner = json.loads(artifacts.winner_json_path.read_text(encoding="utf-8"))

    assert "forward-looking candidate board" in case_study
    assert "Outcome evaluation is pending because 0 of 6 rows currently have valid 2025 outcomes." in case_study
    assert "Outcomes pending: final 2025 breakout evaluation will appear here once valid outcome data is complete." in case_study
    assert "- Using a surfaced cutoff of top 3, the model produced 2 hits, 1 false positives, and 1 false negatives." not in case_study
    assert winner["season_pair_summary"]["valid_outcome_rows"] == 0
    assert winner["season_pair_summary"]["missing_outcome_rows"] == 6


def test_cli_parser_includes_build_wr_case_study_command() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "build-wr-case-study",
            "--feature-season",
            "2024",
            "--outcome-season",
            "2025",
        ]
    )

    assert args.command == "build-wr-case-study"
    assert args.feature_season == 2024
    assert args.outcome_season == 2025
