import csv
from pathlib import Path

import pytest

from src.ingestion import build_wr_tables_from_csv
from src.transforms.wr_tables import build_canonical_wr_tables
from src.validation import ValidationError, read_raw_wr_week_rows


FIXTURE_PATH = Path("tests/fixtures/wr_history_sample.csv")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_csv_ingestion_builds_expected_files(tmp_path: Path) -> None:
    output_paths = build_wr_tables_from_csv(FIXTURE_PATH, output_dir=tmp_path)

    assert set(output_paths) == {
        "wr_player_weeks",
        "wr_player_seasons",
        "wr_feature_seasons",
        "wr_outcome_seasons",
    }
    for path in output_paths.values():
        assert path.exists()

    weeks = _read_csv(output_paths["wr_player_weeks"])
    assert weeks[0]["player_id"] == "wr_alpha"
    assert weeks[-1]["player_id"] == "wr_beta"
    assert weeks[-1]["week_is_active"] == "false"
    assert weeks[-1]["snap_share"] == ""


def test_weekly_to_season_aggregation_is_correct() -> None:
    raw_rows = read_raw_wr_week_rows(FIXTURE_PATH)
    tables = build_canonical_wr_tables(raw_rows)

    alpha_2022 = next(
        row
        for row in tables["wr_player_seasons"]
        if row["player_id"] == "wr_alpha" and row["season"] == 2022
    )
    beta_2022 = next(
        row
        for row in tables["wr_player_seasons"]
        if row["player_id"] == "wr_beta" and row["season"] == 2022
    )

    assert alpha_2022["games_played"] == 2
    assert alpha_2022["total_ppr"] == 36.0
    assert alpha_2022["ppg"] == 18.0
    assert alpha_2022["spike_week_count"] == 1
    assert alpha_2022["spike_week_rate"] == 0.5
    assert alpha_2022["dud_week_count"] == 0
    assert alpha_2022["total_targets"] == 19
    assert alpha_2022["targets_per_game"] == 9.5
    assert alpha_2022["avg_snap_share"] == 0.78

    assert beta_2022["games_played"] == 1
    assert beta_2022["weeks_recorded"] == 2
    assert beta_2022["dud_week_count"] == 1
    assert beta_2022["dud_week_rate"] == 1.0
    assert beta_2022["ppg"] == 3.0
    assert beta_2022["avg_snap_share"] is None


def test_feature_outcome_split_is_timestamp_safe() -> None:
    raw_rows = read_raw_wr_week_rows(FIXTURE_PATH)
    tables = build_canonical_wr_tables(raw_rows)

    feature_row = next(
        row
        for row in tables["wr_feature_seasons"]
        if row["player_id"] == "wr_alpha" and row["season"] == 2022
    )
    outcome_row = next(
        row
        for row in tables["wr_outcome_seasons"]
        if row["player_id"] == "wr_alpha" and row["feature_season"] == 2022
    )

    assert feature_row["target_outcome_season"] == 2023
    assert feature_row["data_through_season"] == 2022
    assert not any(column.startswith("outcome_") for column in feature_row)
    assert outcome_row["outcome_season"] == 2023
    assert outcome_row["outcome_total_ppr"] == 34.0
    assert outcome_row["outcome_games_played"] == 2


def test_duplicate_raw_rows_are_rejected(tmp_path: Path) -> None:
    duplicate_csv = tmp_path / "duplicate.csv"
    duplicate_csv.write_text(
        "player_id,player_name,team,season,week,position,fantasy_points_ppr,targets,receptions,receiving_yards,receiving_tds\n"
        "wr_dup,Duplicate,DDD,2022,1,WR,10.0,5,4,50,1\n"
        "wr_dup,Duplicate,DDD,2022,1,WR,11.0,6,5,60,1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="duplicate WR weekly primary key"):
        read_raw_wr_week_rows(duplicate_csv)


def test_processed_outputs_are_deterministic(tmp_path: Path) -> None:
    output_dir_a = tmp_path / "run_a"
    output_dir_b = tmp_path / "run_b"

    paths_a = build_wr_tables_from_csv(FIXTURE_PATH, output_dir=output_dir_a)
    paths_b = build_wr_tables_from_csv(FIXTURE_PATH, output_dir=output_dir_b)

    for table_name in paths_a:
        assert paths_a[table_name].read_text(encoding="utf-8") == paths_b[table_name].read_text(
            encoding="utf-8"
        )


def test_non_wr_rows_are_rejected(tmp_path: Path) -> None:
    invalid_csv = tmp_path / "non_wr.csv"
    invalid_csv.write_text(
        "player_id,player_name,team,season,week,position,fantasy_points_ppr,targets,receptions,receiving_yards,receiving_tds\n"
        "rb_test,Runner,RRR,2022,1,RB,10.0,5,4,50,1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="only WR rows are supported"):
        read_raw_wr_week_rows(invalid_csv)
