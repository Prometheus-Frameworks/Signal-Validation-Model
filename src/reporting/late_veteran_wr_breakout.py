"""Deterministic research artifacts for ``late_veteran_wr_breakout_v0``.

This writer consumes only local, digest-pinned inputs.  It does not fetch live
sources, rank candidates, or create a downstream recommendation surface.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import inspect
import json
import math
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping
from urllib.parse import urlparse

from src.ingestion import (
    PlayerSeasonCoverageArtifact,
    PlayerSeasonRecord,
    load_player_season_coverage,
)
from src.labels.late_veteran_wr_breakout import (
    DECLARED_OBSERVED_ROW_UNIVERSE,
    LATE_VETERAN_WR_BREAKOUT_V0,
    HistoricalPair,
    PrimaryCohortEvaluation,
    build_diagnostic_sensitivity_grid,
    build_historical_pairs,
    evaluate_feature_eligibility,
    evaluate_primary_cohort,
)
from src.validation import ValidationError

DEFINITION_VERSION = "late_veteran_wr_breakout_v0"
EVIDENCE_CUTOFF_DATE = "2026-08-09"
EVIDENCE_CUTOFF_AT = "2026-08-09T19:28:02Z"
PINNED_PILOT_RECEIPTS_SHA256 = (
    "114af8226458759c15f89428601b6cf007080387f35a8fe83667db52ba22f3c8"
)
RESEARCH_ISSUE_URL = (
    "https://github.com/Prometheus-Frameworks/Signal-Validation-Model/issues/16"
)
PINNED_SIGNAL_VALIDATION_BASE_COMMIT_SHA = (
    "0b8f600a4779df4c64420844649b732edeb6c3e2"
)
PILOT_PLAYER_ID = "00-0039792"
PILOT_PLAYER_NAME = "Devontez Walker"
POSITIVE_CONTROL_IDS = ("00-0036259", "00-0038606")
DECLARED_COMPARISON_IDS = frozenset(
    {
        "00-0039739",  # Roman Wilson
        "00-0039751",  # Jordan Whittington
        "00-0039355",  # Luke McCaffrey
        "00-0039365",  # Jacob Cowing
        "00-0038104",  # Tyquan Thornton
        "00-0039410",  # Ryan Flournoy
    }
)
TERMINAL_DECISIONS = frozenset(
    {
        "late_veteran_wr_breakout_v0_research_validated",
        "late_veteran_wr_breakout_v0_requires_data_or_definition_followup",
        "late_veteran_wr_breakout_v0_blocked",
    }
)
TerminalDecision = Literal[
    "late_veteran_wr_breakout_v0_research_validated",
    "late_veteran_wr_breakout_v0_requires_data_or_definition_followup",
    "late_veteran_wr_breakout_v0_blocked",
]

HISTORICAL_PAIR_COLUMNS = [
    "player_id",
    "player_name",
    "feature_season",
    "target_season",
    "feature_team",
    "feature_career_year",
    "target_career_year",
    "feature_games_played",
    "feature_ppr",
    "feature_ppg",
    "feature_targets",
    "feature_receptions",
    "feature_receiving_yards",
    "feature_receiving_tds",
    "feature_target_share",
    "feature_air_yards_share",
    "feature_wopr",
    "eligibility_state",
    "football_archetype_eligible",
    "market_status",
    "market_qualified_eligible",
    "eligibility_reason_codes",
    "market_reason_codes",
    "outcome_available",
    "outcome_season",
    "outcome_team",
    "outcome_career_year",
    "outcome_games_played",
    "outcome_ppr",
    "outcome_ppg",
    "outcome_targets",
    "outcome_receptions",
    "outcome_receiving_yards",
    "outcome_receiving_tds",
    "outcome_target_share",
    "outcome_air_yards_share",
    "outcome_wopr",
    "fantasy_breakout",
    "role_expansion",
    "archetype_hit",
    "ppg_increase",
    "target_share_increase",
    "outcome_reason_codes",
    "evaluation_state",
    "evaluation_exclusion_reason",
    "confusion_class",
]


@dataclass(frozen=True)
class LateVeteranWrBreakoutArtifacts:
    definition_path: Path
    summary_path: Path
    historical_pairs_path: Path
    examples_path: Path
    pilot_path: Path
    receipt_path: Path
    terminal_decision: TerminalDecision


def build_late_veteran_wr_breakout_v0(
    player_season_input: str | Path,
    pilot_receipts_input: str | Path,
    output_dir: str | Path = "outputs",
) -> LateVeteranWrBreakoutArtifacts:
    """Build the six issue-16 research artifacts from local pinned inputs."""

    player_artifact = load_player_season_coverage(player_season_input)
    pilot_input_path = Path(pilot_receipts_input)
    pilot_source, pilot_input_sha256 = _read_and_validate_pilot_receipts(pilot_input_path)

    records = player_artifact.records_for_position("WR")
    if not records:
        raise ValidationError("pinned player-season input contains no WR records")
    historical_pairs = build_historical_pairs(records)
    primary_evaluation = evaluate_primary_cohort(historical_pairs)
    sensitivity = build_diagnostic_sensitivity_grid(records)
    historical_run_blockers = _historical_run_blockers(
        historical_pairs,
        primary_evaluation,
    )

    terminal_decision = _terminal_decision(
        primary_evaluation,
        historical_run_blockers,
    )
    definition_payload = _build_definition_payload()
    summary_payload = _build_summary_payload(
        player_artifact=player_artifact,
        records=records,
        historical_pairs=historical_pairs,
        primary_evaluation=primary_evaluation,
        sensitivity=sensitivity,
        terminal_decision=terminal_decision,
        historical_run_blockers=historical_run_blockers,
    )
    pair_rows = [_historical_pair_row(pair) for pair in historical_pairs]
    examples_markdown = _build_examples_markdown(historical_pairs)
    pilot_payload = _build_pilot_payload(
        records=records,
        pilot_source=pilot_source,
        player_artifact=player_artifact,
        pilot_input_sha256=pilot_input_sha256,
    )

    base_output = Path(output_dir)
    validation_dir = base_output / "validation_reports"
    case_study_dir = base_output / "case_studies"
    validation_dir.mkdir(parents=True, exist_ok=True)
    case_study_dir.mkdir(parents=True, exist_ok=True)

    definition_path = validation_dir / "late_veteran_wr_breakout_v0_definition.json"
    summary_path = validation_dir / "late_veteran_wr_breakout_v0_summary.json"
    historical_pairs_path = (
        validation_dir / "late_veteran_wr_breakout_v0_historical_pairs.csv"
    )
    examples_path = case_study_dir / "late_veteran_wr_breakout_v0_examples.md"
    pilot_path = case_study_dir / "late_veteran_wr_breakout_2026_pilot.json"
    receipt_path = validation_dir / "late_veteran_wr_breakout_v0_receipt.json"

    for payload, label in (
        (definition_payload, "definition"),
        (summary_payload, "summary"),
        (pilot_payload, "pilot"),
    ):
        _assert_no_forbidden_output_keys(payload, label)

    _write_json(definition_path, definition_payload)
    _write_json(summary_path, summary_payload)
    _write_csv(historical_pairs_path, HISTORICAL_PAIR_COLUMNS, pair_rows)
    examples_path.write_text(examples_markdown, encoding="utf-8")
    _write_json(pilot_path, pilot_payload)

    output_paths = (
        definition_path,
        summary_path,
        historical_pairs_path,
        examples_path,
        pilot_path,
    )
    receipt_payload = _build_receipt_payload(
        base_output=base_output,
        player_artifact=player_artifact,
        pilot_source=pilot_source,
        pilot_input_sha256=pilot_input_sha256,
        output_paths=output_paths,
    )
    _assert_no_forbidden_output_keys(receipt_payload, "receipt")
    _write_json(receipt_path, receipt_payload)

    return LateVeteranWrBreakoutArtifacts(
        definition_path=definition_path,
        summary_path=summary_path,
        historical_pairs_path=historical_pairs_path,
        examples_path=examples_path,
        pilot_path=pilot_path,
        receipt_path=receipt_path,
        terminal_decision=terminal_decision,
    )


def _build_definition_payload() -> dict[str, Any]:
    definition = asdict(LATE_VETERAN_WR_BREAKOUT_V0)
    return {
        "artifact_id": "late_veteran_wr_breakout_v0_definition",
        "spec_version": DEFINITION_VERSION,
        "status": "frozen_research_definition_not_promoted",
        "research_issue": RESEARCH_ISSUE_URL,
        "frozen_at": EVIDENCE_CUTOFF_AT,
        "primary_hypothesis": definition,
        "declared_observed_row_universe": DECLARED_OBSERVED_ROW_UNIVERSE,
        "eligibility_states": {
            "football_archetype_eligible": (
                "Uses source-backed tenure, complete exposure history, prior production, "
                "feature PPG, and feature target share only."
            ),
            "market_qualified_eligible": (
                "Unavailable in v0 because no governed comparable redraft ADP input is bound."
            ),
        },
        "outcome_labels": {
            "fantasy_breakout": (
                "Outcome games, PPR PPG floor, and PPG increase are evaluated together."
            ),
            "role_expansion": (
                "Outcome target-share level and increase are evaluated separately."
            ),
            "archetype_hit": "Requires fantasy_breakout and confirmed role_expansion.",
        },
        "leakage_boundary": {
            "feature_side_only": [
                "position",
                "season_type",
                "rookie_year",
                "career_year",
                "season_ppg",
                "target_share",
                "complete_prior_history",
            ],
            "outcome_side_only": [
                "outcome_games_played",
                "outcome_season_ppg",
                "outcome_target_share",
            ],
            "outcome_fields_used_for_feature_eligibility": False,
        },
        "sensitivity_posture": {
            "diagnostic_only": True,
            "may_replace_primary_v0": False,
            "market_grid_state": "not_evaluated_governed_market_input_unavailable",
        },
    }


def _build_summary_payload(
    *,
    player_artifact: PlayerSeasonCoverageArtifact,
    records: tuple[PlayerSeasonRecord, ...],
    historical_pairs: tuple[HistoricalPair, ...],
    primary_evaluation: PrimaryCohortEvaluation,
    sensitivity: Iterable[Any],
    terminal_decision: TerminalDecision,
    historical_run_blockers: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "artifact_id": "late_veteran_wr_breakout_v0_summary",
        "spec_version": DEFINITION_VERSION,
        "status": "research_result_not_promoted",
        "research_issue": RESEARCH_ISSUE_URL,
        "repository_base_commit_sha": PINNED_SIGNAL_VALIDATION_BASE_COMMIT_SHA,
        "evidence_cutoff_at": EVIDENCE_CUTOFF_AT,
        "terminal_decision": terminal_decision,
        "historical_run_blockers": list(historical_run_blockers),
        "input_coverage": {
            "artifact_id": player_artifact.receipt.artifact_id,
            "source_commit_sha": player_artifact.receipt.source_commit_sha,
            "source_blob_sha": player_artifact.receipt.source_blob_sha,
            "content_sha256": player_artifact.receipt.content_sha256,
            "seasons": list(player_artifact.receipt.seasons),
            "all_position_record_count": player_artifact.receipt.total_record_count,
            "wr_record_count": len(records),
        },
        "population": {
            "declared_universe": DECLARED_OBSERVED_ROW_UNIVERSE,
            "by_feature_season": _population_by_feature_season(historical_pairs),
            "eligibility_state_counts": dict(
                sorted(Counter(pair.eligibility.state for pair in historical_pairs).items())
            ),
            "evaluation_exclusion_counts": dict(
                sorted(
                    Counter(
                        pair.evaluation_exclusion_reason
                        for pair in historical_pairs
                        if pair.evaluation_exclusion_reason is not None
                    ).items()
                )
            ),
        },
        "missingness": _missingness_payload(records, historical_pairs),
        "primary_cohort_evaluation": _evaluation_payload(primary_evaluation),
        "terminal_decision_basis": _terminal_decision_basis(
            primary_evaluation,
            records,
            historical_run_blockers,
        ),
        "no_leakage_receipt": _no_leakage_receipt(),
        "descriptive_feature_comparison": _feature_comparison_payload(historical_pairs),
        "diagnostic_sensitivity": {
            "configuration_count": len(tuple(sensitivity)),
            "primary_definition_replaced": False,
            "market_dimension": {
                "state": "not_evaluated_governed_market_input_unavailable",
                "declared_cutoffs": list(
                    LATE_VETERAN_WR_BREAKOUT_V0.market_adp_sensitivity
                ),
                "unranked_case_declared": (
                    LATE_VETERAN_WR_BREAKOUT_V0.market_unranked_sensitivity_declared
                ),
            },
            "configurations": [_sensitivity_payload(item) for item in sensitivity],
        },
        "interpretation_limits": [
            "The evaluation universe is the pinned observed stat-row population, not a historical active-roster census.",
            "Coverage exclusions are not false negatives.",
            "No predictive-power claim is made.",
            "Market-qualified eligibility remains unavailable.",
            "Routes, route participation, and snap share do not influence any result because their promoted coverage is absent.",
        ],
    }


def _build_pilot_payload(
    *,
    records: tuple[PlayerSeasonRecord, ...],
    pilot_source: Mapping[str, Any],
    player_artifact: PlayerSeasonCoverageArtifact,
    pilot_input_sha256: str,
) -> dict[str, Any]:
    by_key = {(record.player_id, record.season): record for record in records}
    histories: dict[str, tuple[PlayerSeasonRecord, ...]] = defaultdict(tuple)
    for player_id in {record.player_id for record in records}:
        histories[player_id] = tuple(
            sorted(
                (record for record in records if record.player_id == player_id),
                key=lambda record: record.season,
            )
        )

    raw_pilot = _require_mapping(pilot_source.get("pilot"), "pilot receipts.pilot")
    pilot_feature = by_key.get((PILOT_PLAYER_ID, 2025))
    if pilot_feature is None:
        pilot_name = _require_text(raw_pilot.get("player_name"), "pilot.player_name")
        pilot_eligibility_state = "unavailable_feature_row"
        pilot_eligible = None
        pilot_reason_codes = ["unavailable_feature_row"]
        pilot_market_reason_codes = ["governed_redraft_adp_unavailable"]
        pilot_observation = None
    elif pilot_feature.player_name != PILOT_PLAYER_NAME:
        pilot_name = _require_text(raw_pilot.get("player_name"), "pilot.player_name")
        pilot_eligibility_state = "unresolved_identity"
        pilot_eligible = None
        pilot_reason_codes = ["source_name_conflicts_with_canonical_player_id"]
        pilot_market_reason_codes = ["governed_redraft_adp_unavailable"]
        pilot_observation = None
    else:
        pilot_name = pilot_feature.player_name
        pilot_eligibility = evaluate_feature_eligibility(
            pilot_feature,
            histories[PILOT_PLAYER_ID],
        )
        pilot_eligibility_state = pilot_eligibility.state
        pilot_eligible = pilot_eligibility.football_archetype_eligible
        pilot_reason_codes = list(pilot_eligibility.reason_codes)
        pilot_market_reason_codes = list(pilot_eligibility.market_reason_codes)
        pilot_observation = _record_observation(pilot_feature)
    raw_claims = _require_mapping(
        raw_pilot.get("claim_boundaries"),
        "pilot receipts.pilot.claim_boundaries",
    )
    external_observed = _copy_json_value(raw_claims.get("observed"))
    inferred = _copy_json_value(raw_claims.get("inferred"))
    operator = _copy_json_value(raw_claims.get("operator"))
    forecast = _copy_json_value(raw_claims.get("forecast"))
    unknown = _copy_json_value(raw_claims.get("unknown"))

    comparison_rows: list[dict[str, Any]] = []
    for comparison in _require_list(
        pilot_source.get("comparisons"),
        "pilot receipts.comparisons",
    ):
        source_row = _require_mapping(comparison, "pilot receipts comparison")
        player_id = _require_text(source_row.get("player_id"), "comparison.player_id")
        player_name = _require_text(source_row.get("player_name"), "comparison.player_name")
        feature = by_key.get((player_id, 2025))
        if feature is None:
            comparison_rows.append(
                {
                    "player_id": player_id,
                    "player_name": player_name,
                    "feature_season": 2025,
                    "availability_state": "unavailable_feature_row",
                    "football_archetype_eligible": None,
                    "market_status": "unavailable",
                    "reason_codes": ["unavailable_feature_row"],
                    "observed": None,
                    "external_observation_state": source_row[
                        "external_observation_state"
                    ],
                }
            )
            continue
        if feature.player_name != player_name:
            comparison_rows.append(
                {
                    "player_id": player_id,
                    "player_name": player_name,
                    "feature_season": 2025,
                    "availability_state": "unresolved_identity",
                    "football_archetype_eligible": None,
                    "market_status": "unavailable",
                    "reason_codes": ["source_name_conflicts_with_canonical_player_id"],
                    "observed": None,
                    "external_observation_state": source_row[
                        "external_observation_state"
                    ],
                }
            )
            continue
        eligibility = evaluate_feature_eligibility(feature, histories[player_id])
        comparison_rows.append(
            {
                "player_id": player_id,
                "player_name": player_name,
                "feature_season": feature.season,
                "availability_state": eligibility.state,
                "football_archetype_eligible": (
                    eligibility.football_archetype_eligible
                ),
                "market_status": eligibility.market_status,
                "reason_codes": list(eligibility.reason_codes),
                "observed": _record_observation(feature),
                "external_observation_state": source_row[
                    "external_observation_state"
                ],
            }
        )

    comparison_rows.sort(key=lambda row: str(row["player_id"]))
    return {
        "artifact_id": "late_veteran_wr_breakout_2026_pilot",
        "spec_version": DEFINITION_VERSION,
        "status": "research_watchlist_not_promoted",
        "research_issue": RESEARCH_ISSUE_URL,
        "evidence_cutoff_date": EVIDENCE_CUTOFF_DATE,
        "evidence_cutoff_at": EVIDENCE_CUTOFF_AT,
        "ordering": {
            "semantics": "non_ordinal",
            "rule": "comparison rows are ordered by player_id for deterministic serialization",
        },
        "source_bindings": {
            "player_season_artifact_sha256": player_artifact.receipt.content_sha256,
            "pilot_receipts_sha256": pilot_input_sha256,
        },
        "source_receipts": [
            _copy_json_value(receipt)
            for receipt in _require_list(
                pilot_source.get("receipts"),
                "pilot receipts.receipts",
            )
        ],
        "pilot": {
            "player_id": PILOT_PLAYER_ID,
            "player_name": pilot_name,
            "feature_season": 2025,
            "target_season": 2026,
            "designation": "research_only_pilot",
            "football_archetype_eligibility": {
                "state": pilot_eligibility_state,
                "eligible": pilot_eligible,
                "reason_codes": pilot_reason_codes,
            },
            "market_qualified_eligibility": {
                "state": "unavailable",
                "eligible": None,
                "reason_codes": pilot_market_reason_codes,
            },
            "observed": {
                "governed_historical": pilot_observation,
                "candidate_external_observations": external_observed,
            },
            "inferred": inferred,
            "operator": operator,
            "forecast": forecast,
            "unknown": unknown,
        },
        "comparisons": comparison_rows,
        "claim_boundaries": {
            "external_receipt_status": "candidate_external_observation",
            "future_usage_established": False,
            "forecast_activated": False,
            "market_status_supported": False,
        },
        "non_authorizations": _copy_json_value(pilot_source.get("non_authorizations")),
    }


def _build_receipt_payload(
    *,
    base_output: Path,
    player_artifact: PlayerSeasonCoverageArtifact,
    pilot_source: Mapping[str, Any],
    pilot_input_sha256: str,
    output_paths: Iterable[Path],
) -> dict[str, Any]:
    repository_root = Path(__file__).resolve().parents[2]
    implementation_paths = (
        repository_root / "src/ingestion/tiber_player_season_coverage.py",
        repository_root / "src/labels/late_veteran_wr_breakout.py",
        repository_root / "src/reporting/late_veteran_wr_breakout.py",
    )
    return {
        "artifact_id": "late_veteran_wr_breakout_v0_receipt",
        "spec_version": DEFINITION_VERSION,
        "status": "deterministic_research_run_receipt_not_promoted",
        "research_issue": RESEARCH_ISSUE_URL,
        "repository_base_commit_sha": PINNED_SIGNAL_VALIDATION_BASE_COMMIT_SHA,
        "evidence_cutoff_at": EVIDENCE_CUTOFF_AT,
        "input_bindings": {
            "player_season_coverage": asdict(player_artifact.receipt),
            "pilot_receipts": {
                "logical_source_path": (
                    "data/raw/late_veteran_wr_breakout_2026_pilot_receipts_v0.json"
                ),
                "artifact_id": pilot_source["artifact_id"],
                "spec_version": pilot_source["spec_version"],
                "status": pilot_source["status"],
                "content_sha256": pilot_input_sha256,
            },
        },
        "implementation_bindings": [
            {
                "relative_path": str(path.relative_to(repository_root)),
                "content_sha256": _sha256_path(path),
            }
            for path in implementation_paths
        ],
        "output_bindings": [
            {
                "relative_path": str(path.relative_to(base_output)),
                "content_sha256": _sha256_path(path),
            }
            for path in sorted(output_paths, key=lambda item: str(item.relative_to(base_output)))
        ],
        "run_guards": {
            "live_network_used": False,
            "wall_clock_used": False,
            "output_count_excluding_receipt": len(tuple(output_paths)),
            "receipt_self_hash_excluded": True,
            "forecast_mutated": False,
            "downstream_consumer_mutated": False,
        },
    }


def _historical_pair_row(pair: HistoricalPair) -> dict[str, Any]:
    feature = pair.feature
    outcome = pair.outcome
    return {
        "player_id": feature.player_id,
        "player_name": feature.player_name,
        "feature_season": feature.season,
        "target_season": feature.season + 1,
        "feature_team": feature.primary_team,
        "feature_career_year": feature.career_year,
        "target_career_year": feature.career_year + 1,
        "feature_games_played": feature.games_played,
        "feature_ppr": feature.season_ppr,
        "feature_ppg": feature.season_ppg,
        "feature_targets": feature.targets,
        "feature_receptions": feature.receptions,
        "feature_receiving_yards": feature.receiving_yards,
        "feature_receiving_tds": feature.receiving_tds,
        "feature_target_share": feature.target_share,
        "feature_air_yards_share": feature.air_yards_share,
        "feature_wopr": feature.wopr,
        "eligibility_state": pair.eligibility.state,
        "football_archetype_eligible": pair.eligibility.football_archetype_eligible,
        "market_status": pair.eligibility.market_status,
        "market_qualified_eligible": pair.eligibility.market_qualified_eligible,
        "eligibility_reason_codes": pair.eligibility.reason_codes,
        "market_reason_codes": pair.eligibility.market_reason_codes,
        "outcome_available": outcome is not None,
        "outcome_season": outcome.season if outcome else None,
        "outcome_team": outcome.primary_team if outcome else None,
        "outcome_career_year": outcome.career_year if outcome else None,
        "outcome_games_played": outcome.games_played if outcome else None,
        "outcome_ppr": outcome.season_ppr if outcome else None,
        "outcome_ppg": outcome.season_ppg if outcome else None,
        "outcome_targets": outcome.targets if outcome else None,
        "outcome_receptions": outcome.receptions if outcome else None,
        "outcome_receiving_yards": outcome.receiving_yards if outcome else None,
        "outcome_receiving_tds": outcome.receiving_tds if outcome else None,
        "outcome_target_share": outcome.target_share if outcome else None,
        "outcome_air_yards_share": outcome.air_yards_share if outcome else None,
        "outcome_wopr": outcome.wopr if outcome else None,
        "fantasy_breakout": pair.labels.fantasy_breakout,
        "role_expansion": pair.labels.role_expansion,
        "archetype_hit": pair.labels.archetype_hit,
        "ppg_increase": pair.labels.ppg_increase,
        "target_share_increase": pair.labels.target_share_increase,
        "outcome_reason_codes": pair.labels.reason_codes,
        "evaluation_state": pair.evaluation_state,
        "evaluation_exclusion_reason": pair.evaluation_exclusion_reason,
        "confusion_class": _confusion_class(pair),
    }


def _confusion_class(pair: HistoricalPair) -> str:
    if pair.evaluation_state != "included":
        return "coverage_exclusion"
    predicted = pair.eligibility.football_archetype_eligible
    actual = pair.labels.archetype_hit
    if predicted is True and actual is True:
        return "true_positive"
    if predicted is True and actual is False:
        return "false_positive"
    if predicted is False and actual is True:
        return "false_negative"
    if predicted is False and actual is False:
        return "true_negative"
    raise ValidationError("included historical pair lacks binary prediction/outcome")


def _evaluation_payload(evaluation: PrimaryCohortEvaluation) -> dict[str, Any]:
    payload = asdict(evaluation)
    payload["exclusion_reason_counts"] = dict(evaluation.exclusion_reason_counts)
    payload["uncertainty"] = {
        "method": "wilson_95_percent_interval",
        "precision": _wilson_interval(
            evaluation.true_positives,
            evaluation.prediction_positive_count,
        ),
        "recall": _wilson_interval(
            evaluation.true_positives,
            evaluation.actual_hit_count,
        ),
        "base_rate": _wilson_interval(
            evaluation.actual_hit_count,
            evaluation.evaluable_pair_count,
        ),
    }
    return payload


def _no_leakage_receipt() -> dict[str, Any]:
    signature = inspect.signature(evaluate_feature_eligibility)
    parameter_names = tuple(signature.parameters)
    if "outcome" in parameter_names or "outcome_row" in parameter_names:
        raise ValidationError(
            "feature eligibility interface unexpectedly accepts an outcome parameter"
        )
    return {
        "feature_eligibility_function": (
            "src.labels.late_veteran_wr_breakout.evaluate_feature_eligibility"
        ),
        "accepted_parameters": list(parameter_names),
        "outcome_parameter_accepted": False,
        "feature_decision_built_before_outcome_join": True,
        "outcome_labels_stored_separately": True,
    }


def _sensitivity_payload(diagnostic: Any) -> dict[str, Any]:
    return {
        "feature_ppg_ceiling": diagnostic.feature_ppg_ceiling,
        "feature_target_share_ceiling": diagnostic.feature_target_share_ceiling,
        "outcome_ppg_floor": diagnostic.outcome_ppg_floor,
        "target_share_increase_floor": diagnostic.target_share_increase_floor,
        "diagnostic_only": True,
        "market_status": diagnostic.market_status,
        "evaluation": _evaluation_payload(diagnostic.evaluation),
    }


def _population_by_feature_season(
    pairs: Iterable[HistoricalPair],
) -> dict[str, dict[str, Any]]:
    by_season: dict[int, list[HistoricalPair]] = defaultdict(list)
    for pair in pairs:
        by_season[pair.feature.season].append(pair)
    result: dict[str, dict[str, Any]] = {}
    for season, season_pairs in sorted(by_season.items()):
        exclusion_counts = Counter(
            pair.evaluation_exclusion_reason
            for pair in season_pairs
            if pair.evaluation_exclusion_reason is not None
        )
        result[str(season)] = {
            "observed_pair_count": len(season_pairs),
            "included_count": sum(
                pair.evaluation_state == "included" for pair in season_pairs
            ),
            "coverage_exclusion_count": sum(
                pair.evaluation_state == "coverage_exclusion" for pair in season_pairs
            ),
            "eligibility_state_counts": dict(
                sorted(Counter(pair.eligibility.state for pair in season_pairs).items())
            ),
            "exclusion_reason_counts": dict(sorted(exclusion_counts.items())),
        }
    return result


def _missingness_payload(
    records: Iterable[PlayerSeasonRecord],
    pairs: Iterable[HistoricalPair],
) -> dict[str, Any]:
    rows = tuple(records)
    pair_rows = tuple(pairs)
    required_fields = {
        "player_id": sum(not record.player_id for record in rows),
        "player_name": sum(not record.player_name for record in rows),
        "primary_team": sum(not record.primary_team for record in rows),
        "season": 0,
        "rookie_year": 0,
        "career_year": 0,
        "games_played": 0,
        "season_ppr": sum(not math.isfinite(record.season_ppr) for record in rows),
        "season_ppg": sum(not math.isfinite(record.season_ppg) for record in rows),
        "targets": 0,
        "receptions": 0,
        "receiving_yards": sum(
            not math.isfinite(record.receiving_yards) for record in rows
        ),
        "receiving_tds": 0,
        "target_share": sum(not math.isfinite(record.target_share) for record in rows),
        "air_yards_share": sum(
            not math.isfinite(record.air_yards_share) for record in rows
        ),
        "wopr": sum(not math.isfinite(record.wopr) for record in rows),
    }
    return {
        "required_player_season_fields": required_fields,
        "optional_role_fields": {
            "routes_run": sum(record.routes_run is None for record in rows),
            "route_participation": sum(
                record.route_participation is None for record in rows
            ),
            "snap_share": sum(record.snap_share is None for record in rows),
        },
        "unsupported_context_fields": {
            "age": "unavailable_no_source_backed_field_bound",
            "current_active_roster_status": "unavailable_historical_stat_rows_are_not_roster_truth",
            "current_official_depth_chart": "unavailable_no_governed_receipt_bound",
        },
        "pair_level": {
            "missing_adjacent_outcome_row": sum(pair.outcome is None for pair in pair_rows),
            "prior_history_incomplete": sum(
                pair.eligibility.state == "prior_history_incomplete" for pair in pair_rows
            ),
            "tenure_conflict": sum(
                pair.eligibility.state == "tenure_conflict"
                or pair.labels.state == "tenure_conflict"
                for pair in pair_rows
            ),
            "market_evidence_unavailable": len(pair_rows),
        },
    }


def _feature_comparison_payload(pairs: Iterable[HistoricalPair]) -> dict[str, Any]:
    evaluable = tuple(pair for pair in pairs if pair.evaluation_state == "included")
    ppg_only = tuple(
        pair
        for pair in evaluable
        if pair.feature.season_ppg < LATE_VETERAN_WR_BREAKOUT_V0.feature_ppg_ceiling
        and "prior_established_ppg" not in pair.eligibility.reason_codes
        and "prior_established_target_share" not in pair.eligibility.reason_codes
    )
    ppg_and_share = tuple(
        pair
        for pair in ppg_only
        if pair.feature.target_share
        < LATE_VETERAN_WR_BREAKOUT_V0.feature_target_share_ceiling
    )
    return {
        "purpose": (
            "Descriptive check of whether adding feature target-share concentration "
            "changes outcomes relative to the same prior-history-safe PPG screen."
        ),
        "ppg_only": _outcome_rates(ppg_only),
        "ppg_plus_feature_target_share": _outcome_rates(ppg_and_share),
        "causal_or_predictive_claim": False,
    }


def _outcome_rates(pairs: tuple[HistoricalPair, ...]) -> dict[str, Any]:
    count = len(pairs)
    fantasy = sum(pair.labels.fantasy_breakout is True for pair in pairs)
    role = sum(pair.labels.role_expansion == "confirmed" for pair in pairs)
    hits = sum(pair.labels.archetype_hit is True for pair in pairs)
    return {
        "row_count": count,
        "fantasy_breakout_count": fantasy,
        "fantasy_breakout_rate": _safe_ratio(fantasy, count),
        "role_expansion_count": role,
        "role_expansion_rate": _safe_ratio(role, count),
        "archetype_hit_count": hits,
        "archetype_hit_rate": _safe_ratio(hits, count),
    }


def _build_examples_markdown(pairs: Iterable[HistoricalPair]) -> str:
    all_pairs = tuple(pairs)
    controls: list[HistoricalPair] = []
    for player_id, feature_season in ((POSITIVE_CONTROL_IDS[0], 2023), (POSITIVE_CONTROL_IDS[1], 2024)):
        match = next(
            (
                pair
                for pair in all_pairs
                if pair.feature.player_id == player_id
                and pair.feature.season == feature_season
            ),
            None,
        )
        if match is not None:
            controls.append(match)

    negative_pool = [
        pair
        for pair in all_pairs
        if pair.evaluation_state == "included"
        and pair.eligibility.football_archetype_eligible is True
        and pair.labels.archetype_hit is False
    ]
    negative_pool.sort(key=_negative_control_sort_key)
    negatives = negative_pool[:2]

    lines = [
        "# Late-veteran WR breakout v0 examples",
        "",
        "These are research traces from the pinned observed-row population. They are not rankings or recommendations.",
        "",
        "## Positive controls",
        "",
        _examples_table(controls),
        "",
        (
            "Jauan Jennings remains provisional because the promoted input begins in 2021 while his source-backed rookie year is 2020. Parker Washington has complete rookie-to-feature exposure in the pinned window."
            if len(controls) == 2
            else "One or more declared positive-control traces are unavailable in this input."
        ),
        "",
        "## Reproducibly selected negative controls",
        "",
        "Selection rule: primary-eligible non-hits, ordered by the fewest failed outcome components, normalized threshold shortfall, feature season, then player ID.",
        "",
        _examples_table(negatives),
        "",
        (
            "Two reproducible negative controls were available."
            if len(negatives) == 2
            else f"Only {len(negatives)} reproducible negative-control trace(s) were available."
        ),
        "",
        "## Interpretation boundary",
        "",
        "Outcome information is used only to label and select retrospective examples; it never changes feature-side eligibility.",
        "",
    ]
    return "\n".join(lines)


def _negative_control_sort_key(pair: HistoricalPair) -> tuple[Any, ...]:
    failed_components = int(pair.labels.fantasy_breakout is not True) + int(
        pair.labels.role_expansion != "confirmed"
    )
    outcome = pair.outcome
    if outcome is None:
        return (99, math.inf, pair.feature.season, pair.feature.player_id)
    definition = LATE_VETERAN_WR_BREAKOUT_V0
    shortfall = (
        max(0.0, definition.outcome_ppg_floor - outcome.season_ppg)
        + max(0.0, definition.outcome_ppg_increase_floor - (pair.labels.ppg_increase or 0.0))
        + 20.0 * max(0.0, definition.outcome_target_share_floor - outcome.target_share)
        + 20.0
        * max(
            0.0,
            definition.target_share_increase_floor
            - (pair.labels.target_share_increase or 0.0),
        )
    )
    return (failed_components, round(shortfall, 6), pair.feature.season, pair.feature.player_id)


def _examples_table(pairs: Iterable[HistoricalPair]) -> str:
    lines = [
        "| Player | Pair | Feature PPG | Feature target share | Outcome PPG | Outcome target share | Eligibility | Fantasy breakout | Role expansion | Archetype hit |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |",
    ]
    for pair in pairs:
        outcome_ppg = "n/a" if pair.outcome is None else f"{pair.outcome.season_ppg:.2f}"
        outcome_share = "n/a" if pair.outcome is None else f"{pair.outcome.target_share:.4f}"
        lines.append(
            "| {name} | {feature}→{outcome} | {feature_ppg:.2f} | {feature_share:.4f} | {outcome_ppg} | {outcome_share} | {eligibility} | {fantasy} | {role} | {hit} |".format(
                name=pair.feature.player_name,
                feature=pair.feature.season,
                outcome=pair.feature.season + 1,
                feature_ppg=pair.feature.season_ppg,
                feature_share=pair.feature.target_share,
                outcome_ppg=outcome_ppg,
                outcome_share=outcome_share,
                eligibility=pair.eligibility.state,
                fantasy=_display_optional_bool(pair.labels.fantasy_breakout),
                role=pair.labels.role_expansion,
                hit=_display_optional_bool(pair.labels.archetype_hit),
            )
        )
    return "\n".join(lines)


def _record_observation(record: PlayerSeasonRecord) -> dict[str, Any]:
    return {
        "source_state": "promoted_governed_player_season_evidence",
        "team_of_record": record.primary_team,
        "season": record.season,
        "career_year": record.career_year,
        "games_played": record.games_played,
        "season_ppr": record.season_ppr,
        "season_ppg": record.season_ppg,
        "targets": record.targets,
        "receptions": record.receptions,
        "receiving_yards": record.receiving_yards,
        "receiving_tds": record.receiving_tds,
        "target_share": record.target_share,
        "air_yards_share": record.air_yards_share,
        "wopr": record.wopr,
        "routes_run": record.routes_run,
        "route_participation": record.route_participation,
        "snap_share": record.snap_share,
        "missing_fields": list(record.missing_fields),
    }


def _terminal_decision(
    evaluation: PrimaryCohortEvaluation,
    historical_run_blockers: tuple[str, ...],
) -> TerminalDecision:
    if historical_run_blockers:
        decision: TerminalDecision = "late_veteran_wr_breakout_v0_blocked"
    elif evaluation.market_status == "unavailable" or evaluation.small_sample_warning:
        decision = "late_veteran_wr_breakout_v0_requires_data_or_definition_followup"
    else:
        decision = "late_veteran_wr_breakout_v0_research_validated"
    if decision not in TERMINAL_DECISIONS:
        raise ValidationError(f"unsupported terminal decision: {decision}")
    return decision


def _terminal_decision_basis(
    evaluation: PrimaryCohortEvaluation,
    records: Iterable[PlayerSeasonRecord],
    historical_run_blockers: tuple[str, ...],
) -> list[str]:
    rows = tuple(records)
    reasons: list[str] = []
    reasons.extend(historical_run_blockers)
    if evaluation.evaluable_pair_count == 0:
        reasons.append("no_evaluable_historical_pairs")
    if evaluation.market_status == "unavailable":
        reasons.append("governed_comparable_redraft_market_unavailable")
    if all(
        record.routes_run is None
        and record.route_participation is None
        and record.snap_share is None
        for record in rows
    ):
        reasons.append("route_and_snap_role_fields_have_zero_coverage")
    if evaluation.prediction_positive_count > 0:
        reasons.append(
            "primary_result_is_descriptive_only_"
            f"{evaluation.true_positives}_of_"
            f"{evaluation.prediction_positive_count}_screen_positives_were_hits"
        )
    return reasons


def _historical_run_blockers(
    pairs: tuple[HistoricalPair, ...],
    evaluation: PrimaryCohortEvaluation,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not pairs:
        blockers.append("historical_pair_population_empty")
    valid_2024_to_2025 = [
        pair
        for pair in pairs
        if pair.feature.season == 2024
        and pair.outcome is not None
        and pair.outcome.season == 2025
        and pair.labels.state == "valid"
    ]
    if not valid_2024_to_2025:
        blockers.append("no_valid_2024_to_2025_outcome_seam")
    if evaluation.evaluable_pair_count == 0:
        blockers.append("zero_evaluable_historical_pairs")
    return tuple(blockers)


def _read_and_validate_pilot_receipts(
    path: Path,
    *,
    expected_sha256: str = PINNED_PILOT_RECEIPTS_SHA256,
) -> tuple[dict[str, Any], str]:
    if not path.exists() or not path.is_file():
        raise ValidationError(f"pilot receipt input does not exist or is not a file: {path}")
    raw_bytes = path.read_bytes()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    if digest != expected_sha256:
        raise ValidationError(
            "pilot receipt input digest mismatch: "
            f"expected {expected_sha256}, got {digest}"
        )
    try:
        payload = json.loads(
            raw_bytes.decode("utf-8"),
            parse_constant=_reject_non_finite_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValidationError("pilot receipt input is not valid finite-value JSON") from exc
    root = dict(_require_mapping(payload, "pilot receipts"))
    _require_exact(root, "artifact_id", "late_veteran_wr_breakout_2026_pilot_receipts_v0")
    _require_exact(root, "spec_version", "late_veteran_wr_breakout_2026_pilot_receipts_v0")
    _require_exact(root, "status", "candidate_external_observations_not_promoted")
    _require_exact(root, "evidence_cutoff_date", EVIDENCE_CUTOFF_DATE)
    _require_exact(root, "evidence_cutoff_at", EVIDENCE_CUTOFF_AT)

    research_issue = _require_mapping(root.get("research_issue"), "pilot receipts.research_issue")
    if research_issue.get("issue_number") != 16 or research_issue.get("url") != RESEARCH_ISSUE_URL:
        raise ValidationError("pilot receipt input is not bound to Signal-Validation-Model issue 16")

    pilot = _require_mapping(root.get("pilot"), "pilot receipts.pilot")
    _require_exact(pilot, "player_id", PILOT_PLAYER_ID)
    _require_exact(pilot, "player_name", PILOT_PLAYER_NAME)
    if pilot.get("ordinal_rank") is not None:
        raise ValidationError("pilot receipt input must not assign an ordinal position")

    comparisons = _require_list(root.get("comparisons"), "pilot receipts.comparisons")
    comparison_ids: set[str] = set()
    for index, value in enumerate(comparisons):
        comparison = _require_mapping(value, f"pilot receipts.comparisons[{index}]")
        player_id = _require_text(comparison.get("player_id"), "comparison.player_id")
        if player_id in comparison_ids:
            raise ValidationError(f"duplicate comparison player_id: {player_id}")
        comparison_ids.add(player_id)
        if comparison.get("ordinal_rank") is not None:
            raise ValidationError("comparison receipt must not assign an ordinal position")
        _require_text(
            comparison.get("external_observation_state"),
            "comparison.external_observation_state",
        )
    if comparison_ids != DECLARED_COMPARISON_IDS:
        raise ValidationError(
            "pilot comparison population does not match the issue-16 declaration"
        )

    receipts = _require_list(root.get("receipts"), "pilot receipts.receipts")
    receipt_ids: set[str] = set()
    cutoff = _parse_datetime(EVIDENCE_CUTOFF_AT)
    for index, value in enumerate(receipts):
        receipt = _require_mapping(value, f"pilot receipts.receipts[{index}]")
        receipt_id = _require_text(receipt.get("receipt_id"), "receipt.receipt_id")
        if receipt_id in receipt_ids:
            raise ValidationError(f"duplicate pilot receipt_id: {receipt_id}")
        receipt_ids.add(receipt_id)
        _require_exact(receipt, "player_id", PILOT_PLAYER_ID)
        _require_exact(receipt, "source_type", "official_team_editorial")
        _require_exact(receipt, "evidence_status", "candidate_external_observation")
        _require_exact(receipt, "included_under_cutoff", EVIDENCE_CUTOFF_AT)
        source_url = _require_text(receipt.get("url"), "receipt.url")
        parsed_url = urlparse(source_url)
        if parsed_url.scheme != "https" or parsed_url.netloc != "www.baltimoreravens.com":
            raise ValidationError("pilot receipt URL must be an official HTTPS Ravens source")
        published_at = _parse_datetime(
            _require_text(receipt.get("published_at"), "receipt.published_at")
        )
        if published_at > cutoff:
            raise ValidationError(f"pilot receipt {receipt_id} exceeds the evidence cutoff")
        claims = _require_list(receipt.get("paraphrased_claims"), "receipt.paraphrased_claims")
        if not claims:
            raise ValidationError(f"pilot receipt {receipt_id} has no paraphrased claims")

    claims = _require_mapping(pilot.get("claim_boundaries"), "pilot.claim_boundaries")
    referenced_ids: set[str] = set()
    observed_claim_ids: set[str] = set()
    for observed in _require_list(claims.get("observed"), "pilot.claim_boundaries.observed"):
        observed_mapping = _require_mapping(observed, "pilot observed claim")
        claim_id = _require_text(observed_mapping.get("claim_id"), "observed.claim_id")
        if claim_id in observed_claim_ids:
            raise ValidationError(f"duplicate pilot observed claim_id: {claim_id}")
        observed_claim_ids.add(claim_id)
        referenced_ids.update(
            _require_text(value, "observed receipt_id")
            for value in _require_list(observed_mapping.get("receipt_ids"), "observed.receipt_ids")
        )
    if not referenced_ids or not referenced_ids <= receipt_ids:
        raise ValidationError("pilot observed claims reference unknown or no receipts")
    for inferred in _require_list(claims.get("inferred"), "pilot.claim_boundaries.inferred"):
        inferred_mapping = _require_mapping(inferred, "pilot inferred claim")
        basis_claim_ids = {
            _require_text(value, "inferred basis observed claim_id")
            for value in _require_list(
                inferred_mapping.get("basis_observed_claim_ids"),
                "inferred.basis_observed_claim_ids",
            )
        }
        if not basis_claim_ids or not basis_claim_ids <= observed_claim_ids:
            raise ValidationError(
                "pilot inferred claims must reference known observed claim IDs"
            )
    forecast = _require_mapping(claims.get("forecast"), "pilot.claim_boundaries.forecast")
    if forecast.get("state") != "not_activated" or forecast.get("claims") != []:
        raise ValidationError("pilot Forecast boundary must remain not_activated with no claims")

    _require_list(root.get("non_authorizations"), "pilot receipts.non_authorizations")
    return root, digest


def _assert_no_forbidden_output_keys(value: Any, label: str) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            key_tokens = set(str(key).lower().split("_"))
            if key_tokens & {"rank", "ranking", "score", "winner", "recommendation"}:
                raise ValidationError(f"{label} contains forbidden output key: {key}")
            _assert_no_forbidden_output_keys(nested, label)
    elif isinstance(value, list):
        for nested in value:
            _assert_no_forbidden_output_keys(nested, label)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _write_csv(
    path: Path,
    fieldnames: list[str],
    rows: Iterable[Mapping[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            if set(row) != set(fieldnames):
                raise ValidationError("historical pair row does not match the fixed CSV schema")
            writer.writerow({field: _serialize_csv(row.get(field)) for field in fieldnames})


def _serialize_csv(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, tuple):
        return "|".join(str(item) for item in value)
    return value


def _copy_json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=False))


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else round(numerator / denominator, 4)


def _wilson_interval(successes: int, observations: int) -> dict[str, float] | None:
    if observations <= 0:
        return None
    z = 1.96
    proportion = successes / observations
    denominator = 1.0 + (z * z / observations)
    center = (proportion + z * z / (2.0 * observations)) / denominator
    margin = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / observations
            + z * z / (4.0 * observations * observations)
        )
        / denominator
    )
    return {
        "lower": round(max(0.0, center - margin), 4),
        "upper": round(min(1.0, center + margin), 4),
    }


def _display_optional_bool(value: bool | None) -> str:
    return "unavailable" if value is None else ("true" if value else "false")


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"invalid evidence timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise ValidationError(f"evidence timestamp must include a timezone: {value}")
    return parsed.astimezone(timezone.utc)


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be a list")
    return value


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value.strip()


def _require_exact(mapping: Mapping[str, Any], key: str, expected: str) -> str:
    value = _require_text(mapping.get(key), key)
    if value != expected:
        raise ValidationError(f"{key} must equal {expected!r}, got {value!r}")
    return value


def _reject_non_finite_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is not allowed: {value}")


__all__ = [
    "EVIDENCE_CUTOFF_AT",
    "EVIDENCE_CUTOFF_DATE",
    "LateVeteranWrBreakoutArtifacts",
    "TerminalDecision",
    "build_late_veteran_wr_breakout_v0",
]
