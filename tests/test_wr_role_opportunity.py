from __future__ import annotations

import csv
import json
from pathlib import Path

from src.enrichment.wr_cohort_baselines import COHORT_DATASET_COLUMNS
from src.enrichment.wr_role_opportunity import (
    ROLE_DATASET_COLUMNS,
    build_wr_role_metrics,
    enrich_wr_role_dataset,
    write_wr_role_outputs,
)
from src.scoring.recipe_comparison import compare_wr_recipes
from src.scoring.recipes import RECIPES
from src.scoring.wr_signal_score import _score_candidate


def _player_season_row(
    player_id: str,
    player_name: str,
    season: int,
    *,
    avg_route_participation: float | None,
    avg_target_share: float | None,
    avg_air_yard_share: float | None,
) -> dict[str, object]:
    return {
        "player_id": player_id,
        "player_name": player_name,
        "team": "TST",
        "season": season,
        "position": "WR",
        "weeks_recorded": 3,
        "games_played": 3,
        "total_ppr": 36.0,
        "ppg": 12.0,
        "spike_week_threshold": 20.0,
        "spike_week_count": 1,
        "spike_week_rate": 0.3333,
        "dud_week_threshold": 5.0,
        "dud_week_count": 0,
        "dud_week_rate": 0.0,
        "total_targets": 24,
        "targets_per_game": 8.0,
        "total_receptions": 15,
        "receptions_per_game": 5.0,
        "total_receiving_yards": 210.0,
        "receiving_yards_per_game": 70.0,
        "total_receiving_tds": 2,
        "receiving_tds_per_game": 0.6667,
        "avg_snap_share": 0.80,
        "avg_route_participation": avg_route_participation,
        "avg_target_share": avg_target_share,
        "avg_air_yard_share": avg_air_yard_share,
    }


def _weekly_row(
    player_id: str,
    season: int,
    week: int,
    *,
    route_participation: float | None,
    target_share: float | None,
    air_yard_share: float | None,
) -> dict[str, object]:
    return {
        "player_id": player_id,
        "player_name": player_id.upper(),
        "team": "TST",
        "season": season,
        "week": week,
        "position": "WR",
        "week_is_active": True,
        "raw_games_value": 1,
        "ppr_points": 10.0,
        "targets": 8,
        "receptions": 5,
        "receiving_yards": 65.0,
        "receiving_tds": 0,
        "snap_share": 0.80,
        "route_participation": route_participation,
        "target_share": target_share,
        "air_yard_share": air_yard_share,
    }


def _cohort_validation_row(
    player_id: str,
    player_name: str,
    feature_season: int,
    *,
    feature_ppg: float,
    feature_finish: int,
) -> dict[str, object]:
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
        "feature_total_ppr": round(feature_ppg * 17, 4),
        "outcome_total_ppr": round((feature_ppg + 1.0) * 17, 4),
        "feature_ppg": feature_ppg,
        "outcome_ppg": round(feature_ppg + 1.0, 4),
        "ppg_delta_next_season": 1.0,
        "feature_finish": feature_finish,
        "outcome_finish": max(1, feature_finish - 10),
        "finish_delta_next_season": 10,
        "feature_targets_per_game": 7.5,
        "outcome_targets_per_game": 8.0,
        "feature_target_share": 0.22,
        "expected_ppg_baseline": round(feature_ppg + 1.2, 4),
        "actual_minus_expected_ppg": -0.2,
        "is_new_fantasy_starter": False,
        "breakout_reason": "top24_jump" if feature_finish > 24 else "no_breakout_trigger",
        "breakout_label_default": feature_finish > 24,
        "breakout_label_ppg_jump": False,
        "breakout_label_top24_jump": feature_finish > 24,
        "career_year": 2,
        "career_year_bucket": "yr2",
        "age_bucket": "age_unknown",
        "cohort_key": "WR|yr2|age_unknown",
        "cohort_player_count": 3,
        "expected_ppg_from_cohort": round(feature_ppg - 0.8, 4),
        "expected_finish_from_cohort": float(feature_finish + 4),
        "feature_ppg_minus_cohort_expected": 0.8,
        "outcome_ppg_minus_cohort_expected": 1.8,
        "actual_minus_cohort_expected_ppg": 1.8,
    }


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            payload = {}
            for field in fieldnames:
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


def test_build_wr_role_metrics_is_deterministic() -> None:
    player_season_rows = [
        _player_season_row(
            "wr_role_a",
            "Role A",
            2024,
            avg_route_participation=0.80,
            avg_target_share=0.24,
            avg_air_yard_share=0.30,
        )
    ]
    weekly_rows = [
        _weekly_row("wr_role_a", 2024, 1, route_participation=0.70, target_share=0.22, air_yard_share=0.28),
        _weekly_row("wr_role_a", 2024, 2, route_participation=0.80, target_share=0.24, air_yard_share=0.30),
        _weekly_row("wr_role_a", 2024, 3, route_participation=0.90, target_share=0.26, air_yard_share=0.32),
    ]

    first = build_wr_role_metrics(player_season_rows, weekly_rows)
    second = build_wr_role_metrics(player_season_rows, weekly_rows)
    metrics = first[("wr_role_a", 2024)]

    assert first == second
    assert metrics.route_participation_season_avg == 0.8
    assert metrics.target_share_season_avg == 0.24
    assert metrics.air_yard_share_season_avg == 0.3
    assert metrics.routes_consistency_index == 0.9167
    assert metrics.target_earning_index == 0.3
    assert metrics.opportunity_concentration_score == 0.479


def test_role_enrichment_uses_only_processed_feature_season_inputs() -> None:
    player_season_rows = [
        _player_season_row(
            "wr_role_a",
            "Role A",
            2024,
            avg_route_participation=0.78,
            avg_target_share=0.23,
            avg_air_yard_share=0.29,
        )
    ]
    weekly_rows = [
        _weekly_row("wr_role_a", 2024, 1, route_participation=0.75, target_share=0.21, air_yard_share=0.27),
        _weekly_row("wr_role_a", 2024, 2, route_participation=0.81, target_share=0.24, air_yard_share=0.30),
    ]
    base_validation = [_cohort_validation_row("wr_role_a", "Role A", 2024, feature_ppg=12.0, feature_finish=30)]
    leaked_validation = [{**base_validation[0], "outcome_ppg": 40.0, "breakout_label_default": False, "actual_minus_expected_ppg": 20.0}]

    base = enrich_wr_role_dataset(player_season_rows, weekly_rows, base_validation)[0]
    leaked = enrich_wr_role_dataset(player_season_rows, weekly_rows, leaked_validation)[0]

    for field in ROLE_DATASET_COLUMNS:
        if field in COHORT_DATASET_COLUMNS:
            continue
        assert base[field] == leaked[field]


def test_write_wr_role_outputs_writes_expected_artifacts(tmp_path: Path) -> None:
    processed_dir = tmp_path / "processed"
    reports_dir = tmp_path / "reports"
    player_season_rows = [
        _player_season_row("wr_a", "A", 2024, avg_route_participation=0.76, avg_target_share=0.22, avg_air_yard_share=0.27),
        _player_season_row("wr_b", "B", 2024, avg_route_participation=None, avg_target_share=None, avg_air_yard_share=None),
    ]
    weekly_rows = [
        _weekly_row("wr_a", 2024, 1, route_participation=0.74, target_share=0.21, air_yard_share=0.26),
        _weekly_row("wr_a", 2024, 2, route_participation=0.78, target_share=0.22, air_yard_share=0.27),
        _weekly_row("wr_b", 2024, 1, route_participation=None, target_share=None, air_yard_share=None),
    ]
    validation_rows = [
        _cohort_validation_row("wr_a", "A", 2024, feature_ppg=11.5, feature_finish=32),
        _cohort_validation_row("wr_b", "B", 2024, feature_ppg=10.0, feature_finish=40),
    ]
    _write_csv(processed_dir / "wr_player_seasons.csv", list(player_season_rows[0].keys()), player_season_rows)
    _write_csv(processed_dir / "wr_player_weeks.csv", list(weekly_rows[0].keys()), weekly_rows)
    _write_csv(reports_dir / "wr_validation_dataset_enriched.csv", COHORT_DATASET_COLUMNS, validation_rows)

    artifacts = write_wr_role_outputs(
        processed_dir=processed_dir,
        validation_dataset_path=reports_dir / "wr_validation_dataset_enriched.csv",
        output_dir=reports_dir,
    )

    enriched_rows = list(csv.DictReader(artifacts.enriched_dataset_path.open(encoding="utf-8", newline="")))
    summary = json.loads(artifacts.summary_path.read_text(encoding="utf-8"))
    examples = artifacts.examples_path.read_text(encoding="utf-8")

    assert artifacts.enriched_dataset_path.exists()
    assert artifacts.summary_path.exists()
    assert artifacts.examples_path.exists()
    assert list(enriched_rows[0].keys()) == ROLE_DATASET_COLUMNS
    assert summary["leakage_guardrails"]["next_season_outcomes_used"] is False
    assert summary["coverage"]["route_participation_season_avg"] == 1
    assert "# WR Role Enrichment Examples" in examples


def test_role_aware_recipe_scoring_rewards_role_strength() -> None:
    common = {
        "player_id": "wr_hi",
        "player_name": "High Role",
        "feature_season": 2024,
        "outcome_season": 2025,
        "position": "WR",
        "feature_team": "TST",
        "has_valid_outcome": True,
        "breakout_label_default": False,
        "breakout_reason": "no_breakout_trigger",
        "feature_games_played": 17,
        "feature_total_ppr": 170.0,
        "feature_ppg": 10.0,
        "feature_finish": 30,
        "feature_targets_per_game": 7.0,
        "feature_target_share": 0.20,
        "expected_ppg_baseline": 11.5,
        "cohort_player_count": 3,
        "expected_finish_from_cohort": 34.0,
        "feature_ppg_minus_cohort_expected": 0.8,
    }
    strong_role = {
        **common,
        "route_participation_season_avg": 0.86,
        "target_share_season_avg": 0.26,
        "air_yard_share_season_avg": 0.33,
        "routes_consistency_index": 0.93,
        "target_earning_index": 0.3023,
        "opportunity_concentration_score": 0.4595,
    }
    weak_role = {
        **common,
        "player_id": "wr_lo",
        "player_name": "Low Role",
        "route_participation_season_avg": 0.58,
        "target_share_season_avg": 0.13,
        "air_yard_share_season_avg": 0.11,
        "routes_consistency_index": 0.62,
        "target_earning_index": 0.2241,
        "opportunity_concentration_score": 0.301,
    }

    baseline_high = _score_candidate(strong_role, recipe=RECIPES["baseline_v1"])
    baseline_low = _score_candidate(weak_role, recipe=RECIPES["baseline_v1"])
    role_high = _score_candidate(strong_role, recipe=RECIPES["role_balanced"])
    role_low = _score_candidate(weak_role, recipe=RECIPES["role_balanced"])

    assert baseline_high["role_signal"] > baseline_low["role_signal"]
    assert baseline_high["wr_signal_score"] == baseline_low["wr_signal_score"]
    assert role_high["wr_signal_score"] > role_low["wr_signal_score"]


def test_compare_wr_recipes_reports_role_family_deltas(tmp_path: Path) -> None:
    processed_dir = tmp_path / "processed"
    reports_dir = tmp_path / "reports"
    player_season_rows = [
        _player_season_row("wr_a", "A", 2024, avg_route_participation=0.82, avg_target_share=0.24, avg_air_yard_share=0.30),
        _player_season_row("wr_b", "B", 2024, avg_route_participation=0.60, avg_target_share=0.14, avg_air_yard_share=0.12),
        _player_season_row("wr_c", "C", 2024, avg_route_participation=0.74, avg_target_share=0.20, avg_air_yard_share=0.24),
    ]
    weekly_rows = [
        _weekly_row("wr_a", 2024, 1, route_participation=0.80, target_share=0.24, air_yard_share=0.29),
        _weekly_row("wr_a", 2024, 2, route_participation=0.84, target_share=0.25, air_yard_share=0.31),
        _weekly_row("wr_b", 2024, 1, route_participation=0.58, target_share=0.14, air_yard_share=0.11),
        _weekly_row("wr_b", 2024, 2, route_participation=0.62, target_share=0.14, air_yard_share=0.13),
        _weekly_row("wr_c", 2024, 1, route_participation=0.70, target_share=0.19, air_yard_share=0.23),
        _weekly_row("wr_c", 2024, 2, route_participation=0.78, target_share=0.21, air_yard_share=0.25),
    ]
    validation_rows = [
        _cohort_validation_row("wr_a", "A", 2024, feature_ppg=12.5, feature_finish=35),
        _cohort_validation_row("wr_b", "B", 2024, feature_ppg=10.0, feature_finish=18),
        _cohort_validation_row("wr_c", "C", 2024, feature_ppg=11.2, feature_finish=28),
    ]
    _write_csv(processed_dir / "wr_player_seasons.csv", list(player_season_rows[0].keys()), player_season_rows)
    _write_csv(processed_dir / "wr_player_weeks.csv", list(weekly_rows[0].keys()), weekly_rows)
    _write_csv(reports_dir / "wr_validation_dataset_enriched.csv", COHORT_DATASET_COLUMNS, validation_rows)
    role_artifacts = write_wr_role_outputs(
        processed_dir=processed_dir,
        validation_dataset_path=reports_dir / "wr_validation_dataset_enriched.csv",
        output_dir=reports_dir,
    )

    artifacts = compare_wr_recipes(role_artifacts.enriched_dataset_path, output_dir=tmp_path / "outputs")
    summary = json.loads(artifacts.summary_path.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(artifacts.comparison_table_path.open(encoding="utf-8", newline="")))

    assert any(row["recipe_family"] == "role" for row in rows)
    assert any(row["recipe_name"] == "role_balanced" for row in rows)
    assert any(row["recipe_name"] == "role_upside" for row in rows)
    assert summary["best_role_recipe"]["recipe_name"] in {"role_balanced", "role_upside"}
    assert summary["role_vs_base_delta"] is not None
    assert summary["role_vs_cohort_delta"] is not None
