"""Placeholder breakout labeling rules for PR1."""

from __future__ import annotations

from src.schemas import BreakoutLabelRow, PlayerSeasonFeatureRow


BREAKOUT_LABEL_NAME = "wr_breakout_v1_placeholder"


def assign_breakout_label(
    feature_row: PlayerSeasonFeatureRow,
    outcome_row: dict[str, object],
) -> BreakoutLabelRow:
    """Assign a deterministic placeholder breakout label for a WR outcome season."""

    outcome_ppr_points = float(outcome_row["outcome_ppr_points"])
    outcome_ppr_points_per_game = float(outcome_row["outcome_ppr_points_per_game"])
    outcome_games_played = int(outcome_row["outcome_games_played"])

    is_breakout = (
        outcome_ppr_points >= 200.0
        and outcome_ppr_points_per_game >= 12.0
        and outcome_games_played >= 12
        and feature_row.feature_season_ppr_points < 200.0
    )

    reason = (
        "Scaffold placeholder rule: breakout thresholds met without prior 200-PPR season."
        if is_breakout
        else "Scaffold placeholder rule: breakout thresholds not met."
    )

    return BreakoutLabelRow(
        player_id=feature_row.player_id,
        player_name=feature_row.player_name,
        feature_season=feature_row.feature_season,
        outcome_season=int(outcome_row["outcome_season"]),
        label_name=BREAKOUT_LABEL_NAME,
        is_breakout=is_breakout,
        outcome_ppr_points=outcome_ppr_points,
        outcome_ppr_points_per_game=outcome_ppr_points_per_game,
        outcome_games_played=outcome_games_played,
        label_reason=reason,
    )
