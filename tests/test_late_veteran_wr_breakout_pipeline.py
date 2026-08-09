from __future__ import annotations

from collections import Counter
import csv
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any

from src.ingestion import (
    PlayerSeasonCoverageArtifact,
    PlayerSeasonCoverageReceipt,
    PlayerSeasonRecord,
)
from src.reporting import build_late_veteran_wr_breakout_v0
from src.reporting.late_veteran_wr_breakout import (
    HISTORICAL_PAIR_COLUMNS,
    TERMINAL_DECISIONS,
)


PILOT_RECEIPTS = Path(
    "data/raw/late_veteran_wr_breakout_2026_pilot_receipts_v0.json"
)


def _record(
    player_id: str,
    player_name: str,
    season: int,
    rookie_year: int,
    *,
    ppg: float,
    target_share: float,
    games: int = 12,
) -> PlayerSeasonRecord:
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


def _synthetic_records() -> tuple[PlayerSeasonRecord, ...]:
    records = [
        # Jauan Jennings: the 2020 rookie row is intentionally outside the fixture,
        # so the positive outcome trace remains prior-history incomplete.
        _record("00-0036259", "Jauan Jennings", 2021, 2020, ppg=2.0, target_share=0.04),
        _record("00-0036259", "Jauan Jennings", 2022, 2020, ppg=3.0, target_share=0.05),
        _record("00-0036259", "Jauan Jennings", 2023, 2020, ppg=3.96, target_share=0.0701),
        _record("00-0036259", "Jauan Jennings", 2024, 2020, ppg=14.03, target_share=0.2203),
        # Parker Washington: complete rookie-to-feature history and a positive hit.
        _record("00-0038606", "Parker Washington", 2023, 2023, ppg=3.0, target_share=0.04),
        _record("00-0038606", "Parker Washington", 2024, 2023, ppg=6.93, target_share=0.0977),
        _record("00-0038606", "Parker Washington", 2025, 2023, ppg=11.54, target_share=0.1737),
        # Two deterministic primary-eligible negative controls.
        _record("00-neg-a", "Negative Alpha", 2023, 2023, ppg=2.0, target_share=0.03),
        _record("00-neg-a", "Negative Alpha", 2024, 2023, ppg=4.0, target_share=0.06),
        _record("00-neg-a", "Negative Alpha", 2025, 2023, ppg=8.0, target_share=0.10),
        _record("00-neg-b", "Negative Beta", 2023, 2023, ppg=2.5, target_share=0.04),
        _record("00-neg-b", "Negative Beta", 2024, 2023, ppg=4.5, target_share=0.07),
        _record("00-neg-b", "Negative Beta", 2025, 2023, ppg=9.0, target_share=0.12),
        # The current-facing pilot has a complete 2024 -> 2025 feature history.
        _record("00-0039792", "Devontez Walker", 2024, 2024, ppg=3.03, target_share=0.0240),
        _record("00-0039792", "Devontez Walker", 2025, 2024, ppg=4.70, target_share=0.0197),
        # One declared comparison is available; the other named rows remain absent.
        _record("00-0039739", "Roman Wilson", 2024, 2024, ppg=0.0, target_share=0.01),
        _record("00-0039739", "Roman Wilson", 2025, 2024, ppg=4.29, target_share=0.0402),
    ]
    return tuple(sorted(records, key=lambda row: (row.season, row.player_id)))


def _synthetic_artifact() -> PlayerSeasonCoverageArtifact:
    records = _synthetic_records()
    by_season = tuple(sorted(Counter(row.season for row in records).items()))
    digest = hashlib.sha256(b"late-veteran-wr-breakout-offline-fixture-v0").hexdigest()
    receipt = PlayerSeasonCoverageReceipt(
        source_repository="https://github.com/Prometheus-Frameworks/TIBER-Data",
        source_commit_sha="1" * 40,
        artifact_last_changed_commit_sha="2" * 40,
        source_path="exports/promoted/nfl/player_season_coverage_v0.json",
        source_blob_sha="3" * 40,
        content_sha256=digest,
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


def _artifact_paths(result: Any) -> tuple[Path, ...]:
    return (
        result.definition_path,
        result.summary_path,
        result.historical_pairs_path,
        result.examples_path,
        result.pilot_path,
        result.receipt_path,
    )


def _forbidden_keys(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if set(str(key).lower().split("_")) & {
                "rank",
                "ranking",
                "score",
                "winner",
                "recommendation",
            }:
                found.append(str(key))
            found.extend(_forbidden_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            found.extend(_forbidden_keys(nested))
    return found


def test_pipeline_writes_six_deterministic_non_ranking_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    artifact = _synthetic_artifact()
    monkeypatch.setattr(
        "src.reporting.late_veteran_wr_breakout.load_player_season_coverage",
        lambda _path: artifact,
    )

    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first = build_late_veteran_wr_breakout_v0(
        player_season_input=tmp_path / "offline-player-seasons.json",
        pilot_receipts_input=PILOT_RECEIPTS,
        output_dir=first_root,
    )
    second = build_late_veteran_wr_breakout_v0(
        player_season_input=tmp_path / "offline-player-seasons.json",
        pilot_receipts_input=PILOT_RECEIPTS,
        output_dir=second_root,
    )

    first_paths = _artifact_paths(first)
    second_paths = _artifact_paths(second)
    assert len(first_paths) == len(second_paths) == 6
    assert all(path.exists() for path in (*first_paths, *second_paths))
    assert [path.relative_to(first_root) for path in first_paths] == [
        path.relative_to(second_root) for path in second_paths
    ]
    for first_path, second_path in zip(first_paths, second_paths, strict=True):
        assert first_path.read_bytes() == second_path.read_bytes()
        assert "candidate_rankings" not in first_path.parts
        assert "candidate_rankings" not in second_path.parts

    assert first.terminal_decision in TERMINAL_DECISIONS
    assert (
        first.terminal_decision
        == "late_veteran_wr_breakout_v0_requires_data_or_definition_followup"
    )


def test_summary_csv_and_receipt_bindings_reconcile(tmp_path: Path, monkeypatch) -> None:
    artifact = _synthetic_artifact()
    monkeypatch.setattr(
        "src.reporting.late_veteran_wr_breakout.load_player_season_coverage",
        lambda _path: artifact,
    )
    output_root = tmp_path / "outputs"
    result = build_late_veteran_wr_breakout_v0(
        player_season_input=tmp_path / "offline-player-seasons.json",
        pilot_receipts_input=PILOT_RECEIPTS,
        output_dir=output_root,
    )

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    with result.historical_pairs_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    evaluation = summary["primary_cohort_evaluation"]
    assert list(rows[0]) == HISTORICAL_PAIR_COLUMNS
    assert evaluation["observed_pair_count"] == len(rows)
    assert evaluation["evaluable_pair_count"] == sum(
        row["evaluation_state"] == "included" for row in rows
    )
    assert evaluation["coverage_exclusion_count"] == sum(
        row["evaluation_state"] == "coverage_exclusion" for row in rows
    )
    for confusion_class, summary_key in (
        ("true_positive", "true_positives"),
        ("false_positive", "false_positives"),
        ("false_negative", "false_negatives"),
        ("true_negative", "true_negatives"),
    ):
        assert evaluation[summary_key] == sum(
            row["confusion_class"] == confusion_class for row in rows
        )
    assert summary["terminal_decision"] in TERMINAL_DECISIONS

    bindings = receipt["output_bindings"]
    assert len(bindings) == 5
    assert receipt["run_guards"]["output_count_excluding_receipt"] == 5
    assert receipt["run_guards"]["receipt_self_hash_excluded"] is True
    for binding in bindings:
        path = output_root / binding["relative_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == binding["content_sha256"]
    pilot_input_digest = hashlib.sha256(PILOT_RECEIPTS.read_bytes()).hexdigest()
    assert receipt["input_bindings"]["pilot_receipts"]["content_sha256"] == pilot_input_digest

    for path in (result.definition_path, result.summary_path, result.pilot_path, result.receipt_path):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert _forbidden_keys(payload) == []


def test_missing_outcome_seam_writes_a_blocked_research_result(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = _synthetic_artifact()
    records = tuple(
        row
        for row in source.records
        if row.player_id == "00-0039792" and row.season == 2025
    )
    receipt = replace(
        source.receipt,
        seasons=(2025,),
        total_record_count=1,
        counts_by_season=((2025, 1),),
        counts_by_position=(("WR", 1),),
    )
    artifact = PlayerSeasonCoverageArtifact(records=records, receipt=receipt)
    monkeypatch.setattr(
        "src.reporting.late_veteran_wr_breakout.load_player_season_coverage",
        lambda _path: artifact,
    )

    result = build_late_veteran_wr_breakout_v0(
        player_season_input=tmp_path / "offline-player-seasons.json",
        pilot_receipts_input=PILOT_RECEIPTS,
        output_dir=tmp_path / "blocked",
    )
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))

    assert result.terminal_decision == "late_veteran_wr_breakout_v0_blocked"
    assert summary["terminal_decision"] == result.terminal_decision
    assert set(summary["historical_run_blockers"]) == {
        "no_valid_2024_to_2025_outcome_seam",
        "zero_evaluable_historical_pairs",
    }
    assert all(path.exists() for path in _artifact_paths(result))
