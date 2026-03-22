from __future__ import annotations

import csv
import json
from pathlib import Path

from src.cli import build_parser
from src.enrichment.wr_role_opportunity import ROLE_DATASET_COLUMNS
from src.exports.wr_exports import PLAYER_SIGNAL_CARD_COLUMNS, export_wr_results
from src.reporting.wr_case_study import build_wr_case_study
from src.scoring.recipe_comparison import compare_wr_recipes


EXPORT_GENERATED_AT = "2026-03-22T00:00:00Z"


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
        "route_participation_season_avg": 0.82,
        "target_share_season_avg": 0.20,
        "air_yard_share_season_avg": 0.28,
        "routes_consistency_index": 0.90,
        "target_earning_index": 0.24,
        "opportunity_concentration_score": 0.44,
    }


def _export_fixture_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    season_rows = [
        ("wr_2024_01", "Nova Star", 10.1, 0.31, 17.2, 5, 21.1, 12, "top24_jump", True, True, True, 3.5, 0.88, 0.31, 0.36, 0.97, 0.35, 0.57),
        ("wr_2024_02", "Volume Mirage", 9.4, 0.28, 15.7, 8, 15.7, 19, "no_breakout_trigger", False, False, False, -0.5, 0.84, 0.28, 0.33, 0.95, 0.33, 0.53),
        ("wr_2024_03", "Breakout Blaze", 8.8, 0.25, 14.5, 20, 19.3, 18, "ppg_jump", True, True, True, 3.7, 0.81, 0.25, 0.30, 0.92, 0.31, 0.49),
        ("wr_2024_04", "Hidden Surge", 7.3, 0.21, 11.3, 30, 16.1, 20, "beat_expected_baseline", True, True, True, 2.8, 0.78, 0.21, 0.26, 0.90, 0.27, 0.45),
        ("wr_2024_05", "Depth Option", 6.1, 0.18, 9.1, 40, 9.0, 39, "no_breakout_trigger", False, False, False, -0.8, 0.65, 0.18, 0.21, 0.85, 0.22, 0.38),
    ]
    for player_id, player_name, targets, share, feature_ppg, finish, outcome_ppg, outcome_finish, reason, breakout, ppg_jump, top24_jump, actual_minus_expected, route_participation, target_share, air_yards, routes_consistency, target_earning, opp_concentration in season_rows:
        row = _base_dataset_row(player_id, player_name, 2024)
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
        row["route_participation_season_avg"] = route_participation
        row["target_share_season_avg"] = target_share
        row["air_yard_share_season_avg"] = air_yards
        row["routes_consistency_index"] = routes_consistency
        row["target_earning_index"] = target_earning
        row["opportunity_concentration_score"] = opp_concentration
        rows.append(row)
    return rows


def _write_validation_dataset(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ROLE_DATASET_COLUMNS)
        writer.writeheader()
        for row in rows:
            payload = {}
            for field in ROLE_DATASET_COLUMNS:
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


def _build_export_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    dataset_path = tmp_path / "validation_reports" / "wr_validation_dataset_role_enriched.csv"
    _write_validation_dataset(dataset_path, _export_fixture_rows())

    comparison = compare_wr_recipes(dataset_path, output_dir=tmp_path / "outputs")
    build_wr_case_study(
        validation_dataset_path=dataset_path,
        comparison_summary_path=comparison.summary_path,
        candidate_dir=tmp_path / "outputs" / "candidate_rankings",
        output_dir=tmp_path / "outputs" / "case_studies",
        feature_season=2024,
        outcome_season=2025,
        surfaced_rank_cutoff=3,
    )
    return (
        dataset_path,
        comparison.summary_path,
        tmp_path / "outputs" / "candidate_rankings",
        tmp_path / "outputs" / "case_studies",
    )


def test_export_generation_is_deterministic_and_writes_manifest(tmp_path: Path) -> None:
    dataset_path, comparison_summary_path, candidate_dir, case_study_dir = _build_export_inputs(tmp_path)

    first_output = tmp_path / "exports_first"
    second_output = tmp_path / "exports_second"
    first = export_wr_results(
        validation_dataset_path=dataset_path,
        comparison_summary_path=comparison_summary_path,
        candidate_dir=candidate_dir,
        case_study_dir=case_study_dir,
        output_dir=first_output,
        feature_season=2024,
        outcome_season=2025,
        generated_at=EXPORT_GENERATED_AT,
    )
    second = export_wr_results(
        validation_dataset_path=dataset_path,
        comparison_summary_path=comparison_summary_path,
        candidate_dir=candidate_dir,
        case_study_dir=case_study_dir,
        output_dir=second_output,
        feature_season=2024,
        outcome_season=2025,
        generated_at=EXPORT_GENERATED_AT,
    )

    assert first.manifest_path.read_text(encoding="utf-8") == second.manifest_path.read_text(encoding="utf-8")
    assert first.breakout_candidates_path.read_text(encoding="utf-8") == second.breakout_candidates_path.read_text(encoding="utf-8")
    assert first.best_recipe_summary_path.read_text(encoding="utf-8") == second.best_recipe_summary_path.read_text(encoding="utf-8")
    assert first.case_study_summary_path.read_text(encoding="utf-8") == second.case_study_summary_path.read_text(encoding="utf-8")
    assert first.player_signal_cards_path.read_text(encoding="utf-8") == second.player_signal_cards_path.read_text(encoding="utf-8")

    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert manifest["generated_at"] == EXPORT_GENERATED_AT
    assert manifest["artifacts"][0]["artifact_name"] == "wr_breakout_candidates_latest.json"
    assert manifest["artifacts"][3]["field_order"] == PLAYER_SIGNAL_CARD_COLUMNS


def test_export_schema_and_field_order_are_stable(tmp_path: Path) -> None:
    dataset_path, comparison_summary_path, candidate_dir, case_study_dir = _build_export_inputs(tmp_path)

    artifacts = export_wr_results(
        validation_dataset_path=dataset_path,
        comparison_summary_path=comparison_summary_path,
        candidate_dir=candidate_dir,
        case_study_dir=case_study_dir,
        output_dir=tmp_path / "exports",
        feature_season=2024,
        outcome_season=2025,
        generated_at=EXPORT_GENERATED_AT,
    )

    breakout_candidates = json.loads(artifacts.breakout_candidates_path.read_text(encoding="utf-8"))
    best_recipe_summary = json.loads(artifacts.best_recipe_summary_path.read_text(encoding="utf-8"))
    case_study_summary = json.loads(artifacts.case_study_summary_path.read_text(encoding="utf-8"))
    signal_cards = list(csv.DictReader(artifacts.player_signal_cards_path.open(encoding="utf-8", newline="")))

    assert breakout_candidates["best_recipe_name"] == best_recipe_summary["best_recipe_name"]
    assert breakout_candidates["candidate_count"] == len(signal_cards)
    assert list(signal_cards[0].keys()) == PLAYER_SIGNAL_CARD_COLUMNS
    assert signal_cards[0]["candidate_rank"] == "1"
    assert list(breakout_candidates["candidates"][0].keys()) == [
        "player_id",
        "player_name",
        "feature_season",
        "outcome_season",
        "best_recipe_name",
        "candidate_rank",
        "final_signal_score",
        "breakout_label_default",
        "breakout_reason",
        "component_scores",
        "cohort_context",
        "role_context",
        "source_artifacts",
    ]
    assert best_recipe_summary["best_recipe_selection_rule"]["primary_metric"] == "precision_at_20"
    assert case_study_summary["feature_season"] == 2024
    assert case_study_summary["outcome_season"] == 2025
    assert case_study_summary["hit_count"] == 2
    assert case_study_summary["false_positive_count"] == 1
    assert case_study_summary["false_negative_count"] == 1
    assert "Nova Star" in case_study_summary["top_flagged_names"]
    assert sorted(case_study_summary["actual_breakout_names"]) == ["Breakout Blaze", "Hidden Surge", "Nova Star"]


def test_export_cli_parser_supports_command() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "export-wr-results",
            "--validation-dataset",
            "outputs/validation_reports/wr_validation_dataset_role_enriched.csv",
            "--comparison-summary",
            "outputs/validation_reports/wr_recipe_comparison_summary.json",
            "--candidate-dir",
            "outputs/candidate_rankings",
            "--case-study-dir",
            "outputs/case_studies",
            "--output-dir",
            "outputs/exports",
            "--feature-season",
            "2024",
            "--outcome-season",
            "2025",
        ]
    )

    assert args.command == "export-wr-results"
    assert args.feature_season == 2024
    assert args.outcome_season == 2025
