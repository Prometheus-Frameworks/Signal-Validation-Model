from src.schemas import PlayerSeasonFeatureRow, SchemaValidationError


def build_valid_feature_row() -> dict:
    return {
        "player_id": "wr_test",
        "player_name": "Test Player",
        "position": "WR",
        "feature_season": 2024,
        "target_outcome_season": 2025,
        "data_through_season": 2024,
        "prior_team": "TST",
        "age_on_sept_1": 24.0,
        "games_played": 15,
        "routes_run": 400,
        "targets": 90,
        "target_share": 0.21,
        "air_yards_share": 0.24,
        "first_read_target_share": 0.20,
        "yards_per_route_run": 1.9,
        "explosive_play_rate": 0.11,
        "red_zone_target_share": 0.18,
        "feature_season_ppr_points": 160.0,
        "feature_season_ppr_points_per_game": 10.7,
    }


def test_feature_row_schema_accepts_timestamp_safe_input() -> None:
    row = PlayerSeasonFeatureRow.model_validate(build_valid_feature_row())
    assert row.player_id == "wr_test"
    assert row.target_outcome_season == 2025


def test_feature_row_rejects_future_leakage_at_interface_level() -> None:
    payload = build_valid_feature_row()
    payload["data_through_season"] = 2025

    try:
        PlayerSeasonFeatureRow.model_validate(payload)
    except SchemaValidationError as exc:
        assert "data_through_season cannot exceed feature_season" in str(exc)
    else:
        raise AssertionError("Expected timestamp safety validation to fail.")


def test_feature_row_rejects_non_adjacent_outcome_season() -> None:
    payload = build_valid_feature_row()
    payload["target_outcome_season"] = 2026

    try:
        PlayerSeasonFeatureRow.model_validate(payload)
    except SchemaValidationError as exc:
        assert "target_outcome_season must equal feature_season + 1" in str(exc)
    else:
        raise AssertionError("Expected one-step horizon validation to fail.")
