from __future__ import annotations

import csv
import json
from pathlib import Path

from src.ingestion import build_wr_tables_from_csv
from src.labels.wr_breakouts import (
    EXPECTED_PPG_BASELINE_WEIGHTS,
    EXPECTED_PPG_BEAT_THRESHOLD,
    PPG_JUMP_THRESHOLD,
    build_label_examples_markdown,
    build_label_summary,
    build_wr_validation_dataset,
    write_wr_label_outputs,
)
from src.transforms.wr_tables import build_canonical_wr_tables
from src.validation import read_raw_wr_week_rows

FIXTURE_PATH = Path("tests/fixtures/wr_history_sample.csv")


def _fixture_feature_and_outcome_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    tables = build_canonical_wr_tables(read_raw_wr_week_rows(FIXTURE_PATH))
    return tables["wr_feature_seasons"], tables["wr_outcome_seasons"]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _filler_feature_rows(count: int, season: int, ppg: float) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(count):
        rows.append(
            {
                "player_id": f"wr_fill_{season}_{index:02d}",
                "player_name": f"Fill {index}",
                "season": season,
                "target_outcome_season": season + 1,
                "position": "WR",
                "team": "FIL",
                "games_played": 17,
                "total_ppr": round(ppg * 17, 4),
                "ppg": ppg,
                "targets_per_game": 8.0,
                "avg_target_share": 0.22,
            }
        )
    return rows


def _filler_outcome_rows(count: int, feature_season: int, ppg: float) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(count):
        rows.append(
            {
                "player_id": f"wr_fill_{feature_season}_{index:02d}",
                "player_name": f"Fill {index}",
                "feature_season": feature_season,
                "outcome_season": feature_season + 1,
                "position": "WR",
                "team": "FIL",
                "outcome_games_played": 17,
                "outcome_total_ppr": round(ppg * 17, 4),
                "outcome_ppg": ppg,
                "outcome_targets_per_game": 8.0,
            }
        )
    return rows


def test_validation_dataset_joins_feature_and_outcome_rows() -> None:
    feature_rows, outcome_rows = _fixture_feature_and_outcome_rows()

    dataset = build_wr_validation_dataset(feature_rows, outcome_rows)

    alpha_2022 = next(
        row
        for row in dataset
        if row["player_id"] == "wr_alpha" and row["feature_season"] == 2022
    )
    beta_2022 = next(
        row
        for row in dataset
        if row["player_id"] == "wr_beta" and row["feature_season"] == 2022
    )

    assert alpha_2022["outcome_season"] == 2023
    assert alpha_2022["has_valid_outcome"] is True
    assert alpha_2022["feature_ppg"] == 18.0
    assert alpha_2022["outcome_ppg"] == 17.0
    assert alpha_2022["ppg_delta_next_season"] == -1.0
    assert alpha_2022["feature_finish"] == 1
    assert alpha_2022["outcome_finish"] == 1

    assert beta_2022["outcome_season"] == 2023
    assert beta_2022["has_valid_outcome"] is False
    assert beta_2022["outcome_ppg"] is None
    assert beta_2022["breakout_reason"] == "missing_outcome"


def test_default_label_and_reason_assignment_are_deterministic() -> None:
    feature_rows = [
        {
            "player_id": "wr_gamma",
            "player_name": "Gamma",
            "season": 2023,
            "target_outcome_season": 2024,
            "position": "WR",
            "team": "GAM",
            "games_played": 17,
            "total_ppr": 136.0,
            "ppg": 8.0,
            "targets_per_game": 6.0,
            "avg_target_share": 0.18,
        },
        {
            "player_id": "wr_delta",
            "player_name": "Delta",
            "season": 2023,
            "target_outcome_season": 2024,
            "position": "WR",
            "team": "DEL",
            "games_played": 17,
            "total_ppr": 255.0,
            "ppg": 15.0,
            "targets_per_game": 8.0,
            "avg_target_share": 0.24,
        },
        {
            "player_id": "wr_epsilon",
            "player_name": "Epsilon",
            "season": 2023,
            "target_outcome_season": 2024,
            "position": "WR",
            "team": "EPS",
            "games_played": 17,
            "total_ppr": 170.0,
            "ppg": 10.0,
            "targets_per_game": 7.0,
            "avg_target_share": 0.20,
        },
    ]
    feature_rows.extend(_filler_feature_rows(count=24, season=2023, ppg=11.0))

    outcome_rows = [
        {
            "player_id": "wr_gamma",
            "player_name": "Gamma",
            "feature_season": 2023,
            "outcome_season": 2024,
            "position": "WR",
            "team": "GAM",
            "outcome_games_played": 17,
            "outcome_total_ppr": 221.0,
            "outcome_ppg": 13.0,
            "outcome_targets_per_game": 8.5,
        },
        {
            "player_id": "wr_delta",
            "player_name": "Delta",
            "feature_season": 2023,
            "outcome_season": 2024,
            "position": "WR",
            "team": "DEL",
            "outcome_games_played": 17,
            "outcome_total_ppr": 255.0,
            "outcome_ppg": 15.0,
            "outcome_targets_per_game": 8.0,
        },
        {
            "player_id": "wr_epsilon",
            "player_name": "Epsilon",
            "feature_season": 2023,
            "outcome_season": 2024,
            "position": "WR",
            "team": "EPS",
            "outcome_games_played": 17,
            "outcome_total_ppr": 257.55,
            "outcome_ppg": 15.15,
            "outcome_targets_per_game": 8.0,
        },
    ]
    outcome_rows.extend(_filler_outcome_rows(count=23, feature_season=2023, ppg=12.0))

    dataset = build_wr_validation_dataset(feature_rows, outcome_rows)

    gamma = next(row for row in dataset if row["player_id"] == "wr_gamma")
    delta = next(row for row in dataset if row["player_id"] == "wr_delta")
    epsilon = next(row for row in dataset if row["player_id"] == "wr_epsilon")

    assert gamma["breakout_label_default"] is True
    assert gamma["breakout_label_ppg_jump"] is True
    assert gamma["breakout_label_top24_jump"] is True
    assert gamma["is_new_fantasy_starter"] is True
    assert gamma["breakout_reason"] == "top24_jump"

    assert delta["breakout_label_default"] is False
    assert delta["breakout_reason"] == "no_breakout_trigger"

    expected_baseline = round(
        10.0 * EXPECTED_PPG_BASELINE_WEIGHTS["feature_ppg"]
        + 7.0 * EXPECTED_PPG_BASELINE_WEIGHTS["targets_per_game"]
        + 0.20 * EXPECTED_PPG_BASELINE_WEIGHTS["target_share"],
        4,
    )
    assert epsilon["expected_ppg_baseline"] == expected_baseline
    assert epsilon["actual_minus_expected_ppg"] == round(15.15 - expected_baseline, 4)
    assert epsilon["breakout_label_default"] is True
    assert epsilon["breakout_label_ppg_jump"] is True


def test_threshold_ties_do_not_trigger_ppg_or_baseline_breakout() -> None:
    feature_rows = [
        {
            "player_id": "wr_edge_a",
            "player_name": "Edge A",
            "season": 2023,
            "target_outcome_season": 2024,
            "position": "WR",
            "team": "EDA",
            "games_played": 17,
            "total_ppr": 170.0,
            "ppg": 10.0,
            "targets_per_game": 7.0,
            "avg_target_share": 0.20,
        },
        {
            "player_id": "wr_edge_b",
            "player_name": "Edge B",
            "season": 2023,
            "target_outcome_season": 2024,
            "position": "WR",
            "team": "EDB",
            "games_played": 17,
            "total_ppr": 170.0,
            "ppg": 10.0,
            "targets_per_game": 7.0,
            "avg_target_share": 0.20,
        },
        {
            "player_id": "wr_edge_c",
            "player_name": "Edge C",
            "season": 2023,
            "target_outcome_season": 2024,
            "position": "WR",
            "team": "EDC",
            "games_played": 17,
            "total_ppr": 169.0,
            "ppg": 9.9412,
            "targets_per_game": 6.9,
            "avg_target_share": 0.19,
        },
    ]
    baseline = round(
        10.0 * EXPECTED_PPG_BASELINE_WEIGHTS["feature_ppg"]
        + 7.0 * EXPECTED_PPG_BASELINE_WEIGHTS["targets_per_game"]
        + 0.20 * EXPECTED_PPG_BASELINE_WEIGHTS["target_share"],
        4,
    )
    feature_rows.extend(_filler_feature_rows(count=24, season=2023, ppg=14.0))

    outcome_rows = [
        {
            "player_id": "wr_edge_a",
            "player_name": "Edge A",
            "feature_season": 2023,
            "outcome_season": 2024,
            "position": "WR",
            "team": "EDA",
            "outcome_games_played": 17,
            "outcome_total_ppr": 221.0,
            "outcome_ppg": 10.0 + PPG_JUMP_THRESHOLD,
            "outcome_targets_per_game": 8.0,
        },
        {
            "player_id": "wr_edge_b",
            "player_name": "Edge B",
            "feature_season": 2023,
            "outcome_season": 2024,
            "position": "WR",
            "team": "EDB",
            "outcome_games_played": 17,
            "outcome_total_ppr": (baseline + EXPECTED_PPG_BEAT_THRESHOLD) * 17,
            "outcome_ppg": baseline + EXPECTED_PPG_BEAT_THRESHOLD,
            "outcome_targets_per_game": 8.0,
        },
        {
            "player_id": "wr_edge_c",
            "player_name": "Edge C",
            "feature_season": 2023,
            "outcome_season": 2024,
            "position": "WR",
            "team": "EDC",
            "outcome_games_played": 17,
            "outcome_total_ppr": 160.0,
            "outcome_ppg": 9.4118,
            "outcome_targets_per_game": 6.0,
        },
    ]
    outcome_rows.extend(_filler_outcome_rows(count=24, feature_season=2023, ppg=14.0))

    dataset = build_wr_validation_dataset(feature_rows, outcome_rows)
    edge_a = next(row for row in dataset if row["player_id"] == "wr_edge_a")
    edge_b = next(row for row in dataset if row["player_id"] == "wr_edge_b")

    assert edge_a["ppg_delta_next_season"] == PPG_JUMP_THRESHOLD
    assert edge_a["breakout_label_ppg_jump"] is False

    assert edge_b["actual_minus_expected_ppg"] == EXPECTED_PPG_BEAT_THRESHOLD
    assert edge_b["breakout_label_default"] is False


def test_finish_ties_are_broken_deterministically_by_player_id() -> None:
    feature_rows = [
        {
            "player_id": "wr_a",
            "player_name": "A",
            "season": 2023,
            "target_outcome_season": 2024,
            "position": "WR",
            "team": "AAA",
            "games_played": 17,
            "total_ppr": 170.0,
            "ppg": 10.0,
            "targets_per_game": 7.0,
            "avg_target_share": 0.20,
        },
        {
            "player_id": "wr_b",
            "player_name": "B",
            "season": 2023,
            "target_outcome_season": 2024,
            "position": "WR",
            "team": "BBB",
            "games_played": 17,
            "total_ppr": 170.0,
            "ppg": 10.0,
            "targets_per_game": 7.0,
            "avg_target_share": 0.20,
        },
    ]
    outcome_rows = [
        {
            "player_id": "wr_a",
            "player_name": "A",
            "feature_season": 2023,
            "outcome_season": 2024,
            "position": "WR",
            "team": "AAA",
            "outcome_games_played": 17,
            "outcome_total_ppr": 170.0,
            "outcome_ppg": 10.0,
            "outcome_targets_per_game": 7.0,
        },
        {
            "player_id": "wr_b",
            "player_name": "B",
            "feature_season": 2023,
            "outcome_season": 2024,
            "position": "WR",
            "team": "BBB",
            "outcome_games_played": 17,
            "outcome_total_ppr": 170.0,
            "outcome_ppg": 10.0,
            "outcome_targets_per_game": 7.0,
        },
    ]

    dataset = build_wr_validation_dataset(feature_rows, outcome_rows)
    wr_a = next(row for row in dataset if row["player_id"] == "wr_a")
    wr_b = next(row for row in dataset if row["player_id"] == "wr_b")

    assert wr_a["feature_finish"] == 1
    assert wr_b["feature_finish"] == 2
    assert wr_a["outcome_finish"] == 1
    assert wr_b["outcome_finish"] == 2


def test_label_outputs_are_deterministic_and_include_summary_and_examples(tmp_path: Path) -> None:
    processed_dir_a = tmp_path / "processed_a"
    processed_dir_b = tmp_path / "processed_b"
    build_wr_tables_from_csv(FIXTURE_PATH, output_dir=processed_dir_a)
    build_wr_tables_from_csv(FIXTURE_PATH, output_dir=processed_dir_b)

    output_dir_a = tmp_path / "reports_a"
    output_dir_b = tmp_path / "reports_b"

    paths_a = write_wr_label_outputs(processed_dir_a, output_dir_a)
    paths_b = write_wr_label_outputs(processed_dir_b, output_dir_b)

    for key in paths_a:
        assert paths_a[key].read_text(encoding="utf-8") == paths_b[key].read_text(encoding="utf-8")

    summary = json.loads(paths_a["wr_label_summary"].read_text(encoding="utf-8"))
    assert summary["row_count"] == 3
    assert summary["valid_outcome_count"] == 1
    assert summary["missing_outcome_count"] == 2
    assert summary["breakout_reason_counts"]["missing_outcome"] == 2

    labels = _read_csv(paths_a["wr_breakout_labels"])
    assert labels[0]["player_id"] == "wr_alpha"
    assert labels[1]["breakout_reason"] == "missing_outcome"

    examples = paths_a["wr_label_examples"].read_text(encoding="utf-8")
    assert "# WR Breakout Label Examples" in examples
    assert "## Missing-outcome rows" in examples


def test_summary_builder_matches_markdown_examples_shape() -> None:
    feature_rows, outcome_rows = _fixture_feature_and_outcome_rows()
    dataset = build_wr_validation_dataset(feature_rows, outcome_rows)

    summary = build_label_summary(dataset)
    examples = build_label_examples_markdown(dataset)

    assert summary["label_counts"]["breakout_label_default"] == 0
    assert summary["breakout_reason_counts"]["missing_outcome"] == 2
    assert "wr_beta" in examples
