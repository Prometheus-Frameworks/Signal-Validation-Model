from __future__ import annotations

import csv
import json
from pathlib import Path

from src.enrichment.wr_cohort_baselines import (
    COHORT_DATASET_COLUMNS,
    AGE_BUCKET_DEFINITIONS,
    CAREER_YEAR_BUCKET_DEFINITIONS,
    assign_wr_cohorts,
    enrich_wr_validation_dataset,
    write_wr_cohort_outputs,
)
from src.labels.wr_breakouts import WR_VALIDATION_DATASET_COLUMNS
from src.scoring.recipe_comparison import compare_wr_recipes


def _feature_row(player_id: str, player_name: str, season: int, ppg: float) -> dict[str, object]:
    return {
        "player_id": player_id,
        "player_name": player_name,
        "season": season,
        "target_outcome_season": season + 1,
        "data_through_season": season,
        "position": "WR",
        "team": "TST",
        "games_played": 17,
        "weeks_recorded": 17,
        "total_ppr": round(ppg * 17, 4),
        "ppg": ppg,
        "spike_week_rate": 0.1,
        "dud_week_rate": 0.1,
        "total_targets": 120,
        "targets_per_game": 7.0,
        "total_receptions": 80,
        "receptions_per_game": 4.7,
        "total_receiving_yards": 1000,
        "receiving_yards_per_game": 58.8,
        "total_receiving_tds": 6,
        "receiving_tds_per_game": 0.35,
        "avg_snap_share": 0.75,
        "avg_route_participation": 0.82,
        "avg_target_share": 0.2,
        "avg_air_yard_share": 0.25,
    }


def _validation_row(
    player_id: str,
    player_name: str,
    feature_season: int,
    feature_ppg: float,
    outcome_ppg: float | None,
    feature_finish: int,
    outcome_finish: int | None,
) -> dict[str, object]:
    return {
        "player_id": player_id,
        "player_name": player_name,
        "feature_season": feature_season,
        "outcome_season": feature_season + 1,
        "position": "WR",
        "feature_team": "TST",
        "outcome_team": "TST" if outcome_ppg is not None else None,
        "has_valid_outcome": outcome_ppg is not None,
        "feature_games_played": 17,
        "outcome_games_played": 17 if outcome_ppg is not None else None,
        "feature_total_ppr": round(feature_ppg * 17, 4),
        "outcome_total_ppr": round(outcome_ppg * 17, 4) if outcome_ppg is not None else None,
        "feature_ppg": feature_ppg,
        "outcome_ppg": outcome_ppg,
        "ppg_delta_next_season": round(outcome_ppg - feature_ppg, 4) if outcome_ppg is not None else None,
        "feature_finish": feature_finish,
        "outcome_finish": outcome_finish,
        "finish_delta_next_season": feature_finish - outcome_finish if outcome_finish is not None else None,
        "feature_targets_per_game": 7.0,
        "outcome_targets_per_game": 7.5 if outcome_ppg is not None else None,
        "feature_target_share": 0.20,
        "expected_ppg_baseline": round(feature_ppg + 0.8, 4),
        "actual_minus_expected_ppg": round(outcome_ppg - (feature_ppg + 0.8), 4) if outcome_ppg is not None else None,
        "is_new_fantasy_starter": False,
        "breakout_reason": "top24_jump" if outcome_finish is not None and outcome_finish <= 24 and feature_finish > 24 else "no_breakout_trigger",
        "breakout_label_default": outcome_finish is not None and outcome_finish <= 24 and feature_finish > 24,
        "breakout_label_ppg_jump": outcome_ppg is not None and outcome_ppg - feature_ppg > 3.0,
        "breakout_label_top24_jump": outcome_finish is not None and outcome_finish <= 24 and feature_finish > 24,
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


def test_assign_wr_cohorts_uses_deterministic_career_year_buckets() -> None:
    assignments = assign_wr_cohorts(
        [
            _feature_row("wr_a", "A", 2022, 8.0),
            _feature_row("wr_a", "A", 2023, 9.0),
            _feature_row("wr_a", "A", 2024, 10.0),
            _feature_row("wr_a", "A", 2025, 11.0),
        ]
    )

    assert assignments[("wr_a", 2022)].career_year == 1
    assert assignments[("wr_a", 2022)].career_year_bucket == "yr1"
    assert assignments[("wr_a", 2023)].career_year_bucket == "yr2"
    assert assignments[("wr_a", 2024)].career_year_bucket == "yr3"
    assert assignments[("wr_a", 2025)].career_year_bucket == "yr4_plus"
    assert assignments[("wr_a", 2023)].age_bucket == "age_unknown"
    assert "yr1" in CAREER_YEAR_BUCKET_DEFINITIONS
    assert "age_unknown" in AGE_BUCKET_DEFINITIONS


def test_enrichment_uses_only_prior_feature_seasons_for_expectations() -> None:
    feature_rows = [
        _feature_row("wr_a", "A", 2022, 8.0),
        _feature_row("wr_a", "A", 2023, 9.0),
        _feature_row("wr_b", "B", 2022, 7.0),
        _feature_row("wr_b", "B", 2023, 8.0),
        _feature_row("wr_c", "C", 2024, 12.0),
    ]
    validation_rows = [
        _validation_row("wr_a", "A", 2022, 8.0, 10.0, 45, 30),
        _validation_row("wr_a", "A", 2023, 9.0, 11.0, 40, 24),
        _validation_row("wr_b", "B", 2022, 7.0, 8.0, 55, 40),
        _validation_row("wr_b", "B", 2023, 8.0, 9.0, 50, 38),
        _validation_row("wr_c", "C", 2024, 12.0, 14.0, 35, 18),
    ]

    enriched = enrich_wr_validation_dataset(feature_rows=feature_rows, validation_rows=validation_rows)
    row_2024 = next(row for row in enriched if row["player_id"] == "wr_c")
    row_2022 = next(row for row in enriched if row["player_id"] == "wr_a" and row["feature_season"] == 2022)

    assert row_2022["cohort_player_count"] == 0
    assert row_2022["expected_ppg_from_cohort"] is None
    assert row_2024["career_year_bucket"] == "yr1"
    assert row_2024["cohort_player_count"] == 2
    assert row_2024["expected_ppg_from_cohort"] == 9.0
    assert row_2024["expected_finish_from_cohort"] == 35.0
    assert row_2024["feature_ppg_minus_cohort_expected"] == 3.0
    assert row_2024["outcome_ppg_minus_cohort_expected"] == 5.0
    assert row_2024["actual_minus_cohort_expected_ppg"] == 5.0


def test_write_wr_cohort_outputs_writes_enriched_dataset_and_summary(tmp_path: Path) -> None:
    processed_dir = tmp_path / "processed"
    reports_dir = tmp_path / "reports"
    feature_rows = [
        _feature_row("wr_a", "A", 2022, 8.0),
        _feature_row("wr_a", "A", 2023, 9.0),
        _feature_row("wr_b", "B", 2022, 7.0),
        _feature_row("wr_b", "B", 2023, 8.0),
        _feature_row("wr_c", "C", 2024, 12.0),
    ]
    validation_rows = [
        _validation_row("wr_a", "A", 2022, 8.0, 10.0, 45, 30),
        _validation_row("wr_a", "A", 2023, 9.0, 11.0, 40, 24),
        _validation_row("wr_b", "B", 2022, 7.0, 8.0, 55, 40),
        _validation_row("wr_b", "B", 2023, 8.0, 9.0, 50, 38),
        _validation_row("wr_c", "C", 2024, 12.0, 14.0, 35, 18),
    ]
    _write_csv(processed_dir / "wr_feature_seasons.csv", list(feature_rows[0].keys()), feature_rows)
    _write_csv(reports_dir / "wr_validation_dataset.csv", WR_VALIDATION_DATASET_COLUMNS, validation_rows)

    artifacts = write_wr_cohort_outputs(
        processed_dir=processed_dir,
        validation_dataset_path=reports_dir / "wr_validation_dataset.csv",
        output_dir=reports_dir,
    )

    assert artifacts.enriched_dataset_path.exists()
    assert artifacts.summary_path.exists()
    assert artifacts.examples_path.exists()
    enriched_rows = list(csv.DictReader(artifacts.enriched_dataset_path.open(encoding="utf-8", newline="")))
    summary = json.loads(artifacts.summary_path.read_text(encoding="utf-8"))
    examples = artifacts.examples_path.read_text(encoding="utf-8")

    assert list(enriched_rows[0].keys()) == COHORT_DATASET_COLUMNS
    assert "bucket_definitions" in summary
    assert summary["leakage_guardrails"]["historical_rows_only"] is True
    assert "# WR Cohort Baseline Examples" in examples


def test_compare_wr_recipes_supports_cohort_aware_variants(tmp_path: Path) -> None:
    processed_dir = tmp_path / "processed"
    reports_dir = tmp_path / "reports"
    feature_rows = [
        _feature_row("wr_a", "A", 2022, 8.0),
        _feature_row("wr_a", "A", 2023, 9.0),
        _feature_row("wr_b", "B", 2022, 7.0),
        _feature_row("wr_b", "B", 2023, 8.0),
        _feature_row("wr_c", "C", 2024, 12.0),
        _feature_row("wr_d", "D", 2024, 11.5),
    ]
    validation_rows = [
        _validation_row("wr_a", "A", 2022, 8.0, 10.0, 45, 30),
        _validation_row("wr_a", "A", 2023, 9.0, 11.0, 40, 24),
        _validation_row("wr_b", "B", 2022, 7.0, 8.0, 55, 40),
        _validation_row("wr_b", "B", 2023, 8.0, 9.0, 50, 38),
        _validation_row("wr_c", "C", 2024, 12.0, 14.0, 35, 18),
        _validation_row("wr_d", "D", 2024, 11.5, 12.5, 36, 28),
    ]
    _write_csv(processed_dir / "wr_feature_seasons.csv", list(feature_rows[0].keys()), feature_rows)
    _write_csv(reports_dir / "wr_validation_dataset.csv", WR_VALIDATION_DATASET_COLUMNS, validation_rows)
    enriched_artifacts = write_wr_cohort_outputs(
        processed_dir=processed_dir,
        validation_dataset_path=reports_dir / "wr_validation_dataset.csv",
        output_dir=reports_dir,
    )

    artifacts = compare_wr_recipes(enriched_artifacts.enriched_dataset_path, output_dir=tmp_path / "outputs")
    summary = json.loads(artifacts.summary_path.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(artifacts.comparison_table_path.open(encoding="utf-8", newline="")))

    assert any(row["recipe_family"] == "cohort" for row in rows)
    assert any(row["recipe_name"] == "cohort_balanced" for row in rows)
    assert any(row["recipe_name"] == "cohort_upside" for row in rows)
    assert summary["best_base_recipe"]["metrics"]["precision_at_20"] is not None
    assert summary["best_cohort_recipe"]["metrics"]["precision_at_20"] is not None
    assert summary["cohort_vs_base_delta"] is not None
