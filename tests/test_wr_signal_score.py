from __future__ import annotations

import csv
import json
from pathlib import Path

from src.labels.wr_breakouts import WR_VALIDATION_DATASET_COLUMNS, write_wr_label_outputs
from src.scoring.wr_signal_score import (
    COMPONENT_WEIGHTS,
    SCORING_VERSION,
    _score_candidate,
    build_scored_candidates,
    build_validation_summary,
    score_wr_candidates,
)
from src.ingestion import build_wr_tables_from_csv

FIXTURE_PATH = Path("tests/fixtures/wr_history_sample.csv")


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
        writer = csv.DictWriter(handle, fieldnames=WR_VALIDATION_DATASET_COLUMNS)
        writer.writeheader()
        for row in rows:
            payload = {}
            for field in WR_VALIDATION_DATASET_COLUMNS:
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


def test_wr_signal_score_is_deterministic_for_same_input() -> None:
    row = _base_dataset_row("wr_same", "Same", 2023)

    first = _score_candidate(row)
    second = _score_candidate(row)

    assert first == second


def test_wr_signal_score_ignores_outcome_columns() -> None:
    base = _base_dataset_row("wr_leak", "Leak Test", 2023)
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

    base_score = _score_candidate(base)
    leaked_score = _score_candidate(leaked)

    assert base_score["wr_signal_score"] == leaked_score["wr_signal_score"]
    assert base_score["usage_signal"] == leaked_score["usage_signal"]
    assert base_score["development_signal"] == leaked_score["development_signal"]


def test_wr_signal_rankings_break_ties_by_player_id() -> None:
    rows = [
        _base_dataset_row("wr_b", "B", 2023),
        _base_dataset_row("wr_a", "A", 2023),
    ]

    ranked = build_scored_candidates(rows)

    assert [row.player_id for row in ranked] == ["wr_a", "wr_b"]
    assert [row.rank for row in ranked] == [1, 2]


def test_validation_summary_metrics_match_fixture_ranks() -> None:
    rows: list[dict[str, object]] = []
    breakout_ranks = {2, 5, 12, 31}
    for rank in range(1, 36):
        row = _base_dataset_row(f"wr_{rank:02d}", f"Player {rank:02d}", 2023)
        row["feature_targets_per_game"] = round(9.5 - rank * 0.12, 4)
        row["feature_target_share"] = round(0.29 - rank * 0.003, 4)
        row["feature_ppg"] = round(15.5 - rank * 0.22, 4)
        row["feature_total_ppr"] = round(row["feature_ppg"] * 17, 4)
        row["feature_finish"] = rank
        row["expected_ppg_baseline"] = round(row["feature_ppg"] + 0.2, 4)
        row["breakout_label_default"] = rank in breakout_ranks
        row["breakout_reason"] = "top24_jump" if rank in breakout_ranks else "no_breakout_trigger"
        rows.append(row)

    summary = build_validation_summary(build_scored_candidates(rows))

    assert summary["candidate_count"] == 35
    assert summary["breakout_count"] == 4
    assert summary["precision_at_10"] == 0.2
    assert summary["precision_at_20"] == 0.15
    assert summary["precision_at_30"] == 0.1
    assert summary["recall_at_10"] == 0.5
    assert summary["recall_at_20"] == 0.75
    assert summary["recall_at_30"] == 0.75
    assert summary["average_rank_of_actual_breakouts"] == 12.5
    assert summary["median_rank_of_actual_breakouts"] == 8.5
    assert summary["false_positives_in_top_20"] == 17
    assert summary["false_negatives_outside_top_30"] == 1


def test_component_scores_output_uses_explicit_weighted_sum() -> None:
    row = _base_dataset_row("wr_components", "Components", 2023)
    scored = _score_candidate(row)

    recomputed = round(
        scored["usage_signal"] * COMPONENT_WEIGHTS["usage_signal"]
        + scored["efficiency_signal"] * COMPONENT_WEIGHTS["efficiency_signal"]
        + scored["development_signal"] * COMPONENT_WEIGHTS["development_signal"]
        + scored["stability_signal"] * COMPONENT_WEIGHTS["stability_signal"]
        + scored["cohort_signal"] * COMPONENT_WEIGHTS["cohort_signal"]
        + scored["role_signal"] * COMPONENT_WEIGHTS["role_signal"]
        + scored["penalty_signal"] * COMPONENT_WEIGHTS["penalty_signal"],
        4,
    )

    assert scored["wr_signal_score"] == recomputed


def test_score_command_writes_reports_and_component_outputs(tmp_path: Path) -> None:
    rows: list[dict[str, object]] = []
    for rank in range(1, 34):
        row = _base_dataset_row(f"wr_out_{rank:02d}", f"Output {rank:02d}", 2024)
        row["feature_targets_per_game"] = round(9.7 - rank * 0.15, 4)
        row["feature_target_share"] = round(0.30 - rank * 0.0035, 4)
        row["feature_ppg"] = round(15.8 - rank * 0.24, 4)
        row["feature_total_ppr"] = round(row["feature_ppg"] * 17, 4)
        row["feature_finish"] = rank
        row["expected_ppg_baseline"] = round(row["feature_ppg"] + (1.0 if rank in {3, 32} else 0.2), 4)
        row["breakout_label_default"] = rank in {3, 32}
        row["breakout_reason"] = "top24_jump" if rank in {3, 32} else "no_breakout_trigger"
        rows.append(row)

    dataset_path = tmp_path / "validation" / "wr_validation_dataset.csv"
    _write_validation_dataset(dataset_path, rows)

    artifacts = score_wr_candidates(dataset_path, output_dir=tmp_path / "outputs")

    summary = json.loads(artifacts.validation_summary_path.read_text(encoding="utf-8"))
    rankings = list(csv.DictReader(artifacts.candidate_rankings_path.open(encoding="utf-8", newline="")))
    components = list(csv.DictReader(artifacts.component_scores_path.open(encoding="utf-8", newline="")))
    false_positives = artifacts.false_positives_path.read_text(encoding="utf-8")
    false_negatives = artifacts.false_negatives_path.read_text(encoding="utf-8")
    top_candidates = artifacts.top_candidates_path.read_text(encoding="utf-8")

    assert artifacts.candidate_rankings_path.exists()
    assert artifacts.component_scores_path.exists()
    assert artifacts.validation_summary_path.exists()
    assert artifacts.top_candidates_path.exists()
    assert artifacts.false_positives_path.exists()
    assert artifacts.false_negatives_path.exists()

    assert summary["scoring_version"] == SCORING_VERSION
    assert summary["false_negatives_outside_top_30"] == 1
    assert rankings[0]["rank"] == "1"
    assert "usage_signal" in components[0]
    assert components[0]["scoring_version"] == SCORING_VERSION
    assert "# WR Top Candidates" in top_candidates
    assert "# WR False Positives" in false_positives
    assert "wr_out_01" in false_positives
    assert "# WR False Negatives" in false_negatives
    assert "wr_out_32" in false_negatives


def test_pr3_fixture_dataset_can_be_scored_end_to_end(tmp_path: Path) -> None:
    processed_dir = tmp_path / "processed"
    reports_dir = tmp_path / "reports"
    build_wr_tables_from_csv(FIXTURE_PATH, output_dir=processed_dir)
    label_outputs = write_wr_label_outputs(processed_dir, reports_dir)

    artifacts = score_wr_candidates(label_outputs["wr_validation_dataset"], output_dir=tmp_path / "outputs")

    assert artifacts.validation_summary_path.exists()
    summary = json.loads(artifacts.validation_summary_path.read_text(encoding="utf-8"))
    assert summary["candidate_count"] == 3
