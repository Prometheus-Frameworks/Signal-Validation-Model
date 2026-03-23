import csv
import json
from pathlib import Path

import pytest

from src.ingestion.real_wr_history import LOCAL_BUILDER_SOURCE_TYPE, build_real_wr_history_with_preferred_source
from src.ingestion.tiber_data_adapter import (
    TIBER_DATA_EXPORT_SOURCE_TYPE,
    TiberDataSourceUnavailable,
    build_wr_history_from_tiber_data,
)
from src.validation import ValidationError

FIXTURE_PATH = Path("tests/fixtures/tiber_wr_export.csv")


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_tiber_export_normalization_writes_contract_and_provenance(tmp_path: Path) -> None:
    output_path = tmp_path / "player_weekly_history.csv"
    provenance_path = tmp_path / "player_weekly_history.provenance.json"

    result = build_wr_history_from_tiber_data(
        output_path=output_path,
        provenance_path=provenance_path,
        export_path_or_url=str(FIXTURE_PATH),
    )

    rows = _read_csv_rows(output_path)
    assert [row["player_id"] for row in rows] == ["wr_alpha", "wr_beta", "wr_alpha"]
    assert rows[0]["player_name"] == "Alpha Wideout"
    assert rows[0]["team"] == "AAA"
    assert rows[0]["fantasy_points_ppr"] == "18.0"
    assert rows[0]["receiving_yards"] == "110.0"
    assert rows[0]["games"] == "1"
    assert rows[0]["snap_share"] == "0.8"

    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert result.source_type == TIBER_DATA_EXPORT_SOURCE_TYPE
    assert provenance["source_type"] == TIBER_DATA_EXPORT_SOURCE_TYPE
    assert provenance["source_location"] == str(FIXTURE_PATH)
    assert provenance["seasons"] == [2024, 2025]
    assert provenance["used_fallback"] is False


def test_tiber_adapter_rejects_duplicate_player_weeks(tmp_path: Path) -> None:
    duplicate_export = tmp_path / "duplicate.csv"
    duplicate_export.write_text(
        "player_id,player_name,team,season,week,position,fantasy_points_ppr,targets,receptions,receiving_yards,receiving_tds\n"
        "wr_dup,Duplicate,DDD,2024,1,WR,10.0,5,4,50,1\n"
        "wr_dup,Duplicate,DDD,2024,1,WR,11.0,6,5,60,1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="duplicate WR weekly primary key"):
        build_wr_history_from_tiber_data(output_path=tmp_path / "out.csv", export_path_or_url=str(duplicate_export))


def test_tiber_adapter_rejects_non_wr_rows(tmp_path: Path) -> None:
    invalid_export = tmp_path / "invalid.csv"
    invalid_export.write_text(
        "player_id,player_name,team,season,week,position,fantasy_points_ppr,targets,receptions,receiving_yards,receiving_tds\n"
        "rb_test,Runner,RRR,2024,1,RB,10.0,5,4,50,1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="only supports WR rows"):
        build_wr_history_from_tiber_data(output_path=tmp_path / "out.csv", export_path_or_url=str(invalid_export))


def test_preferred_source_explicitly_falls_back_to_local_builder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_path = tmp_path / "player_weekly_history.csv"
    provenance_path = tmp_path / "player_weekly_history.provenance.json"

    def fake_local_builder(output_path: Path, seasons: list[int] | None = None) -> Path:
        output_path.write_text(
            "player_id,player_name,team,season,week,position,fantasy_points_ppr,targets,receptions,receiving_yards,receiving_tds,games,snap_share,route_participation,target_share,air_yard_share\n"
            "wr_local,Local Builder,LOC,2024,1,WR,9.0,6,4,50,0,1,0.6,0.75,0.18,0.2\n",
            encoding="utf-8",
        )
        return output_path

    monkeypatch.setattr("scripts.build_real_wr_data.build_real_wr_history", fake_local_builder)

    result = build_real_wr_history_with_preferred_source(
        output_path=output_path,
        provenance_path=provenance_path,
        source="preferred",
    )

    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert result.source_type == LOCAL_BUILDER_SOURCE_TYPE
    assert result.used_fallback is True
    assert provenance["source_type"] == LOCAL_BUILDER_SOURCE_TYPE
    assert provenance["used_fallback"] is True
    assert "requires either an export path/URL or an API URL" in provenance["fallback_reason"]


def test_explicit_tiber_source_does_not_silently_fallback(tmp_path: Path) -> None:
    with pytest.raises(TiberDataSourceUnavailable, match="requires either an export path/URL or an API URL"):
        build_real_wr_history_with_preferred_source(
            output_path=tmp_path / "player_weekly_history.csv",
            provenance_path=tmp_path / "player_weekly_history.provenance.json",
            source="tiber-data",
        )
