from __future__ import annotations

import csv
import json
from pathlib import Path

from src.cli import build_parser
from src.enrichment.wr_role_opportunity import ROLE_DATASET_COLUMNS
from src.exports.wr_exports import export_wr_results
from src.public.wr_public_findings import (
    PUBLIC_NOTABLE_HIT_COLUMNS,
    PUBLIC_NOTABLE_MISS_COLUMNS,
    PUBLIC_RECIPE_COMPARISON_COLUMNS,
    build_wr_public_findings,
)
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


def _public_fixture_rows(*, pending_outcomes: bool = False) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    season_2024 = [
        ("wr_2024_01", "Nova Star", 10.1, 0.31, 17.2, 5, 21.1, 12, "top24_jump", True, True, True, 3.5, 0.88, 0.31, 0.36, 0.97, 0.35, 0.57),
        ("wr_2024_02", "Volume Mirage", 9.4, 0.28, 15.7, 8, 15.7, 19, "no_breakout_trigger", False, False, False, -0.5, 0.84, 0.28, 0.33, 0.95, 0.33, 0.53),
        ("wr_2024_03", "Breakout Blaze", 8.8, 0.25, 14.5, 20, 19.3, 18, "ppg_jump", True, True, True, 3.7, 0.81, 0.25, 0.30, 0.92, 0.31, 0.49),
        ("wr_2024_04", "Hidden Surge", 7.3, 0.21, 11.3, 30, 16.1, 20, "beat_expected_baseline", True, True, True, 2.8, 0.78, 0.21, 0.26, 0.90, 0.27, 0.45),
        ("wr_2024_05", "Depth Option", 6.1, 0.18, 9.1, 40, 9.0, 39, "no_breakout_trigger", False, False, False, -0.8, 0.65, 0.18, 0.21, 0.85, 0.22, 0.38),
    ]
    season_2023 = [
        ("wr_2023_01", "Prior Season One", 9.7, 0.29, 16.1, 11, 19.8, 17, "ppg_jump", True, True, True, 3.1, 0.86, 0.29, 0.34, 0.96, 0.34, 0.54),
        ("wr_2023_02", "Prior Season Two", 6.2, 0.18, 9.4, 37, 9.2, 35, "no_breakout_trigger", False, False, False, -0.6, 0.66, 0.18, 0.22, 0.84, 0.23, 0.39),
    ]
    for feature_season, season_rows in ((2024, season_2024), (2023, season_2023)):
        for player_id, player_name, targets, share, feature_ppg, finish, outcome_ppg, outcome_finish, reason, breakout, ppg_jump, top24_jump, actual_minus_expected, route_participation, target_share, air_yards, routes_consistency, target_earning, opp_concentration in season_rows:
            row = _base_dataset_row(player_id, player_name, feature_season)
            row["feature_targets_per_game"] = targets
            row["feature_target_share"] = share
            row["feature_ppg"] = feature_ppg
            row["feature_total_ppr"] = round(feature_ppg * 17, 4)
            row["feature_finish"] = finish
            row["expected_ppg_baseline"] = round(outcome_ppg - actual_minus_expected, 4)
            if pending_outcomes and feature_season == 2024:
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


def _overwrite_comparison_summary(summary_path: Path) -> None:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    metrics_by_recipe = {
        "balanced_conservative": {"recipe_family": "base", "precision_at_20": 0.33, "recall_at_20": 0.40, "average_breakout_rank": 7.0, "false_positives_in_top_20": 1, "false_negatives_outside_top_30": 1},
        "baseline_v1": {"recipe_family": "base", "precision_at_20": 0.20, "recall_at_20": 0.20, "average_breakout_rank": 9.0, "false_positives_in_top_20": 2, "false_negatives_outside_top_30": 1},
        "cohort_balanced": {"recipe_family": "cohort", "precision_at_20": 0.36, "recall_at_20": 0.40, "average_breakout_rank": 6.0, "false_positives_in_top_20": 1, "false_negatives_outside_top_30": 1},
        "cohort_upside": {"recipe_family": "cohort", "precision_at_20": 0.30, "recall_at_20": 0.40, "average_breakout_rank": 7.0, "false_positives_in_top_20": 1, "false_negatives_outside_top_30": 1},
        "role_balanced": {"recipe_family": "role", "precision_at_20": 0.42, "recall_at_20": 0.50, "average_breakout_rank": 5.0, "false_positives_in_top_20": 1, "false_negatives_outside_top_30": 0},
        "role_upside": {"recipe_family": "role", "precision_at_20": 0.38, "recall_at_20": 0.50, "average_breakout_rank": 6.0, "false_positives_in_top_20": 1, "false_negatives_outside_top_30": 0},
    }
    updated_metrics = []
    for metrics in summary["recipe_metrics"]:
        replacement = metrics_by_recipe.get(metrics["recipe_name"])
        if replacement is None:
            updated_metrics.append(metrics)
            continue
        merged = dict(metrics)
        merged.update(replacement)
        updated_metrics.append(merged)
    summary["recipe_metrics"] = updated_metrics
    summary["best_recipe"]["recipe_name"] = "role_balanced"
    summary["best_recipe"]["scoring_version"] = "wr_signal_score_role_balanced_v1"
    summary["best_recipe"]["metrics"] = next(row for row in updated_metrics if row["recipe_name"] == "role_balanced")
    summary["best_base_recipe"]["metrics"] = next(row for row in updated_metrics if row["recipe_name"] == "balanced_conservative")
    summary["best_cohort_recipe"]["recipe_name"] = "cohort_balanced"
    summary["best_cohort_recipe"]["scoring_version"] = "wr_signal_score_cohort_balanced_v1"
    summary["best_cohort_recipe"]["metrics"] = next(row for row in updated_metrics if row["recipe_name"] == "cohort_balanced")
    summary["best_role_recipe"]["recipe_name"] = "role_balanced"
    summary["best_role_recipe"]["scoring_version"] = "wr_signal_score_role_balanced_v1"
    summary["best_role_recipe"]["metrics"] = next(row for row in updated_metrics if row["recipe_name"] == "role_balanced")
    summary["cohort_vs_base_delta"] = {
        "average_breakout_rank_delta": -1.0,
        "median_breakout_rank_delta": -1.0,
        "precision_at_10_delta": 0.0,
        "precision_at_20_delta": 0.03,
        "precision_at_30_delta": 0.03,
        "recall_at_10_delta": 0.0,
        "recall_at_20_delta": 0.0,
        "recall_at_30_delta": 0.0,
    }
    summary["role_vs_base_delta"] = {
        "average_breakout_rank_delta": -2.0,
        "median_breakout_rank_delta": -2.0,
        "precision_at_10_delta": 0.0,
        "precision_at_20_delta": 0.09,
        "precision_at_30_delta": 0.09,
        "recall_at_10_delta": 0.0,
        "recall_at_20_delta": 0.10,
        "recall_at_30_delta": 0.10,
    }
    summary["role_vs_cohort_delta"] = {
        "average_breakout_rank_delta": -1.0,
        "median_breakout_rank_delta": -1.0,
        "precision_at_10_delta": 0.0,
        "precision_at_20_delta": 0.06,
        "precision_at_30_delta": 0.06,
        "recall_at_10_delta": 0.0,
        "recall_at_20_delta": 0.10,
        "recall_at_30_delta": 0.10,
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_public_inputs(tmp_path: Path, *, pending_outcomes: bool = False) -> tuple[Path, Path, Path]:
    dataset_path = tmp_path / "validation_reports" / "wr_validation_dataset_role_enriched.csv"
    _write_validation_dataset(dataset_path, _public_fixture_rows(pending_outcomes=pending_outcomes))

    comparison = compare_wr_recipes(dataset_path, output_dir=tmp_path / "outputs")
    _overwrite_comparison_summary(comparison.summary_path)
    build_wr_case_study(
        validation_dataset_path=dataset_path,
        comparison_summary_path=comparison.summary_path,
        candidate_dir=tmp_path / "outputs" / "candidate_rankings",
        output_dir=tmp_path / "outputs" / "case_studies",
        feature_season=2024,
        outcome_season=2025,
        surfaced_rank_cutoff=3,
    )
    export_wr_results(
        validation_dataset_path=dataset_path,
        comparison_summary_path=comparison.summary_path,
        candidate_dir=tmp_path / "outputs" / "candidate_rankings",
        case_study_dir=tmp_path / "outputs" / "case_studies",
        output_dir=tmp_path / "outputs" / "exports",
        feature_season=2024,
        outcome_season=2025,
        generated_at=EXPORT_GENERATED_AT,
    )
    return comparison.summary_path, tmp_path / "outputs" / "exports", tmp_path / "outputs" / "case_studies"


def test_public_findings_generation_is_deterministic(tmp_path: Path) -> None:
    comparison_summary_path, exports_dir, case_study_dir = _build_public_inputs(tmp_path)

    first = build_wr_public_findings(
        comparison_summary_path=comparison_summary_path,
        case_study_dir=case_study_dir,
        exports_dir=exports_dir,
        output_dir=tmp_path / "public_first",
        feature_season=2024,
        outcome_season=2025,
    )
    second = build_wr_public_findings(
        comparison_summary_path=comparison_summary_path,
        case_study_dir=case_study_dir,
        exports_dir=exports_dir,
        output_dir=tmp_path / "public_second",
        feature_season=2024,
        outcome_season=2025,
    )

    assert first.findings_markdown_path.read_text(encoding="utf-8") == second.findings_markdown_path.read_text(encoding="utf-8")
    assert first.recipe_comparison_csv_path.read_text(encoding="utf-8") == second.recipe_comparison_csv_path.read_text(encoding="utf-8")
    assert first.notable_hits_csv_path.read_text(encoding="utf-8") == second.notable_hits_csv_path.read_text(encoding="utf-8")
    assert first.notable_misses_csv_path.read_text(encoding="utf-8") == second.notable_misses_csv_path.read_text(encoding="utf-8")
    assert first.key_takeaways_json_path.read_text(encoding="utf-8") == second.key_takeaways_json_path.read_text(encoding="utf-8")


def test_public_findings_filter_to_requested_season_pair(tmp_path: Path) -> None:
    comparison_summary_path, exports_dir, case_study_dir = _build_public_inputs(tmp_path)

    artifacts = build_wr_public_findings(
        comparison_summary_path=comparison_summary_path,
        case_study_dir=case_study_dir,
        exports_dir=exports_dir,
        output_dir=tmp_path / "public",
        feature_season=2024,
        outcome_season=2025,
    )

    markdown = artifacts.findings_markdown_path.read_text(encoding="utf-8")

    assert "Nova Star" in markdown
    assert "Hidden Surge" in markdown
    assert "Prior Season One" not in markdown
    assert "Prior Season Two" not in markdown


def test_public_findings_recipe_family_comparison_extraction(tmp_path: Path) -> None:
    comparison_summary_path, exports_dir, case_study_dir = _build_public_inputs(tmp_path)

    artifacts = build_wr_public_findings(
        comparison_summary_path=comparison_summary_path,
        case_study_dir=case_study_dir,
        exports_dir=exports_dir,
        output_dir=tmp_path / "public",
        feature_season=2024,
        outcome_season=2025,
    )

    recipe_rows = list(csv.DictReader(artifacts.recipe_comparison_csv_path.open(encoding="utf-8", newline="")))

    assert list(recipe_rows[0].keys()) == PUBLIC_RECIPE_COMPARISON_COLUMNS
    assert recipe_rows[0]["recipe_family"] == "base"
    assert [row["recipe_name"] for row in recipe_rows if row["is_best_in_family"] == "true"] == [
        "balanced_conservative",
        "cohort_balanced",
        "role_balanced",
    ]
    assert [row["recipe_name"] for row in recipe_rows if row["is_best_overall"] == "true"] == ["role_balanced"]


def test_public_findings_select_notable_hits_and_misses(tmp_path: Path) -> None:
    comparison_summary_path, exports_dir, case_study_dir = _build_public_inputs(tmp_path)

    artifacts = build_wr_public_findings(
        comparison_summary_path=comparison_summary_path,
        case_study_dir=case_study_dir,
        exports_dir=exports_dir,
        output_dir=tmp_path / "public",
        feature_season=2024,
        outcome_season=2025,
    )

    notable_hits = list(csv.DictReader(artifacts.notable_hits_csv_path.open(encoding="utf-8", newline="")))
    notable_misses = list(csv.DictReader(artifacts.notable_misses_csv_path.open(encoding="utf-8", newline="")))

    assert list(notable_hits[0].keys()) == PUBLIC_NOTABLE_HIT_COLUMNS
    assert list(notable_misses[0].keys()) == PUBLIC_NOTABLE_MISS_COLUMNS
    assert [row["player_name"] for row in notable_hits] == ["Breakout Blaze", "Nova Star"]
    assert [row["miss_type"] for row in notable_misses] == ["false_negative", "false_positive"]
    assert [row["player_name"] for row in notable_misses] == ["Hidden Surge", "Volume Mirage"]


def test_public_findings_markdown_sections_are_present_and_ordered(tmp_path: Path) -> None:
    comparison_summary_path, exports_dir, case_study_dir = _build_public_inputs(tmp_path)

    artifacts = build_wr_public_findings(
        comparison_summary_path=comparison_summary_path,
        case_study_dir=case_study_dir,
        exports_dir=exports_dir,
        output_dir=tmp_path / "public",
        feature_season=2024,
        outcome_season=2025,
    )

    markdown = artifacts.findings_markdown_path.read_text(encoding="utf-8")
    headings = [
        "## Executive summary",
        "## Best overall recipe and family",
        "## Did cohort / role context help?",
        "## Notable player hits",
        "## Notable player misses",
        "## Public-safe signal takeaways",
        "## Limitations and cautions",
    ]

    positions = [markdown.index(heading) for heading in headings]
    assert positions == sorted(positions)
    assert "Best base recipe" in markdown
    assert "Best cohort-aware recipe" in markdown
    assert "Best role-aware recipe" in markdown
    assert "Cohort over base: Improved" in markdown
    assert "Role over base: Improved" in markdown
    assert "Role over cohort: Improved" in markdown


def test_public_findings_key_takeaways_json_schema(tmp_path: Path) -> None:
    comparison_summary_path, exports_dir, case_study_dir = _build_public_inputs(tmp_path)

    artifacts = build_wr_public_findings(
        comparison_summary_path=comparison_summary_path,
        case_study_dir=case_study_dir,
        exports_dir=exports_dir,
        output_dir=tmp_path / "public",
        feature_season=2024,
        outcome_season=2025,
    )

    payload = json.loads(artifacts.key_takeaways_json_path.read_text(encoding="utf-8"))

    assert list(payload.keys()) == [
        "report_name",
        "schema_version",
        "position",
        "feature_season",
        "outcome_season",
        "best_overall_recipe",
        "best_base_recipe",
        "best_cohort_recipe",
        "best_role_recipe",
        "family_improvement_checks",
        "season_pair_summary",
        "notable_selection_rule",
        "notable_hits",
        "notable_misses",
        "key_takeaways",
        "best_recipe_rule",
        "source_artifacts",
    ]
    assert payload["best_overall_recipe"]["recipe_name"] == "role_balanced"
    assert payload["best_base_recipe"]["recipe_name"] == "balanced_conservative"
    assert payload["best_cohort_recipe"]["recipe_name"] == "cohort_balanced"
    assert payload["best_role_recipe"]["recipe_name"] == "role_balanced"
    assert payload["family_improvement_checks"]["cohort_vs_base"]["status"] == "improved"
    assert payload["family_improvement_checks"]["role_vs_base"]["status"] == "improved"
    assert payload["family_improvement_checks"]["role_vs_cohort"]["status"] == "improved"
    assert payload["season_pair_summary"] == {
        "hit_count": 2,
        "false_positive_count": 1,
        "false_negative_count": 1,
    }
    assert [row["player_name"] for row in payload["notable_hits"]] == ["Breakout Blaze", "Nova Star"]
    assert [row["player_name"] for row in payload["notable_misses"]] == ["Hidden Surge", "Volume Mirage"]
    assert len(payload["key_takeaways"]) == 4


def test_public_findings_use_pending_outcome_wording_for_forward_looking_pairs(tmp_path: Path) -> None:
    comparison_summary_path, exports_dir, case_study_dir = _build_public_inputs(tmp_path, pending_outcomes=True)

    artifacts = build_wr_public_findings(
        comparison_summary_path=comparison_summary_path,
        case_study_dir=case_study_dir,
        exports_dir=exports_dir,
        output_dir=tmp_path / "public",
        feature_season=2024,
        outcome_season=2025,
    )

    markdown = artifacts.findings_markdown_path.read_text(encoding="utf-8")
    payload = json.loads(artifacts.key_takeaways_json_path.read_text(encoding="utf-8"))

    assert "forward-looking candidate board" in markdown
    assert "Outcomes pending: player-level hit/miss examples will populate once valid 2025 outcome data is complete." in markdown
    assert "The season-pair review logged 0 hits, 0 false positives, and 0 false negatives." not in markdown
    assert payload["key_takeaways"][2].startswith("Outcome-based player examples are pending")


def test_cli_parser_supports_public_findings_command() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "build-wr-public-findings",
            "--public-dir",
            "outputs/public",
            "--comparison-summary",
            "outputs/validation_reports/wr_recipe_comparison_summary.json",
            "--case-study-dir",
            "outputs/case_studies",
            "--exports-dir",
            "outputs/exports",
            "--feature-season",
            "2024",
            "--outcome-season",
            "2025",
        ]
    )

    assert args.command == "build-wr-public-findings"
    assert args.public_dir == "outputs/public"
    assert args.output_dir is None
    assert args.feature_season == 2024
    assert args.outcome_season == 2025
