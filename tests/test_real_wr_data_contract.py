import csv
import importlib.util
from pathlib import Path

from src.validation import read_raw_wr_week_rows
from src.validation.wr_tables import WR_RAW_REQUIRED_COLUMNS

FIXTURE_PATH = Path("tests/fixtures/wr_history_sample.csv")
SCRIPT_PATH = Path("scripts/build_real_wr_data.py")


def _load_script_module():
    spec = importlib.util.spec_from_file_location("build_real_wr_data", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_builder_declares_contract_columns_in_expected_order() -> None:
    module = _load_script_module()

    assert module.REQUIRED_COLUMNS == WR_RAW_REQUIRED_COLUMNS
    assert module.OUTPUT_COLUMNS == [
        "player_id",
        "player_name",
        "team",
        "season",
        "week",
        "position",
        "fantasy_points_ppr",
        "targets",
        "receptions",
        "receiving_yards",
        "receiving_tds",
        "games",
        "snap_share",
        "route_participation",
        "target_share",
        "air_yard_share",
    ]
    assert module.SEASONS == [2020, 2021, 2022, 2023, 2024]


def test_fixture_matches_required_column_presence() -> None:
    with FIXTURE_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        for column in WR_RAW_REQUIRED_COLUMNS:
            assert column in reader.fieldnames


def test_raw_fixture_rows_respect_basic_numeric_invariants() -> None:
    rows = read_raw_wr_week_rows(FIXTURE_PATH)

    assert rows
    assert all(row["position"] == "WR" for row in rows)
    assert all(row["targets"] >= row["receptions"] for row in rows)
    assert all(row["targets"] >= 0 for row in rows)
    assert all(row["receptions"] >= 0 for row in rows)
    assert all(row["receiving_tds"] >= 0 for row in rows)


def test_raw_fixture_rows_are_sorted_by_player_season_week_after_validation() -> None:
    rows = read_raw_wr_week_rows(FIXTURE_PATH)
    assert rows == sorted(rows, key=lambda row: (row["player_id"], row["season"], row["week"]))
