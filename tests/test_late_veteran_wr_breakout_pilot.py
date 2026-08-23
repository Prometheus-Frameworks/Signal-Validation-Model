from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from src.ingestion import (
    PlayerSeasonCoverageArtifact,
    PlayerSeasonCoverageReceipt,
    PlayerSeasonRecord,
)
from src.reporting import build_late_veteran_wr_breakout_v0
from src.reporting.late_veteran_wr_breakout import (
    DECLARED_COMPARISON_IDS,
    EVIDENCE_CUTOFF_AT,
    EVIDENCE_CUTOFF_DATE,
    _read_and_validate_pilot_receipts,
)
from src.validation import ValidationError


PILOT_RECEIPTS = Path(
    "data/raw/late_veteran_wr_breakout_2026_pilot_receipts_v0.json"
)


def _record(
    player_id: str,
    player_name: str,
    season: int,
    rookie_year: int,
    ppg: float,
    target_share: float,
) -> PlayerSeasonRecord:
    games = 12
    return PlayerSeasonRecord(
        player_id=player_id,
        player_name=player_name,
        position="WR",
        espn_id=None,
        sleeper_id=None,
        identity_confidence="source_verified",
        teams=("TST",),
        primary_team="TST",
        season=season,
        season_type="REG",
        rookie_year=rookie_year,
        career_year=season - rookie_year + 1,
        games_played=games,
        season_ppr=round(ppg * games, 4),
        season_ppg=ppg,
        targets=24,
        receptions=15,
        receiving_yards=220.0,
        receiving_tds=2,
        target_share=target_share,
        air_yards_share=0.10,
        wopr=0.20,
        routes_run=None,
        route_participation=None,
        snap_share=None,
        missing_fields=("routes_run", "route_participation", "snap_share"),
    )


def _synthetic_artifact() -> PlayerSeasonCoverageArtifact:
    records = tuple(
        sorted(
            (
                _record("00-0036259", "Jauan Jennings", 2021, 2020, 2.0, 0.04),
                _record("00-0036259", "Jauan Jennings", 2022, 2020, 3.0, 0.05),
                _record("00-0036259", "Jauan Jennings", 2023, 2020, 3.96, 0.0701),
                _record("00-0036259", "Jauan Jennings", 2024, 2020, 14.03, 0.2203),
                _record("00-0038606", "Parker Washington", 2023, 2023, 3.0, 0.04),
                _record("00-0038606", "Parker Washington", 2024, 2023, 6.93, 0.0977),
                _record("00-0038606", "Parker Washington", 2025, 2023, 11.54, 0.1737),
                _record("00-neg-a", "Negative Alpha", 2023, 2023, 2.0, 0.03),
                _record("00-neg-a", "Negative Alpha", 2024, 2023, 4.0, 0.06),
                _record("00-neg-a", "Negative Alpha", 2025, 2023, 8.0, 0.10),
                _record("00-neg-b", "Negative Beta", 2023, 2023, 2.5, 0.04),
                _record("00-neg-b", "Negative Beta", 2024, 2023, 4.5, 0.07),
                _record("00-neg-b", "Negative Beta", 2025, 2023, 9.0, 0.12),
                _record("00-0039792", "Devontez Walker", 2024, 2024, 3.03, 0.0240),
                _record("00-0039792", "Devontez Walker", 2025, 2024, 4.70, 0.0197),
                _record("00-0039739", "Roman Wilson", 2024, 2024, 0.0, 0.01),
                _record("00-0039739", "Roman Wilson", 2025, 2024, 4.29, 0.0402),
            ),
            key=lambda row: (row.season, row.player_id),
        )
    )
    by_season = tuple(sorted(Counter(row.season for row in records).items()))
    receipt = PlayerSeasonCoverageReceipt(
        source_repository="https://github.com/Prometheus-Frameworks/TIBER-Data",
        source_commit_sha="1" * 40,
        artifact_last_changed_commit_sha="2" * 40,
        source_path="exports/promoted/nfl/player_season_coverage_v0.json",
        source_blob_sha="3" * 40,
        content_sha256=hashlib.sha256(b"offline-pilot-fixture-v0").hexdigest(),
        artifact_id="player_season_coverage_v0",
        spec_version="player_season_coverage_v0_promoted_v1",
        status="promoted_governed_artifact",
        generated_at="2026-07-06T00:00:00Z",
        promoted_at="2026-07-06T00:00:00Z",
        promotion_review="TIBER-Data#202",
        promotion_decision="promote_player_season_coverage_v0_2021_2025",
        row_grain="player_id + season + season_type",
        seasons=tuple(season for season, _ in by_season),
        season_type_scope=("REG",),
        included_positions=("WR",),
        total_record_count=len(records),
        counts_by_season=by_season,
        counts_by_position=(("WR", len(records)),),
    )
    return PlayerSeasonCoverageArtifact(records=records, receipt=receipt)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_pilot_preserves_claim_classes_cutoff_and_missing_comparison(
    tmp_path: Path,
    monkeypatch,
) -> None:
    artifact = _synthetic_artifact()
    monkeypatch.setattr(
        "src.reporting.late_veteran_wr_breakout.load_player_season_coverage",
        lambda _path: artifact,
    )
    result = build_late_veteran_wr_breakout_v0(
        player_season_input=tmp_path / "offline-player-seasons.json",
        pilot_receipts_input=PILOT_RECEIPTS,
        output_dir=tmp_path / "outputs",
    )
    payload = json.loads(result.pilot_path.read_text(encoding="utf-8"))

    assert payload["evidence_cutoff_date"] == EVIDENCE_CUTOFF_DATE == "2026-08-09"
    assert payload["evidence_cutoff_at"] == EVIDENCE_CUTOFF_AT == "2026-08-09T19:28:02Z"
    assert payload["ordering"]["semantics"] == "non_ordinal"
    assert payload["pilot"]["player_id"] == "00-0039792"
    assert set(payload["pilot"]) >= {
        "observed",
        "inferred",
        "operator",
        "forecast",
        "unknown",
    }
    assert payload["pilot"]["forecast"]["state"] == "not_activated"
    assert payload["pilot"]["forecast"]["claims"] == []
    assert payload["claim_boundaries"]["forecast_activated"] is False
    observed_claim_ids = {
        claim["claim_id"]
        for claim in payload["pilot"]["observed"]["candidate_external_observations"]
    }
    assert observed_claim_ids
    assert all(
        set(claim["basis_observed_claim_ids"]) <= observed_claim_ids
        for claim in payload["pilot"]["inferred"]
    )

    comparisons = payload["comparisons"]
    comparison_ids = [row["player_id"] for row in comparisons]
    assert comparison_ids == sorted(DECLARED_COMPARISON_IDS)
    assert len(comparison_ids) == len(DECLARED_COMPARISON_IDS) == 6
    cowing = next(row for row in comparisons if row["player_id"] == "00-0039365")
    assert cowing["player_name"] == "Jacob Cowing"
    assert cowing["availability_state"] == "unavailable_feature_row"
    assert cowing["football_archetype_eligible"] is None
    assert cowing["reason_codes"] == ["unavailable_feature_row"]
    assert cowing["observed"] is None
    assert all(
        forbidden not in row
        for row in comparisons
        for forbidden in ("rank", "ranking", "score", "winner")
    )


def test_receipt_at_exact_cutoff_is_accepted(tmp_path: Path) -> None:
    payload = json.loads(PILOT_RECEIPTS.read_text(encoding="utf-8"))
    payload["receipts"][0]["published_at"] = EVIDENCE_CUTOFF_AT
    input_path = tmp_path / "at-cutoff.json"
    _write_json(input_path, payload)

    expected_digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
    validated, digest = _read_and_validate_pilot_receipts(
        input_path,
        expected_sha256=expected_digest,
    )

    assert validated["receipts"][0]["published_at"] == EVIDENCE_CUTOFF_AT
    assert digest == hashlib.sha256(input_path.read_bytes()).hexdigest()


def test_post_cutoff_receipt_is_rejected(tmp_path: Path) -> None:
    payload = deepcopy(json.loads(PILOT_RECEIPTS.read_text(encoding="utf-8")))
    payload["receipts"][0]["published_at"] = "2026-08-09T19:28:03Z"
    input_path = tmp_path / "post-cutoff.json"
    _write_json(input_path, payload)

    with pytest.raises(ValidationError, match="exceeds the evidence cutoff"):
        _read_and_validate_pilot_receipts(
            input_path,
            expected_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),
        )


def test_unpinned_pilot_receipt_bytes_fail_before_content_validation(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "untrusted.json"
    input_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValidationError, match="pilot receipt input digest mismatch"):
        _read_and_validate_pilot_receipts(input_path)


def test_inference_must_reference_an_observed_claim(tmp_path: Path) -> None:
    payload = deepcopy(json.loads(PILOT_RECEIPTS.read_text(encoding="utf-8")))
    payload["pilot"]["claim_boundaries"]["inferred"][0][
        "basis_observed_claim_ids"
    ] = ["unknown_observed_claim"]
    input_path = tmp_path / "unknown-observed-claim.json"
    _write_json(input_path, payload)

    with pytest.raises(ValidationError, match="known observed claim IDs"):
        _read_and_validate_pilot_receipts(
            input_path,
            expected_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),
        )


def test_missing_pilot_feature_row_remains_visible(tmp_path: Path, monkeypatch) -> None:
    source = _synthetic_artifact()
    records = tuple(row for row in source.records if row.player_id != "00-0039792")
    by_season = tuple(sorted(Counter(row.season for row in records).items()))
    artifact = PlayerSeasonCoverageArtifact(
        records=records,
        receipt=replace(
            source.receipt,
            seasons=tuple(season for season, _ in by_season),
            total_record_count=len(records),
            counts_by_season=by_season,
            counts_by_position=(("WR", len(records)),),
        ),
    )
    monkeypatch.setattr(
        "src.reporting.late_veteran_wr_breakout.load_player_season_coverage",
        lambda _path: artifact,
    )

    result = build_late_veteran_wr_breakout_v0(
        player_season_input=tmp_path / "offline-player-seasons.json",
        pilot_receipts_input=PILOT_RECEIPTS,
        output_dir=tmp_path / "outputs",
    )
    payload = json.loads(result.pilot_path.read_text(encoding="utf-8"))

    assert payload["pilot"]["player_id"] == "00-0039792"
    assert payload["pilot"]["football_archetype_eligibility"] == {
        "state": "unavailable_feature_row",
        "eligible": None,
        "reason_codes": ["unavailable_feature_row"],
    }
    assert payload["pilot"]["observed"]["governed_historical"] is None


def test_comparison_identity_conflict_is_explicit(tmp_path: Path, monkeypatch) -> None:
    source = _synthetic_artifact()
    records = tuple(
        replace(row, player_name="Conflicting Name")
        if row.player_id == "00-0039739"
        else row
        for row in source.records
    )
    artifact = PlayerSeasonCoverageArtifact(records=records, receipt=source.receipt)
    monkeypatch.setattr(
        "src.reporting.late_veteran_wr_breakout.load_player_season_coverage",
        lambda _path: artifact,
    )

    result = build_late_veteran_wr_breakout_v0(
        player_season_input=tmp_path / "offline-player-seasons.json",
        pilot_receipts_input=PILOT_RECEIPTS,
        output_dir=tmp_path / "outputs",
    )
    payload = json.loads(result.pilot_path.read_text(encoding="utf-8"))
    roman = next(
        row for row in payload["comparisons"] if row["player_id"] == "00-0039739"
    )

    assert roman["availability_state"] == "unresolved_identity"
    assert roman["football_archetype_eligible"] is None
    assert roman["observed"] is None
    assert roman["reason_codes"] == [
        "source_name_conflicts_with_canonical_player_id"
    ]
