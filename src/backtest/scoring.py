"""Deterministic placeholder scoring for breakout candidates."""

from __future__ import annotations

from src.schemas import CandidateRankingRow, PlayerSeasonFeatureRow

SCORING_VERSION = "scaffold_deterministic_v1"


def compute_signal_components(feature_row: PlayerSeasonFeatureRow) -> dict[str, float]:
    """Return normalized placeholder components derived only from prior-season features."""

    return {
        "target_share_component": round(feature_row.target_share * 100, 3),
        "air_yards_component": round(feature_row.air_yards_share * 100, 3),
        "efficiency_component": round(feature_row.yards_per_route_run * 10, 3),
        "explosive_component": round(feature_row.explosive_play_rate * 100, 3),
        "red_zone_component": round(feature_row.red_zone_target_share * 100, 3),
    }


def compute_breakout_signal_score(feature_row: PlayerSeasonFeatureRow) -> float:
    """Compute a deterministic scaffold-only signal score from prior-season features."""

    components = compute_signal_components(feature_row)
    score = (
        components["target_share_component"] * 0.30
        + components["air_yards_component"] * 0.20
        + components["efficiency_component"] * 0.25
        + components["explosive_component"] * 0.15
        + components["red_zone_component"] * 0.10
    )
    return round(score, 4)


def build_candidate_ranking_rows(
    feature_rows: list[PlayerSeasonFeatureRow],
) -> list[CandidateRankingRow]:
    """Create ranked scaffold candidate rows from feature rows."""

    sorted_rows = sorted(
        feature_rows,
        key=lambda row: (-compute_breakout_signal_score(row), row.player_id),
    )

    rankings: list[CandidateRankingRow] = []
    for idx, row in enumerate(sorted_rows, start=1):
        rankings.append(
            CandidateRankingRow(
                player_id=row.player_id,
                player_name=row.player_name,
                feature_season=row.feature_season,
                target_outcome_season=row.target_outcome_season,
                position=row.position,
                breakout_signal_score=compute_breakout_signal_score(row),
                rank=idx,
                score_components=compute_signal_components(row),
                scoring_version=SCORING_VERSION,
                notes="Scaffold-only deterministic ranking from mock prior-season features.",
            )
        )
    return rankings
