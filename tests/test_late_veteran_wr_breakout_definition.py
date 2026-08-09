from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from src.ingestion import PlayerSeasonRecord
from src.labels.late_veteran_wr_breakout import (
    DECLARED_OBSERVED_ROW_UNIVERSE,
    LATE_VETERAN_WR_BREAKOUT_V0,
    build_diagnostic_sensitivity_grid,
    build_historical_pairs,
    build_outcome_labels,
    evaluate_feature_eligibility,
    evaluate_primary_cohort,
)
from src.validation import ValidationError


def _record(
    player_id: str,
    season: int,
    *,
    rookie_year: int = 2023,
    player_name: str | None = None,
    position: str = "WR",
    games: int = 17,
    ppg: float = 4.0,
    target_share: float = 0.06,
) -> PlayerSeasonRecord:
    return PlayerSeasonRecord(
        player_id=player_id,
        player_name=player_name or player_id.upper(),
        position=position,
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
        targets=20,
        receptions=12,
        receiving_yards=180.0,
        receiving_tds=1,
        target_share=target_share,
        air_yards_share=0.10,
        wopr=0.20,
        routes_run=None,
        route_participation=None,
        snap_share=None,
        missing_fields=("routes_run", "route_participation", "snap_share"),
    )


def _three_year_player(
    player_id: str,
    *,
    feature_ppg: float = 4.0,
    feature_share: float = 0.06,
    outcome_ppg: float = 10.0,
    outcome_share: float = 0.15,
    outcome_games: int = 8,
) -> tuple[PlayerSeasonRecord, PlayerSeasonRecord, PlayerSeasonRecord]:
    rookie = _record(player_id, 2023, ppg=3.0, target_share=0.04)
    feature = _record(player_id, 2024, ppg=feature_ppg, target_share=feature_share)
    outcome = _record(
        player_id,
        2025,
        games=outcome_games,
        ppg=outcome_ppg,
        target_share=outcome_share,
    )
    return rookie, feature, outcome


def test_v0_definition_is_immutable_and_preregistered() -> None:
    definition = LATE_VETERAN_WR_BREAKOUT_V0

    assert definition.version == "late_veteran_wr_breakout_v0"
    assert definition.feature_ppg_ceiling == 7.0
    assert definition.feature_target_share_ceiling == 0.10
    assert definition.outcome_ppg_increase_floor == 3.0
    assert definition.target_share_increase_floor == 0.05
    assert definition.feature_ppg_sensitivity == (5.0, 7.0, 9.0)
    assert definition.market_adp_sensitivity == (180, 200, 240)

    with pytest.raises(FrozenInstanceError):
        definition.feature_ppg_ceiling = 9.0  # type: ignore[misc]


@pytest.mark.parametrize(
    ("feature_ppg", "feature_share", "eligible", "reason"),
    [
        (6.9999, 0.0999, True, "football_archetype_eligible"),
        (7.0, 0.0999, False, "feature_ppg_at_or_above_ceiling"),
        (6.9999, 0.10, False, "feature_target_share_at_or_above_ceiling"),
    ],
)
def test_feature_thresholds_are_strict_and_market_stays_unavailable(
    feature_ppg: float,
    feature_share: float,
    eligible: bool,
    reason: str,
) -> None:
    rookie, feature, _ = _three_year_player(
        "wr_boundary",
        feature_ppg=feature_ppg,
        feature_share=feature_share,
    )

    result = evaluate_feature_eligibility(feature, (rookie, feature))

    assert result.football_archetype_eligible is eligible
    assert reason in result.reason_codes
    assert result.market_status == "unavailable"
    assert result.market_qualified_eligible is None
    assert result.market_reason_codes == ("governed_redraft_adp_unavailable",)


def test_true_tenure_and_complete_rookie_to_feature_history_are_required() -> None:
    rookie = _record("wr_gap", 2022, rookie_year=2022)
    feature = _record("wr_gap", 2024, rookie_year=2022)

    missing_internal_year = evaluate_feature_eligibility(feature, (rookie, feature))
    left_censored = evaluate_feature_eligibility(feature, (feature,))
    conflicting_tenure = evaluate_feature_eligibility(
        replace(feature, career_year=2),
        (rookie, feature),
    )

    assert missing_internal_year.state == "prior_history_incomplete"
    assert left_censored.state == "prior_history_incomplete"
    assert conflicting_tenure.state == "tenure_conflict"
    assert missing_internal_year.target_career_year == 4


@pytest.mark.parametrize(
    ("prior_ppg", "prior_share", "expected_reason"),
    [
        (10.0, 0.05, "prior_established_ppg"),
        (4.0, 0.15, "prior_established_target_share"),
    ],
)
def test_prior_established_boundaries_exclude_down_years(
    prior_ppg: float,
    prior_share: float,
    expected_reason: str,
) -> None:
    rookie = _record("wr_established", 2023, ppg=prior_ppg, target_share=prior_share)
    feature = _record("wr_established", 2024, ppg=4.0, target_share=0.05)

    result = evaluate_feature_eligibility(feature, (rookie, feature))

    assert result.state == "ineligible"
    assert result.football_archetype_eligible is False
    assert expected_reason in result.reason_codes


def test_entering_year_three_is_source_backed_not_recorded_row_order() -> None:
    year_one = _record("wr_y3", 2023)
    year_two = _record("wr_y3", 2024)
    result = evaluate_feature_eligibility(year_two, (year_one, year_two))

    assert result.feature_career_year == 2
    assert result.target_career_year == 3
    assert result.target_season == 2025
    assert result.state == "eligible"

    veteran_first_seen = _record("wr_veteran", 2024, rookie_year=2020)
    veteran_result = evaluate_feature_eligibility(veteran_first_seen, (veteran_first_seen,))
    assert veteran_result.feature_career_year == 5
    assert veteran_result.state == "prior_history_incomplete"


def test_outcome_thresholds_are_inclusive_and_labels_remain_separate() -> None:
    _, feature, outcome = _three_year_player(
        "wr_outcome_edge",
        feature_ppg=7.0,
        feature_share=0.10,
        outcome_ppg=10.0,
        outcome_share=0.15,
        outcome_games=8,
    )

    labels = build_outcome_labels(feature, outcome)

    assert labels.ppg_increase == 3.0
    assert labels.target_share_increase == 0.05
    assert labels.fantasy_breakout is True
    assert labels.role_expansion == "confirmed"
    assert labels.archetype_hit is True

    seven_games = build_outcome_labels(feature, replace(outcome, games_played=7))
    assert seven_games.fantasy_breakout is False
    assert seven_games.role_expansion == "confirmed"
    assert seven_games.archetype_hit is False


def test_missing_outcome_or_target_share_is_unavailable_not_negative() -> None:
    _, feature, outcome = _three_year_player("wr_missing")

    missing_row = build_outcome_labels(feature, None)
    missing_share = build_outcome_labels(feature, replace(outcome, target_share=None))  # type: ignore[arg-type]
    observed_zero_share = build_outcome_labels(feature, replace(outcome, target_share=0.0))

    assert missing_row.fantasy_breakout is None
    assert missing_row.role_expansion == "unavailable"
    assert missing_row.archetype_hit is None
    assert missing_share.fantasy_breakout is True
    assert missing_share.role_expansion == "unavailable"
    assert missing_share.archetype_hit is None
    assert observed_zero_share.role_expansion == "not_confirmed"


def test_outcome_tenure_conflict_is_explicit() -> None:
    _, feature, outcome = _three_year_player("wr_conflict")

    labels = build_outcome_labels(feature, replace(outcome, career_year=4))

    assert labels.state == "tenure_conflict"
    assert labels.fantasy_breakout is None
    assert labels.role_expansion == "unavailable"
    assert labels.reason_codes == ("outcome_identity_or_tenure_conflict",)


def test_feature_eligibility_is_unchanged_when_outcomes_are_mutated() -> None:
    rookie, feature, outcome = _three_year_player("wr_no_leak")
    first_pairs = build_historical_pairs((rookie, feature, outcome))
    changed_outcome = replace(outcome, season_ppg=30.0, target_share=0.50, games_played=17)
    second_pairs = build_historical_pairs((changed_outcome, feature, rookie))

    first = next(pair for pair in first_pairs if pair.feature.season == 2024)
    second = next(pair for pair in second_pairs if pair.feature.season == 2024)

    assert first.eligibility == second.eligibility
    assert first.labels != second.labels


def test_historical_pairs_retain_missing_outcomes_and_reject_duplicates() -> None:
    rookie, feature, _ = _three_year_player("wr_pair")

    pairs = build_historical_pairs((feature, rookie))
    feature_pair = next(pair for pair in pairs if pair.feature.season == 2024)

    assert feature_pair.outcome is None
    assert feature_pair.labels.state == "unavailable"
    assert feature_pair.evaluation_state == "coverage_exclusion"
    assert feature_pair.evaluation_exclusion_reason == "missing_outcome"

    with pytest.raises(ValidationError, match="duplicate observed WR player-season key"):
        build_historical_pairs((rookie, rookie))


def test_duplicate_player_names_never_override_canonical_id_joins() -> None:
    first = tuple(
        replace(record, player_name="Same Name")
        for record in _three_year_player("wr_same_name_a")
    )
    second = tuple(
        replace(record, player_name="Same Name")
        for record in _three_year_player("wr_same_name_b", outcome_ppg=9.0)
    )

    pairs = build_historical_pairs((*second, *first))
    first_pair = next(
        pair
        for pair in pairs
        if pair.feature.player_id == "wr_same_name_a" and pair.feature.season == 2024
    )
    second_pair = next(
        pair
        for pair in pairs
        if pair.feature.player_id == "wr_same_name_b" and pair.feature.season == 2024
    )

    assert first_pair.outcome is not None
    assert first_pair.outcome.player_id == "wr_same_name_a"
    assert first_pair.labels.fantasy_breakout is True
    assert second_pair.outcome is not None
    assert second_pair.outcome.player_id == "wr_same_name_b"
    assert second_pair.labels.fantasy_breakout is False


def test_primary_evaluation_uses_only_declared_observed_row_universe() -> None:
    records: list[PlayerSeasonRecord] = []
    records.extend(_three_year_player("wr_tp"))
    records.extend(_three_year_player("wr_fp", outcome_ppg=9.9))
    records.extend(_three_year_player("wr_fn", feature_ppg=7.0, outcome_ppg=10.0))
    records.extend(_three_year_player("wr_tn", feature_ppg=7.0, outcome_ppg=9.9))

    evaluation = evaluate_primary_cohort(build_historical_pairs(reversed(records)))

    assert evaluation.declared_universe == DECLARED_OBSERVED_ROW_UNIVERSE
    assert evaluation.observed_pair_count == 12
    assert evaluation.evaluable_pair_count == 4
    assert evaluation.coverage_exclusion_count == 8
    assert evaluation.true_positives == 1
    assert evaluation.false_positives == 1
    assert evaluation.false_negatives == 1
    assert evaluation.true_negatives == 1
    assert evaluation.precision == 0.5
    assert evaluation.recall == 0.5
    assert evaluation.base_rate == 0.5
    assert evaluation.small_sample_warning is not None
    assert evaluation.market_status == "unavailable"


def test_jennings_and_washington_controls_follow_rules_without_name_hardcoding() -> None:
    jennings_feature = _record(
        "00-0036259",
        2023,
        rookie_year=2020,
        player_name="Jauan Jennings",
        ppg=3.96,
        target_share=0.0701,
    )
    jennings_outcome = _record(
        "00-0036259",
        2024,
        rookie_year=2020,
        player_name="Jauan Jennings",
        ppg=14.03,
        target_share=0.2203,
    )
    jennings_labels = build_outcome_labels(jennings_feature, jennings_outcome)
    jennings_eligibility = evaluate_feature_eligibility(
        jennings_feature,
        (jennings_feature,),
    )

    washington_rookie = _record(
        "00-0038606",
        2023,
        player_name="Parker Washington",
        ppg=3.0,
        target_share=0.04,
    )
    washington_feature = _record(
        "00-0038606",
        2024,
        player_name="Parker Washington",
        ppg=6.93,
        target_share=0.0977,
    )
    washington_outcome = _record(
        "00-0038606",
        2025,
        player_name="Parker Washington",
        ppg=11.54,
        target_share=0.1737,
    )
    washington_labels = build_outcome_labels(washington_feature, washington_outcome)
    washington_eligibility = evaluate_feature_eligibility(
        washington_feature,
        (washington_rookie, washington_feature),
    )

    assert jennings_labels.archetype_hit is True
    assert jennings_eligibility.state == "prior_history_incomplete"
    assert washington_labels.archetype_hit is True
    assert washington_eligibility.football_archetype_eligible is True

    synthetic_feature = replace(washington_feature, player_id="wr_synthetic", player_name="Synthetic")
    synthetic_rookie = replace(washington_rookie, player_id="wr_synthetic", player_name="Synthetic")
    synthetic_outcome = replace(washington_outcome, player_id="wr_synthetic", player_name="Synthetic")
    assert evaluate_feature_eligibility(
        synthetic_feature,
        (synthetic_rookie, synthetic_feature),
    ).football_archetype_eligible is True
    assert build_outcome_labels(synthetic_feature, synthetic_outcome).archetype_hit is True


def test_diagnostic_sensitivity_grid_is_complete_deterministic_and_unselected() -> None:
    records = _three_year_player("wr_grid")

    first = build_diagnostic_sensitivity_grid(records)
    second = build_diagnostic_sensitivity_grid(reversed(records))

    assert first == second
    assert len(first) == 3 * 3 * 2 * 4
    assert {row.feature_ppg_ceiling for row in first} == {5.0, 7.0, 9.0}
    assert {row.feature_target_share_ceiling for row in first} == {0.08, 0.10, 0.12}
    assert {row.outcome_ppg_floor for row in first} == {10.0, 12.0}
    assert {row.target_share_increase_floor for row in first} == {0.04, 0.05, 0.06, 0.08}
    assert all(row.diagnostic_only is True for row in first)
    assert all(row.market_status == "unavailable" for row in first)
    assert all(not hasattr(row, name) for row in first for name in ("rank", "score", "best"))
    assert LATE_VETERAN_WR_BREAKOUT_V0.feature_ppg_ceiling == 7.0
    assert LATE_VETERAN_WR_BREAKOUT_V0.target_share_increase_floor == 0.05
