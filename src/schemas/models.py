"""Typed schema models for scaffold research datasets."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json


class SchemaValidationError(ValueError):
    """Raised when a schema violates scaffold validation rules."""


@dataclass(frozen=True)
class PlayerSeasonFeatureRow:
    """Timestamp-safe prior-season feature row for a single player-season."""

    player_id: str
    player_name: str
    position: str
    feature_season: int
    target_outcome_season: int
    data_through_season: int
    prior_team: str
    age_on_sept_1: float
    games_played: int
    routes_run: int
    targets: int
    target_share: float
    air_yards_share: float
    first_read_target_share: float
    yards_per_route_run: float
    explosive_play_rate: float
    red_zone_target_share: float
    feature_season_ppr_points: float
    feature_season_ppr_points_per_game: float

    def __post_init__(self) -> None:
        if len(self.position) != 2 or not self.position.isalpha() or not self.position.isupper():
            raise SchemaValidationError("position must be a two-letter uppercase string")
        if self.target_outcome_season != self.feature_season + 1:
            raise SchemaValidationError("target_outcome_season must equal feature_season + 1")
        if self.data_through_season > self.feature_season:
            raise SchemaValidationError("data_through_season cannot exceed feature_season")

    @classmethod
    def model_validate(cls, payload: dict) -> "PlayerSeasonFeatureRow":
        return cls(**payload)

    def model_dump(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BreakoutLabelRow:
    """Outcome-season breakout label for evaluation only."""

    player_id: str
    player_name: str
    feature_season: int
    outcome_season: int
    label_name: str
    is_breakout: bool
    outcome_ppr_points: float
    outcome_ppr_points_per_game: float
    outcome_games_played: int
    label_reason: str

    def __post_init__(self) -> None:
        if self.outcome_season != self.feature_season + 1:
            raise SchemaValidationError("outcome_season must equal feature_season + 1")

    def model_dump(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class CandidateRankingRow:
    """Scaffold ranking record produced from prior-season features."""

    player_id: str
    player_name: str
    feature_season: int
    target_outcome_season: int
    position: str
    breakout_signal_score: float
    rank: int
    score_components: dict[str, float]
    scoring_version: str
    notes: str

    def model_dump(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ValidationSummaryRow:
    """Aggregate summary for a single scaffold validation run."""

    feature_season: int
    outcome_season: int
    position: str
    candidate_count: int
    breakout_count: int
    top_ranked_player_id: str
    top_ranked_player_name: str
    scoring_version: str
    summary_note: str

    def model_dump(self) -> dict:
        return asdict(self)

    def model_dump_json(self, indent: int = 2) -> str:
        return json.dumps(self.model_dump(), indent=indent)
