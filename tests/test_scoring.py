from src.backtest.scoring import build_candidate_ranking_rows, compute_breakout_signal_score
from src.features.mock_data import load_mock_feature_rows


def test_scoring_function_is_deterministic_for_same_input() -> None:
    row = load_mock_feature_rows()[0]
    first = compute_breakout_signal_score(row)
    second = compute_breakout_signal_score(row)
    assert first == second


def test_candidate_rankings_are_deterministically_sorted() -> None:
    rankings = build_candidate_ranking_rows(load_mock_feature_rows())
    assert [row.player_id for row in rankings] == ["wr_alpha", "wr_charlie", "wr_bravo"]
    assert [row.rank for row in rankings] == [1, 2, 3]
