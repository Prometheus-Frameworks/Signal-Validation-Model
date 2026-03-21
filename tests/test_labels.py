from src.labels.rules import assign_breakout_label
from src.schemas import PlayerSeasonFeatureRow


BASE_FEATURE = PlayerSeasonFeatureRow(
    player_id="wr_fixture",
    player_name="Fixture Player",
    position="WR",
    feature_season=2024,
    target_outcome_season=2025,
    data_through_season=2024,
    prior_team="FIX",
    age_on_sept_1=24.2,
    games_played=16,
    routes_run=490,
    targets=100,
    target_share=0.22,
    air_yards_share=0.27,
    first_read_target_share=0.24,
    yards_per_route_run=2.1,
    explosive_play_rate=0.13,
    red_zone_target_share=0.22,
    feature_season_ppr_points=175.0,
    feature_season_ppr_points_per_game=10.9,
)


def test_assign_breakout_label_marks_breakout_when_thresholds_are_met() -> None:
    label = assign_breakout_label(
        BASE_FEATURE,
        {
            "player_id": "wr_fixture",
            "player_name": "Fixture Player",
            "feature_season": 2024,
            "outcome_season": 2025,
            "outcome_ppr_points": 225.0,
            "outcome_ppr_points_per_game": 13.2,
            "outcome_games_played": 17,
        },
    )

    assert label.is_breakout is True
    assert "thresholds met" in label.label_reason


def test_assign_breakout_label_rejects_repeat_200_point_season_as_breakout() -> None:
    prior_star = PlayerSeasonFeatureRow(**{**BASE_FEATURE.model_dump(), "feature_season_ppr_points": 205.0})

    label = assign_breakout_label(
        prior_star,
        {
            "player_id": "wr_fixture",
            "player_name": "Fixture Player",
            "feature_season": 2024,
            "outcome_season": 2025,
            "outcome_ppr_points": 225.0,
            "outcome_ppr_points_per_game": 13.2,
            "outcome_games_played": 17,
        },
    )

    assert label.is_breakout is False
