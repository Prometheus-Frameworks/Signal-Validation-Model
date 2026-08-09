"""Leakage-safe definition and labels for the late-veteran WR breakout v0 cohort.

This module intentionally contains no ranking or scoring surface.  It treats the
feature-season screen, outcome-season labels, and diagnostic sensitivity runs as
separate deterministic operations over source-backed player-season records.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from itertools import product
import math
from typing import Iterable, Literal

from src.ingestion import PlayerSeasonRecord
from src.validation import ValidationError


EligibilityState = Literal[
    "eligible",
    "ineligible",
    "outside_declared_population",
    "prior_history_incomplete",
    "tenure_conflict",
    "unavailable_feature_fields",
]
RoleExpansionState = Literal["confirmed", "not_confirmed", "unavailable"]
OutcomeState = Literal["valid", "unavailable", "tenure_conflict"]
EvaluationState = Literal["included", "coverage_exclusion"]


@dataclass(frozen=True)
class LateVeteranWrBreakoutDefinition:
    """Immutable preregistered thresholds for one cohort definition."""

    version: str
    position: str
    minimum_feature_career_year: int
    minimum_target_career_year: int
    feature_ppg_ceiling: float
    feature_target_share_ceiling: float
    prior_established_ppg_floor: float
    prior_established_target_share_floor: float
    outcome_games_floor: int
    outcome_ppg_floor: float
    outcome_ppg_increase_floor: float
    outcome_target_share_floor: float
    target_share_increase_floor: float
    market_adp_cutoff: int
    feature_ppg_sensitivity: tuple[float, ...]
    feature_target_share_sensitivity: tuple[float, ...]
    outcome_ppg_sensitivity: tuple[float, ...]
    target_share_increase_sensitivity: tuple[float, ...]
    market_adp_sensitivity: tuple[int, ...]
    market_unranked_sensitivity_declared: bool


LATE_VETERAN_WR_BREAKOUT_V0 = LateVeteranWrBreakoutDefinition(
    version="late_veteran_wr_breakout_v0",
    position="WR",
    minimum_feature_career_year=2,
    minimum_target_career_year=3,
    feature_ppg_ceiling=7.0,
    feature_target_share_ceiling=0.10,
    prior_established_ppg_floor=10.0,
    prior_established_target_share_floor=0.15,
    outcome_games_floor=8,
    outcome_ppg_floor=10.0,
    outcome_ppg_increase_floor=3.0,
    outcome_target_share_floor=0.15,
    target_share_increase_floor=0.05,
    market_adp_cutoff=200,
    feature_ppg_sensitivity=(5.0, 7.0, 9.0),
    feature_target_share_sensitivity=(0.08, 0.10, 0.12),
    outcome_ppg_sensitivity=(10.0, 12.0),
    target_share_increase_sensitivity=(0.04, 0.05, 0.06, 0.08),
    market_adp_sensitivity=(180, 200, 240),
    market_unranked_sensitivity_declared=True,
)


@dataclass(frozen=True)
class FeatureEligibility:
    """Feature-only cohort decision; no outcome field is accepted or inspected."""

    player_id: str
    feature_season: int
    target_season: int
    feature_career_year: int
    target_career_year: int
    state: EligibilityState
    football_archetype_eligible: bool | None
    market_status: Literal["unavailable"]
    market_qualified_eligible: None
    reason_codes: tuple[str, ...]
    market_reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class OutcomeLabels:
    """Independent next-season fantasy and role-expansion labels."""

    player_id: str
    feature_season: int
    outcome_season: int
    state: OutcomeState
    fantasy_breakout: bool | None
    role_expansion: RoleExpansionState
    archetype_hit: bool | None
    ppg_increase: float | None
    target_share_increase: float | None
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class HistoricalPair:
    """One observed feature row joined to its adjacent observed outcome row."""

    feature: PlayerSeasonRecord
    outcome: PlayerSeasonRecord | None
    eligibility: FeatureEligibility
    labels: OutcomeLabels
    evaluation_state: EvaluationState
    evaluation_exclusion_reason: str | None


@dataclass(frozen=True)
class PrimaryCohortEvaluation:
    """Confusion counts for the declared observed-row universe."""

    definition_version: str
    declared_universe: str
    observed_pair_count: int
    evaluable_pair_count: int
    coverage_exclusion_count: int
    prediction_positive_count: int
    actual_hit_count: int
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: float | None
    recall: float | None
    base_rate: float | None
    market_status: Literal["unavailable"]
    exclusion_reason_counts: tuple[tuple[str, int], ...]
    small_sample_warning: str | None


@dataclass(frozen=True)
class SensitivityDiagnostic:
    """One diagnostic-only threshold combination; never a selected recipe."""

    feature_ppg_ceiling: float
    feature_target_share_ceiling: float
    outcome_ppg_floor: float
    target_share_increase_floor: float
    diagnostic_only: Literal[True]
    market_status: Literal["unavailable"]
    evaluation: PrimaryCohortEvaluation


DECLARED_OBSERVED_ROW_UNIVERSE = (
    "pinned observed WR player-season/stat-row population with source-backed "
    "Y3+ target tenure, complete rookie-to-feature exposure, valid required "
    "feature fields, and valid adjacent-season outcome fields"
)


def evaluate_feature_eligibility(
    feature: PlayerSeasonRecord,
    player_history: Iterable[PlayerSeasonRecord],
    *,
    definition: LateVeteranWrBreakoutDefinition = LATE_VETERAN_WR_BREAKOUT_V0,
) -> FeatureEligibility:
    """Apply only feature-season and prior-history rules.

    Market evidence is deliberately unavailable in v0.  Its absence neither
    qualifies nor disqualifies the football-only cohort.
    """

    target_season = feature.season + 1
    target_career_year = feature.career_year + 1
    market_reasons = ("governed_redraft_adp_unavailable",)

    def result(
        state: EligibilityState,
        eligible: bool | None,
        reasons: Iterable[str],
    ) -> FeatureEligibility:
        return FeatureEligibility(
            player_id=feature.player_id,
            feature_season=feature.season,
            target_season=target_season,
            feature_career_year=feature.career_year,
            target_career_year=target_career_year,
            state=state,
            football_archetype_eligible=eligible,
            market_status="unavailable",
            market_qualified_eligible=None,
            reason_codes=tuple(sorted(set(reasons))),
            market_reason_codes=market_reasons,
        )

    if feature.position != definition.position or feature.season_type != "REG":
        return result("outside_declared_population", None, ("outside_declared_population",))

    if feature.career_year < definition.minimum_feature_career_year:
        return result(
            "outside_declared_population",
            None,
            ("feature_career_year_below_minimum",),
        )
    if target_career_year < definition.minimum_target_career_year:
        return result(
            "outside_declared_population",
            None,
            ("target_career_year_below_minimum",),
        )

    if feature.career_year != feature.season - feature.rookie_year + 1:
        return result("tenure_conflict", None, ("feature_tenure_conflict",))

    history_state, ordered_history = _complete_history_through_feature(feature, player_history)
    if history_state == "tenure_conflict":
        return result("tenure_conflict", None, ("prior_history_tenure_conflict",))
    if history_state == "prior_history_incomplete":
        return result(
            "prior_history_incomplete",
            None,
            ("prior_history_incomplete",),
        )

    if not _is_finite_number(feature.season_ppg) or not _is_share(feature.target_share):
        return result(
            "unavailable_feature_fields",
            None,
            ("feature_ppg_or_target_share_unavailable",),
        )

    prior_records = tuple(record for record in ordered_history if record.season < feature.season)
    if any(
        not _is_finite_number(record.season_ppg) or not _is_share(record.target_share)
        for record in prior_records
    ):
        return result(
            "prior_history_incomplete",
            None,
            ("prior_history_required_fields_unavailable",),
        )

    reasons: list[str] = []
    if any(
        float(record.season_ppg) >= definition.prior_established_ppg_floor
        for record in prior_records
    ):
        reasons.append("prior_established_ppg")
    if any(
        float(record.target_share) >= definition.prior_established_target_share_floor
        for record in prior_records
    ):
        reasons.append("prior_established_target_share")
    if float(feature.season_ppg) >= definition.feature_ppg_ceiling:
        reasons.append("feature_ppg_at_or_above_ceiling")
    if float(feature.target_share) >= definition.feature_target_share_ceiling:
        reasons.append("feature_target_share_at_or_above_ceiling")

    if reasons:
        return result("ineligible", False, reasons)
    return result("eligible", True, ("football_archetype_eligible",))


def build_outcome_labels(
    feature: PlayerSeasonRecord,
    outcome: PlayerSeasonRecord | None,
    *,
    definition: LateVeteranWrBreakoutDefinition = LATE_VETERAN_WR_BREAKOUT_V0,
) -> OutcomeLabels:
    """Compute fantasy breakout and role expansion without changing eligibility."""

    expected_outcome_season = feature.season + 1
    if outcome is None:
        return OutcomeLabels(
            player_id=feature.player_id,
            feature_season=feature.season,
            outcome_season=expected_outcome_season,
            state="unavailable",
            fantasy_breakout=None,
            role_expansion="unavailable",
            archetype_hit=None,
            ppg_increase=None,
            target_share_increase=None,
            reason_codes=("missing_outcome_row",),
        )

    if (
        outcome.player_id != feature.player_id
        or outcome.position != definition.position
        or outcome.season_type != "REG"
        or outcome.season != expected_outcome_season
        or outcome.rookie_year != feature.rookie_year
        or outcome.career_year != feature.career_year + 1
        or outcome.career_year != outcome.season - outcome.rookie_year + 1
    ):
        return OutcomeLabels(
            player_id=feature.player_id,
            feature_season=feature.season,
            outcome_season=expected_outcome_season,
            state="tenure_conflict",
            fantasy_breakout=None,
            role_expansion="unavailable",
            archetype_hit=None,
            ppg_increase=None,
            target_share_increase=None,
            reason_codes=("outcome_identity_or_tenure_conflict",),
        )

    fantasy_available = (
        isinstance(outcome.games_played, int)
        and not isinstance(outcome.games_played, bool)
        and outcome.games_played >= 0
        and _is_finite_number(feature.season_ppg)
        and _is_finite_number(outcome.season_ppg)
    )
    ppg_increase = (
        round(float(outcome.season_ppg) - float(feature.season_ppg), 10)
        if fantasy_available
        else None
    )
    fantasy_breakout = (
        bool(
            outcome.games_played >= definition.outcome_games_floor
            and float(outcome.season_ppg) >= definition.outcome_ppg_floor
            and ppg_increase is not None
            and ppg_increase >= definition.outcome_ppg_increase_floor
        )
        if fantasy_available
        else None
    )

    role_available = _is_share(feature.target_share) and _is_share(outcome.target_share)
    target_share_increase = (
        round(float(outcome.target_share) - float(feature.target_share), 10)
        if role_available
        else None
    )
    if not role_available:
        role_expansion: RoleExpansionState = "unavailable"
    elif (
        float(outcome.target_share) >= definition.outcome_target_share_floor
        and target_share_increase is not None
        and target_share_increase >= definition.target_share_increase_floor
    ):
        role_expansion = "confirmed"
    else:
        role_expansion = "not_confirmed"

    if fantasy_breakout is None or role_expansion == "unavailable":
        archetype_hit = None
    else:
        archetype_hit = bool(fantasy_breakout and role_expansion == "confirmed")

    reasons: list[str] = []
    if fantasy_breakout is None:
        reasons.append("fantasy_outcome_fields_unavailable")
    elif fantasy_breakout:
        reasons.append("fantasy_breakout_confirmed")
    else:
        reasons.append("fantasy_breakout_not_confirmed")
    if role_expansion == "unavailable":
        reasons.append("role_target_share_unavailable")
    elif role_expansion == "confirmed":
        reasons.append("role_expansion_confirmed")
    else:
        reasons.append("role_expansion_not_confirmed")

    state: OutcomeState = (
        "valid" if fantasy_breakout is not None and role_expansion != "unavailable" else "unavailable"
    )
    return OutcomeLabels(
        player_id=feature.player_id,
        feature_season=feature.season,
        outcome_season=expected_outcome_season,
        state=state,
        fantasy_breakout=fantasy_breakout,
        role_expansion=role_expansion,
        archetype_hit=archetype_hit,
        ppg_increase=_round_optional(ppg_increase),
        target_share_increase=_round_optional(target_share_increase),
        reason_codes=tuple(reasons),
    )


def build_historical_pairs(
    records: Iterable[PlayerSeasonRecord],
    *,
    definition: LateVeteranWrBreakoutDefinition = LATE_VETERAN_WR_BREAKOUT_V0,
) -> tuple[HistoricalPair, ...]:
    """Join adjacent observed WR seasons and retain unavailable outcomes."""

    wr_records = sorted(
        (
            record
            for record in records
            if record.position == definition.position and record.season_type == "REG"
        ),
        key=lambda record: (record.player_id, record.season),
    )
    records_by_key: dict[tuple[str, int], PlayerSeasonRecord] = {}
    histories: dict[str, list[PlayerSeasonRecord]] = {}
    for record in wr_records:
        key = (record.player_id, record.season)
        if key in records_by_key:
            raise ValidationError(f"duplicate observed WR player-season key: {key}")
        records_by_key[key] = record
        histories.setdefault(record.player_id, []).append(record)

    pairs: list[HistoricalPair] = []
    for feature in wr_records:
        history = tuple(
            record for record in histories[feature.player_id] if record.season <= feature.season
        )
        eligibility = evaluate_feature_eligibility(
            feature,
            history,
            definition=definition,
        )
        outcome = records_by_key.get((feature.player_id, feature.season + 1))
        labels = build_outcome_labels(feature, outcome, definition=definition)
        exclusion_reason = _evaluation_exclusion_reason(eligibility, labels)
        pairs.append(
            HistoricalPair(
                feature=feature,
                outcome=outcome,
                eligibility=eligibility,
                labels=labels,
                evaluation_state=("included" if exclusion_reason is None else "coverage_exclusion"),
                evaluation_exclusion_reason=exclusion_reason,
            )
        )

    return tuple(sorted(pairs, key=lambda pair: (pair.feature.season, pair.feature.player_id)))


def evaluate_primary_cohort(
    pairs: Iterable[HistoricalPair],
    *,
    definition: LateVeteranWrBreakoutDefinition = LATE_VETERAN_WR_BREAKOUT_V0,
) -> PrimaryCohortEvaluation:
    """Evaluate the primary football-only cohort over its declared universe."""

    rows = tuple(pairs)
    evaluable = tuple(pair for pair in rows if pair.evaluation_state == "included")
    exclusions = Counter(
        pair.evaluation_exclusion_reason or "unspecified_coverage_exclusion"
        for pair in rows
        if pair.evaluation_state == "coverage_exclusion"
    )

    true_positives = sum(
        1
        for pair in evaluable
        if pair.eligibility.football_archetype_eligible is True
        and pair.labels.archetype_hit is True
    )
    false_positives = sum(
        1
        for pair in evaluable
        if pair.eligibility.football_archetype_eligible is True
        and pair.labels.archetype_hit is False
    )
    false_negatives = sum(
        1
        for pair in evaluable
        if pair.eligibility.football_archetype_eligible is False
        and pair.labels.archetype_hit is True
    )
    true_negatives = sum(
        1
        for pair in evaluable
        if pair.eligibility.football_archetype_eligible is False
        and pair.labels.archetype_hit is False
    )
    prediction_positive_count = true_positives + false_positives
    actual_hit_count = true_positives + false_negatives

    return PrimaryCohortEvaluation(
        definition_version=definition.version,
        declared_universe=DECLARED_OBSERVED_ROW_UNIVERSE,
        observed_pair_count=len(rows),
        evaluable_pair_count=len(evaluable),
        coverage_exclusion_count=len(rows) - len(evaluable),
        prediction_positive_count=prediction_positive_count,
        actual_hit_count=actual_hit_count,
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        true_negatives=true_negatives,
        precision=_safe_ratio(true_positives, prediction_positive_count),
        recall=_safe_ratio(true_positives, actual_hit_count),
        base_rate=_safe_ratio(actual_hit_count, len(evaluable)),
        market_status="unavailable",
        exclusion_reason_counts=tuple(sorted(exclusions.items())),
        small_sample_warning=(
            "supported evaluable sample is below 30; do not make predictive-power claims"
            if len(evaluable) < 30
            else None
        ),
    )


def build_diagnostic_sensitivity_grid(
    records: Iterable[PlayerSeasonRecord],
    *,
    definition: LateVeteranWrBreakoutDefinition = LATE_VETERAN_WR_BREAKOUT_V0,
) -> tuple[SensitivityDiagnostic, ...]:
    """Run the preregistered diagnostic grid without choosing a winner."""

    frozen_records = tuple(records)
    diagnostics: list[SensitivityDiagnostic] = []
    for feature_ppg, feature_share, outcome_ppg, share_increase in product(
        definition.feature_ppg_sensitivity,
        definition.feature_target_share_sensitivity,
        definition.outcome_ppg_sensitivity,
        definition.target_share_increase_sensitivity,
    ):
        diagnostic_definition = replace(
            definition,
            feature_ppg_ceiling=feature_ppg,
            feature_target_share_ceiling=feature_share,
            outcome_ppg_floor=outcome_ppg,
            target_share_increase_floor=share_increase,
        )
        evaluation = evaluate_primary_cohort(
            build_historical_pairs(frozen_records, definition=diagnostic_definition),
            definition=diagnostic_definition,
        )
        diagnostics.append(
            SensitivityDiagnostic(
                feature_ppg_ceiling=feature_ppg,
                feature_target_share_ceiling=feature_share,
                outcome_ppg_floor=outcome_ppg,
                target_share_increase_floor=share_increase,
                diagnostic_only=True,
                market_status="unavailable",
                evaluation=evaluation,
            )
        )
    return tuple(diagnostics)


def _complete_history_through_feature(
    feature: PlayerSeasonRecord,
    player_history: Iterable[PlayerSeasonRecord],
) -> tuple[
    Literal["complete", "prior_history_incomplete", "tenure_conflict"],
    tuple[PlayerSeasonRecord, ...],
]:
    same_player = [
        record
        for record in player_history
        if record.player_id == feature.player_id
        and record.position == feature.position
        and record.season_type == feature.season_type
        and record.season <= feature.season
    ]
    if not any(
        record.season == feature.season and record.career_year == feature.career_year
        for record in same_player
    ):
        same_player.append(feature)

    by_career_year: dict[int, PlayerSeasonRecord] = {}
    by_season: dict[int, PlayerSeasonRecord] = {}
    for record in same_player:
        existing_year = by_career_year.get(record.career_year)
        existing_season = by_season.get(record.season)
        if (
            (existing_year is not None and existing_year != record)
            or (existing_season is not None and existing_season != record)
            or record.rookie_year != feature.rookie_year
            or record.career_year != record.season - record.rookie_year + 1
        ):
            return "tenure_conflict", ()
        by_career_year[record.career_year] = record
        by_season[record.season] = record

    expected_years = tuple(range(1, feature.career_year + 1))
    if tuple(sorted(by_career_year)) != expected_years:
        return "prior_history_incomplete", ()

    ordered = tuple(by_career_year[career_year] for career_year in expected_years)
    expected_seasons = tuple(range(feature.rookie_year, feature.season + 1))
    if tuple(record.season for record in ordered) != expected_seasons:
        return "prior_history_incomplete", ()
    return "complete", ordered


def _evaluation_exclusion_reason(
    eligibility: FeatureEligibility,
    labels: OutcomeLabels,
) -> str | None:
    if eligibility.state in {
        "outside_declared_population",
        "prior_history_incomplete",
        "tenure_conflict",
        "unavailable_feature_fields",
    }:
        return eligibility.state
    if labels.state == "tenure_conflict":
        return "outcome_tenure_conflict"
    if labels.state == "unavailable":
        if "missing_outcome_row" in labels.reason_codes:
            return "missing_outcome"
        if "role_target_share_unavailable" in labels.reason_codes:
            return "role_outcome_unavailable"
        return "fantasy_outcome_unavailable"
    return None


def _is_finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _is_share(value: object) -> bool:
    return _is_finite_number(value) and 0.0 <= float(value) <= 1.0


def _round_optional(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else round(numerator / denominator, 4)


__all__ = [
    "DECLARED_OBSERVED_ROW_UNIVERSE",
    "LATE_VETERAN_WR_BREAKOUT_V0",
    "FeatureEligibility",
    "HistoricalPair",
    "LateVeteranWrBreakoutDefinition",
    "OutcomeLabels",
    "PrimaryCohortEvaluation",
    "SensitivityDiagnostic",
    "build_diagnostic_sensitivity_grid",
    "build_historical_pairs",
    "build_outcome_labels",
    "evaluate_feature_eligibility",
    "evaluate_primary_cohort",
]
