from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from src.ingestion.tiber_player_season_coverage import (
    EXPECTED_ARTIFACT_ID,
    EXPECTED_PROMOTION_DECISION,
    EXPECTED_PROMOTION_REVIEW,
    EXPECTED_SEASONS,
    EXPECTED_SPEC_VERSION,
    EXPECTED_STATUS,
    PINNED_ARTIFACT_LAST_CHANGED_COMMIT_SHA,
    PINNED_PLAYER_SEASON_COVERAGE_BLOB_SHA,
    PINNED_PLAYER_SEASON_COVERAGE_PATH,
    PINNED_TIBER_DATA_COMMIT_SHA,
    TIBER_DATA_REPOSITORY,
    _load_player_season_coverage_with_expected_digest,
    load_player_season_coverage,
)
from src.validation import ValidationError


def _record(
    *,
    player_id: str,
    player_name: str,
    position: str,
    season: int,
    rookie_year: int | None = None,
    provider_ids: dict[str, str | None] | None = None,
    air_yards_share: float = 0.05,
) -> dict:
    resolved_rookie_year = season if rookie_year is None else rookie_year
    return {
        "player_id": player_id,
        "player_name": player_name,
        "position": position,
        "provider_ids": provider_ids,
        "identity_confidence": "source_verified",
        "teams": ["TST"],
        "primary_team": "TST",
        "season": season,
        "season_type": "REG",
        "rookie_year": resolved_rookie_year,
        "career_year": season - resolved_rookie_year + 1,
        "games_played": 8,
        "production_summary": {
            "season_ppr": 40.0,
            "games_for_ppg": 8,
            "season_ppg": 5.0,
            "receiving": {
                "receiving_yards": 300.0,
                "receiving_tds": 2,
            },
        },
        "usage_summary": {
            "targets": 30,
            "receptions": 20,
            "target_share": 0.08,
            "air_yards_share": air_yards_share,
            "wopr": 0.18,
            "routes_run": None,
            "route_participation": None,
            "snap_share": None,
        },
        "missing_fields": [
            "routes_run",
            "route_participation",
            "snap_share",
        ],
    }


def _records() -> list[dict]:
    return [
        _record(
            player_id="00-wr-2021",
            player_name="Alpha Wideout",
            position="WR",
            season=2021,
            provider_ids=None,
            air_yards_share=-0.0001,
        ),
        _record(
            player_id="00-rb-2022",
            player_name="Beta Runner",
            position="RB",
            season=2022,
            provider_ids={"espn_id": "1002", "sleeper_id": None},
        ),
        _record(
            player_id="00-te-2023",
            player_name="Gamma Tight End",
            position="TE",
            season=2023,
            provider_ids={"espn_id": "1003", "sleeper_id": "s-1003"},
        ),
        _record(
            player_id="00-qb-2024",
            player_name="Delta Quarterback",
            position="QB",
            season=2024,
            provider_ids={"espn_id": None, "sleeper_id": None},
        ),
        _record(
            player_id="00-wr-zulu",
            player_name="Zulu Wideout",
            position="WR",
            season=2025,
            rookie_year=2024,
            provider_ids={"espn_id": "1005", "sleeper_id": None},
        ),
        _record(
            player_id="00-wr-echo",
            player_name="Echo Wideout",
            position="WR",
            season=2025,
            rookie_year=2025,
            provider_ids={"espn_id": "1006", "sleeper_id": None},
        ),
    ]


def _payload(records: list[dict] | None = None) -> dict:
    resolved_records = _records() if records is None else records
    by_season = Counter(record["season"] for record in resolved_records)
    by_position = Counter(record["position"] for record in resolved_records)
    return {
        "artifact_id": EXPECTED_ARTIFACT_ID,
        "spec_version": EXPECTED_SPEC_VERSION,
        "status": EXPECTED_STATUS,
        "generated_at": "2026-07-06T00:00:00Z",
        "promoted_at": "2026-07-06T00:00:00Z",
        "promotion_review": EXPECTED_PROMOTION_REVIEW,
        "promotion_decision": EXPECTED_PROMOTION_DECISION,
        "no_fixture_or_scaffold_markers_confirmed": True,
        "seasons": list(EXPECTED_SEASONS),
        "season_type_scope": ["REG"],
        "included_positions": ["QB", "RB", "TE", "WR"],
        "row_grain": "player_id + season + season_type",
        "counts": {
            "records": len(resolved_records),
            "by_season": {
                str(season): by_season[season]
                for season in reversed(EXPECTED_SEASONS)
            },
            "by_position": {
                position: by_position[position]
                for position in ("WR", "TE", "RB", "QB")
            },
        },
        "records": resolved_records,
    }


def _write_payload(path: Path, payload: dict) -> str:
    raw_bytes = (
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    path.write_bytes(raw_bytes)
    return hashlib.sha256(raw_bytes).hexdigest()


def _load_synthetic(path: Path, payload: dict):
    digest = _write_payload(path, payload)
    return _load_player_season_coverage_with_expected_digest(
        path,
        expected_sha256=digest,
    )


def test_digest_is_verified_before_invalid_json_is_parsed(tmp_path: Path) -> None:
    input_path = tmp_path / "invalid.json"
    input_path.write_bytes(b"{not valid json")

    with pytest.raises(ValidationError, match="digest mismatch"):
        load_player_season_coverage(input_path)


def test_loads_exact_metadata_and_pinned_source_receipt(tmp_path: Path) -> None:
    artifact = _load_synthetic(tmp_path / "coverage.json", _payload())
    receipt = artifact.receipt

    assert receipt.source_repository == TIBER_DATA_REPOSITORY
    assert receipt.source_commit_sha == PINNED_TIBER_DATA_COMMIT_SHA
    assert (
        receipt.artifact_last_changed_commit_sha
        == PINNED_ARTIFACT_LAST_CHANGED_COMMIT_SHA
    )
    assert receipt.source_path == PINNED_PLAYER_SEASON_COVERAGE_PATH
    assert receipt.source_blob_sha == PINNED_PLAYER_SEASON_COVERAGE_BLOB_SHA
    assert receipt.artifact_id == EXPECTED_ARTIFACT_ID
    assert receipt.spec_version == EXPECTED_SPEC_VERSION
    assert receipt.status == EXPECTED_STATUS
    assert receipt.promotion_review == EXPECTED_PROMOTION_REVIEW
    assert receipt.promotion_decision == EXPECTED_PROMOTION_DECISION
    assert receipt.seasons == EXPECTED_SEASONS
    assert receipt.season_type_scope == ("REG",)
    assert receipt.total_record_count == 6


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "error_match"),
    [
        ("status", "candidate", "artifact.status must equal"),
        ("promotion_review", "TIBER-Data#999", "artifact.promotion_review must equal"),
        (
            "promotion_decision",
            "another_decision",
            "artifact.promotion_decision must equal",
        ),
    ],
)
def test_rejects_metadata_drift(
    tmp_path: Path,
    field_name: str,
    invalid_value: str,
    error_match: str,
) -> None:
    payload = _payload()
    payload[field_name] = invalid_value
    input_path = tmp_path / f"invalid-{field_name}.json"
    digest = _write_payload(input_path, payload)

    with pytest.raises(ValidationError, match=error_match):
        _load_player_season_coverage_with_expected_digest(
            input_path,
            expected_sha256=digest,
        )


def test_rejects_non_exact_season_window(tmp_path: Path) -> None:
    payload = _payload()
    payload["seasons"] = [2022, 2023, 2024, 2025]
    input_path = tmp_path / "invalid-seasons.json"
    digest = _write_payload(input_path, payload)

    with pytest.raises(ValidationError, match="artifact.seasons must equal"):
        _load_player_season_coverage_with_expected_digest(
            input_path,
            expected_sha256=digest,
        )


@pytest.mark.parametrize(
    ("container", "field_name", "invalid_value", "error_match"),
    [
        (
            "production_summary",
            "season_ppg",
            "5.0",
            "production_summary.season_ppg must be numeric",
        ),
        (
            "usage_summary",
            "target_share",
            1.01,
            "usage_summary.target_share must be between 0 and 1",
        ),
        (
            "usage_summary",
            "wopr",
            -0.01,
            "usage_summary.wopr cannot be negative",
        ),
    ],
)
def test_rejects_invalid_nested_field_types_and_ranges(
    tmp_path: Path,
    container: str,
    field_name: str,
    invalid_value: object,
    error_match: str,
) -> None:
    payload = _payload()
    payload["records"][0][container][field_name] = invalid_value
    input_path = tmp_path / f"invalid-{container}-{field_name}.json"
    digest = _write_payload(input_path, payload)

    with pytest.raises(ValidationError, match=error_match):
        _load_player_season_coverage_with_expected_digest(
            input_path,
            expected_sha256=digest,
        )


def test_null_provider_ids_are_preserved_as_unavailable(tmp_path: Path) -> None:
    artifact = _load_synthetic(tmp_path / "coverage.json", _payload())
    record = next(
        record for record in artifact.records if record.player_id == "00-wr-2021"
    )

    assert record.espn_id is None
    assert record.sleeper_id is None


def test_slightly_negative_air_yards_share_is_valid_context(tmp_path: Path) -> None:
    artifact = _load_synthetic(tmp_path / "coverage.json", _payload())
    record = next(
        record for record in artifact.records if record.player_id == "00-wr-2021"
    )

    assert record.air_yards_share == pytest.approx(-0.0001)


def test_record_and_count_ordering_is_deterministic(tmp_path: Path) -> None:
    records = _records()
    payload_a = _payload(list(reversed(records)))
    payload_b = _payload([records[4], records[1], records[5], records[0], records[3], records[2]])

    artifact_a = _load_synthetic(tmp_path / "coverage-a.json", payload_a)
    artifact_b = _load_synthetic(tmp_path / "coverage-b.json", payload_b)

    assert artifact_a.records == artifact_b.records
    assert [
        (record.season, record.position, record.player_id)
        for record in artifact_a.records
    ] == [
        (2021, "WR", "00-wr-2021"),
        (2022, "RB", "00-rb-2022"),
        (2023, "TE", "00-te-2023"),
        (2024, "QB", "00-qb-2024"),
        (2025, "WR", "00-wr-echo"),
        (2025, "WR", "00-wr-zulu"),
    ]
    assert artifact_a.receipt.counts_by_season == (
        (2021, 1),
        (2022, 1),
        (2023, 1),
        (2024, 1),
        (2025, 2),
    )
    assert artifact_a.receipt.counts_by_position == (
        ("QB", 1),
        ("RB", 1),
        ("TE", 1),
        ("WR", 3),
    )


def test_rejects_career_year_conflict(tmp_path: Path) -> None:
    payload = _payload()
    payload["records"][0]["career_year"] += 1
    input_path = tmp_path / "career-year-conflict.json"
    digest = _write_payload(input_path, payload)

    with pytest.raises(
        ValidationError,
        match=r"career_year must equal season - rookie_year \+ 1",
    ):
        _load_player_season_coverage_with_expected_digest(
            input_path,
            expected_sha256=digest,
        )


def test_rejects_duplicate_player_season_grain(tmp_path: Path) -> None:
    records = _records()
    records.append(deepcopy(records[0]))
    payload = _payload(records)
    input_path = tmp_path / "duplicate-grain.json"
    digest = _write_payload(input_path, payload)

    with pytest.raises(ValidationError, match="duplicate player-season coverage key"):
        _load_player_season_coverage_with_expected_digest(
            input_path,
            expected_sha256=digest,
        )


def test_rejects_conflicting_identity_for_same_player_id(tmp_path: Path) -> None:
    records = _records()
    records[-1]["player_id"] = records[0]["player_id"]
    records[-1]["rookie_year"] = 2021
    records[-1]["career_year"] = 5
    payload = _payload(records)
    input_path = tmp_path / "identity-conflict.json"
    digest = _write_payload(input_path, payload)

    with pytest.raises(ValidationError, match="conflicting identity fields for player_id"):
        _load_player_season_coverage_with_expected_digest(
            input_path,
            expected_sha256=digest,
        )
