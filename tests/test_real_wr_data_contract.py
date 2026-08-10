import csv
import importlib.util
from pathlib import Path

import pytest

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
    assert module.DEFAULT_SEASONS == [2020, 2021, 2022, 2023, 2024]
    assert module.SEASONS == module.DEFAULT_SEASONS


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

def test_core_dependency_metadata_excludes_legacy_builder_stack() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    core_metadata, optional_metadata = pyproject.split(
        "[project.optional-dependencies]",
        maxsplit=1,
    )

    assert "nfl_data_py" not in core_metadata
    assert "pandas" not in core_metadata
    assert "legacy-local-builder" in optional_metadata
    assert '"nfl_data_py==0.3.3"' in optional_metadata
    assert '"pandas>=1.5,<2.0"' in optional_metadata


def test_legacy_builder_rejects_unsupported_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_script_module()
    monkeypatch.setattr(module.sys, "version_info", (3, 12, 0))

    with pytest.raises(
        module.LegacyLocalBuilderUnavailable,
        match="Python 3.10 or 3.11",
    ):
        module._import_dependencies()
