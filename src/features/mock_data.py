"""Mock prior-season feature rows and next-season outcomes for scaffold runs."""

from __future__ import annotations

from src.schemas import PlayerSeasonFeatureRow


MOCK_OUTCOMES_2025 = [
    {
        "player_id": "wr_alpha",
        "player_name": "Alpha Receiver",
        "feature_season": 2024,
        "outcome_season": 2025,
        "outcome_ppr_points": 228.0,
        "outcome_ppr_points_per_game": 14.3,
        "outcome_games_played": 16,
    },
    {
        "player_id": "wr_bravo",
        "player_name": "Bravo Wideout",
        "feature_season": 2024,
        "outcome_season": 2025,
        "outcome_ppr_points": 171.5,
        "outcome_ppr_points_per_game": 11.4,
        "outcome_games_played": 15,
    },
    {
        "player_id": "wr_charlie",
        "player_name": "Charlie Target",
        "feature_season": 2024,
        "outcome_season": 2025,
        "outcome_ppr_points": 207.5,
        "outcome_ppr_points_per_game": 12.2,
        "outcome_games_played": 17,
    },
]


def load_mock_feature_rows() -> list[PlayerSeasonFeatureRow]:
    """Return deterministic mock prior-season WR features for the scaffold pipeline."""

    rows = [
        {
            "player_id": "wr_alpha",
            "player_name": "Alpha Receiver",
            "position": "WR",
            "feature_season": 2024,
            "target_outcome_season": 2025,
            "data_through_season": 2024,
            "prior_team": "AAA",
            "age_on_sept_1": 24.4,
            "games_played": 16,
            "routes_run": 505,
            "targets": 112,
            "target_share": 0.23,
            "air_yards_share": 0.29,
            "first_read_target_share": 0.26,
            "yards_per_route_run": 2.18,
            "explosive_play_rate": 0.14,
            "red_zone_target_share": 0.24,
            "feature_season_ppr_points": 164.0,
            "feature_season_ppr_points_per_game": 10.3,
        },
        {
            "player_id": "wr_bravo",
            "player_name": "Bravo Wideout",
            "position": "WR",
            "feature_season": 2024,
            "target_outcome_season": 2025,
            "data_through_season": 2024,
            "prior_team": "BBB",
            "age_on_sept_1": 27.1,
            "games_played": 15,
            "routes_run": 440,
            "targets": 95,
            "target_share": 0.20,
            "air_yards_share": 0.22,
            "first_read_target_share": 0.19,
            "yards_per_route_run": 1.81,
            "explosive_play_rate": 0.10,
            "red_zone_target_share": 0.17,
            "feature_season_ppr_points": 145.5,
            "feature_season_ppr_points_per_game": 9.7,
        },
        {
            "player_id": "wr_charlie",
            "player_name": "Charlie Target",
            "position": "WR",
            "feature_season": 2024,
            "target_outcome_season": 2025,
            "data_through_season": 2024,
            "prior_team": "CCC",
            "age_on_sept_1": 23.7,
            "games_played": 17,
            "routes_run": 470,
            "targets": 104,
            "target_share": 0.21,
            "air_yards_share": 0.25,
            "first_read_target_share": 0.22,
            "yards_per_route_run": 1.95,
            "explosive_play_rate": 0.12,
            "red_zone_target_share": 0.20,
            "feature_season_ppr_points": 198.0,
            "feature_season_ppr_points_per_game": 11.6,
        },
    ]
    return [PlayerSeasonFeatureRow.model_validate(row) for row in rows]
