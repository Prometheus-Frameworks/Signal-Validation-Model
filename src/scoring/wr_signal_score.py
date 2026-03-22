"""Deterministic WR breakout signal scoring, ranking, and validation reporting."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Iterable

from src.scoring.recipes import DEFAULT_RECIPE, SignalRecipe

REQUIRED_FEATURE_COLUMNS = {
    "player_id",
    "player_name",
    "feature_season",
    "outcome_season",
    "position",
    "feature_team",
    "feature_games_played",
    "feature_total_ppr",
    "feature_ppg",
    "feature_finish",
    "feature_targets_per_game",
    "feature_target_share",
    "expected_ppg_baseline",
}

REQUIRED_DATASET_COLUMNS = REQUIRED_FEATURE_COLUMNS | {
    "has_valid_outcome",
    "breakout_label_default",
    "breakout_reason",
}

COMPONENT_WEIGHTS = DEFAULT_RECIPE.component_weights
SCORING_VERSION = DEFAULT_RECIPE.scoring_version
RANKING_OUTPUT_COLUMNS = [
    "player_id",
    "player_name",
    "feature_season",
    "outcome_season",
    "position",
    "feature_team",
    "has_valid_outcome",
    "breakout_label_default",
    "breakout_reason",
    "wr_signal_score",
    "rank",
    "scoring_version",
]
COMPONENT_OUTPUT_COLUMNS = [
    "player_id",
    "player_name",
    "feature_season",
    "outcome_season",
    "position",
    "usage_signal",
    "efficiency_signal",
    "development_signal",
    "stability_signal",
    "cohort_signal",
    "role_signal",
    "penalty_signal",
    "wr_signal_score",
    "scoring_version",
    "usage_formula_notes",
    "efficiency_formula_notes",
    "development_formula_notes",
    "stability_formula_notes",
    "cohort_formula_notes",
    "role_formula_notes",
    "penalty_formula_notes",
]


@dataclass(frozen=True)
class ScoredCandidate:
    player_id: str
    player_name: str
    feature_season: int
    outcome_season: int
    position: str
    feature_team: str
    has_valid_outcome: bool
    breakout_label_default: bool
    breakout_reason: str
    usage_signal: float
    efficiency_signal: float
    development_signal: float
    stability_signal: float
    cohort_signal: float
    role_signal: float
    penalty_signal: float
    wr_signal_score: float
    rank: int
    scoring_version: str = SCORING_VERSION

    def ranking_row(self) -> dict[str, object]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "feature_season": self.feature_season,
            "outcome_season": self.outcome_season,
            "position": self.position,
            "feature_team": self.feature_team,
            "has_valid_outcome": self.has_valid_outcome,
            "breakout_label_default": self.breakout_label_default,
            "breakout_reason": self.breakout_reason,
            "wr_signal_score": self.wr_signal_score,
            "rank": self.rank,
            "scoring_version": self.scoring_version,
        }

    def component_row(self, recipe: SignalRecipe = DEFAULT_RECIPE) -> dict[str, object]:
        thresholds = recipe.thresholds
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "feature_season": self.feature_season,
            "outcome_season": self.outcome_season,
            "position": self.position,
            "usage_signal": self.usage_signal,
            "efficiency_signal": self.efficiency_signal,
            "development_signal": self.development_signal,
            "stability_signal": self.stability_signal,
            "cohort_signal": self.cohort_signal,
            "role_signal": self.role_signal,
            "penalty_signal": self.penalty_signal,
            "wr_signal_score": self.wr_signal_score,
            "scoring_version": self.scoring_version,
            "usage_formula_notes": (
                f"{recipe.usage_weights['targets_per_game']:.2f}*scale(feature_targets_per_game,"
                f"{thresholds.usage_targets_per_game_floor:.2f},{thresholds.usage_targets_per_game_ceiling:.2f})+"
                f"{recipe.usage_weights['target_share']:.2f}*scale(feature_target_share,"
                f"{thresholds.usage_target_share_floor:.2f},{thresholds.usage_target_share_ceiling:.2f})"
            ),
            "efficiency_formula_notes": (
                f"{recipe.efficiency_weights['ppg_per_target']:.2f}*scale(feature_ppg_per_target,"
                f"{thresholds.efficiency_ppg_per_target_floor:.2f},"
                f"{thresholds.efficiency_ppg_per_target_ceiling:.2f})+"
                f"{recipe.efficiency_weights['ppg']:.2f}*scale(feature_ppg,"
                f"{thresholds.efficiency_ppg_floor:.2f},{thresholds.efficiency_ppg_ceiling:.2f})"
            ),
            "development_formula_notes": (
                f"{recipe.development_weights['finish_room']:.2f}*scale("
                f"{thresholds.development_finish_anchor:.2f}-feature_finish,"
                f"{thresholds.development_finish_floor:.2f},{thresholds.development_finish_ceiling:.2f})+"
                f"{recipe.development_weights['expected_gap']:.2f}*scale(expected_ppg_baseline-feature_ppg,"
                f"{thresholds.development_expected_gap_floor:.2f},"
                f"{thresholds.development_expected_gap_ceiling:.2f})"
            ),
            "stability_formula_notes": (
                f"{recipe.stability_weights['games_played']:.2f}*scale(feature_games_played,"
                f"{thresholds.stability_games_floor:.2f},{thresholds.stability_games_ceiling:.2f})+"
                f"{recipe.stability_weights['total_ppr']:.2f}*scale(feature_total_ppr,"
                f"{thresholds.stability_total_ppr_floor:.2f},{thresholds.stability_total_ppr_ceiling:.2f})"
            ),
            "cohort_formula_notes": (
                f"{recipe.cohort_weights['ppg_delta']:.2f}*scale(feature_ppg_minus_cohort_expected,"
                f"{thresholds.cohort_ppg_delta_floor:.2f},{thresholds.cohort_ppg_delta_ceiling:.2f})+"
                f"{recipe.cohort_weights['finish_delta']:.2f}*scale(expected_finish_from_cohort-feature_finish,"
                f"{thresholds.cohort_finish_delta_floor:.2f},{thresholds.cohort_finish_delta_ceiling:.2f})+"
                f"{recipe.cohort_weights['cohort_count']:.2f}*scale(cohort_player_count,"
                f"{thresholds.cohort_count_floor:.2f},{thresholds.cohort_count_ceiling:.2f})"
            ),
            "role_formula_notes": (
                f"{recipe.role_weights['route_participation']:.2f}*scale(route_participation_season_avg,"
                f"{thresholds.role_route_participation_floor:.2f},{thresholds.role_route_participation_ceiling:.2f})+"
                f"{recipe.role_weights['target_share']:.2f}*scale(target_share_season_avg,"
                f"{thresholds.role_target_share_floor:.2f},{thresholds.role_target_share_ceiling:.2f})+"
                f"{recipe.role_weights['air_yard_share']:.2f}*scale(air_yard_share_season_avg,"
                f"{thresholds.role_air_yard_share_floor:.2f},{thresholds.role_air_yard_share_ceiling:.2f})+"
                f"{recipe.role_weights['routes_consistency']:.2f}*scale(routes_consistency_index,"
                f"{thresholds.role_routes_consistency_floor:.2f},{thresholds.role_routes_consistency_ceiling:.2f})+"
                f"{recipe.role_weights['target_earning_index']:.2f}*scale(target_earning_index,"
                f"{thresholds.role_target_earning_floor:.2f},{thresholds.role_target_earning_ceiling:.2f})+"
                f"{recipe.role_weights['opportunity_concentration']:.2f}*scale(opportunity_concentration_score,"
                f"{thresholds.role_opportunity_concentration_floor:.2f},"
                f"{thresholds.role_opportunity_concentration_ceiling:.2f})"
            ),
            "penalty_formula_notes": (
                f"{recipe.penalty_weights['already_elite']:.2f}*scale("
                f"{thresholds.penalty_finish_anchor:.2f}-feature_finish,"
                f"{thresholds.penalty_finish_floor:.2f},{thresholds.penalty_finish_ceiling:.2f})+"
                f"{recipe.penalty_weights['missed_games']:.2f}*scale("
                f"{thresholds.penalty_games_anchor:.2f}-feature_games_played,"
                f"{thresholds.penalty_games_floor:.2f},{thresholds.penalty_games_ceiling:.2f})+"
                f"{recipe.penalty_weights['thin_share']:.2f}*scale("
                f"{thresholds.penalty_target_share_anchor:.2f}-feature_target_share,"
                f"{thresholds.penalty_target_share_floor:.2f},{thresholds.penalty_target_share_ceiling:.2f})"
            ),
        }


@dataclass(frozen=True)
class ScoreArtifacts:
    candidate_rankings_path: Path
    component_scores_path: Path
    validation_summary_path: Path
    top_candidates_path: Path
    false_positives_path: Path
    false_negatives_path: Path


def score_wr_candidates(
    validation_dataset_path: str | Path,
    output_dir: str | Path = "outputs",
    recipe: SignalRecipe = DEFAULT_RECIPE,
) -> ScoreArtifacts:
    """Score WR candidates from the PR3 validation dataset and write deterministic artifacts."""

    dataset_path = Path(validation_dataset_path)
    output_dir = Path(output_dir)
    rows = read_validation_dataset(dataset_path)
    scored_candidates = build_scored_candidates(rows, recipe=recipe)
    summary = build_validation_summary(scored_candidates, recipe=recipe)

    candidate_dir = output_dir / "candidate_rankings"
    report_dir = output_dir / "validation_reports"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    candidate_rankings_path = candidate_dir / "wr_candidate_rankings.csv"
    component_scores_path = candidate_dir / "wr_signal_component_scores.csv"
    validation_summary_path = report_dir / "wr_signal_validation_summary.json"
    top_candidates_path = report_dir / "wr_top_candidates.md"
    false_positives_path = report_dir / "wr_false_positives.md"
    false_negatives_path = report_dir / "wr_false_negatives.md"

    _write_csv(candidate_rankings_path, RANKING_OUTPUT_COLUMNS, [row.ranking_row() for row in scored_candidates])
    _write_csv(component_scores_path, COMPONENT_OUTPUT_COLUMNS, [row.component_row(recipe=recipe) for row in scored_candidates])
    validation_summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    top_candidates_path.write_text(build_top_candidates_markdown(scored_candidates), encoding="utf-8")
    false_positives_path.write_text(build_false_positives_markdown(scored_candidates), encoding="utf-8")
    false_negatives_path.write_text(build_false_negatives_markdown(scored_candidates), encoding="utf-8")

    return ScoreArtifacts(
        candidate_rankings_path=candidate_rankings_path,
        component_scores_path=component_scores_path,
        validation_summary_path=validation_summary_path,
        top_candidates_path=top_candidates_path,
        false_positives_path=false_positives_path,
        false_negatives_path=false_negatives_path,
    )


def read_validation_dataset(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        raise ValueError(f"validation dataset does not exist: {path}")

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("validation dataset must contain a header row")
        missing = sorted(REQUIRED_DATASET_COLUMNS - set(reader.fieldnames))
        if missing:
            raise ValueError(f"validation dataset is missing required columns: {missing}")
        return [_normalize_dataset_row(row) for row in reader]


def build_scored_candidates(
    rows: Iterable[dict[str, object]],
    recipe: SignalRecipe = DEFAULT_RECIPE,
) -> list[ScoredCandidate]:
    by_season: dict[int, list[dict[str, object]]] = {}
    for row in rows:
        by_season.setdefault(int(row["feature_season"]), []).append(row)

    scored: list[ScoredCandidate] = []
    for feature_season, season_rows in sorted(by_season.items()):
        season_candidates = [_score_candidate(row, recipe=recipe) for row in season_rows]
        ordered = sorted(
            season_candidates,
            key=lambda row: (
                -row["wr_signal_score"],
                -row["usage_signal"],
                -row["efficiency_signal"],
                -row["development_signal"],
                -row["stability_signal"],
                -row["cohort_signal"],
                -row["role_signal"],
                row["penalty_signal"],
                row["player_id"],
            ),
        )
        for rank, row in enumerate(ordered, start=1):
            scored.append(
                ScoredCandidate(
                    player_id=str(row["player_id"]),
                    player_name=str(row["player_name"]),
                    feature_season=feature_season,
                    outcome_season=int(row["outcome_season"]),
                    position=str(row["position"]),
                    feature_team=str(row["feature_team"]),
                    has_valid_outcome=bool(row["has_valid_outcome"]),
                    breakout_label_default=bool(row["breakout_label_default"]),
                    breakout_reason=str(row["breakout_reason"]),
                    usage_signal=float(row["usage_signal"]),
                    efficiency_signal=float(row["efficiency_signal"]),
                    development_signal=float(row["development_signal"]),
                    stability_signal=float(row["stability_signal"]),
                    cohort_signal=float(row["cohort_signal"]),
                    role_signal=float(row["role_signal"]),
                    penalty_signal=float(row["penalty_signal"]),
                    wr_signal_score=float(row["wr_signal_score"]),
                    rank=rank,
                    scoring_version=recipe.scoring_version,
                )
            )
    return scored


def build_validation_summary(
    scored_candidates: Iterable[ScoredCandidate],
    recipe: SignalRecipe = DEFAULT_RECIPE,
) -> dict[str, object]:
    rows = list(scored_candidates)
    evaluable_rows = [row for row in rows if row.has_valid_outcome]
    breakouts = [row for row in evaluable_rows if row.breakout_label_default]

    summary: dict[str, object] = {
        "position": "WR",
        "recipe_name": recipe.name,
        "scoring_version": recipe.scoring_version,
        "candidate_count": len(rows),
        "evaluated_candidate_count": len(evaluable_rows),
        "breakout_count": len(breakouts),
        "feature_seasons": sorted({row.feature_season for row in rows}),
        "precision_at_10": _precision_at_n(evaluable_rows, 10),
        "precision_at_20": _precision_at_n(evaluable_rows, 20),
        "precision_at_30": _precision_at_n(evaluable_rows, 30),
        "recall_at_10": _recall_at_n(breakouts, 10),
        "recall_at_20": _recall_at_n(breakouts, 20),
        "recall_at_30": _recall_at_n(breakouts, 30),
        "average_rank_of_actual_breakouts": _average_rank(breakouts),
        "median_rank_of_actual_breakouts": _median_rank(breakouts),
        "false_positives_in_top_20": sum(
            1 for row in evaluable_rows if row.rank <= 20 and not row.breakout_label_default
        ),
        "false_negatives_outside_top_30": sum(1 for row in breakouts if row.rank > 30),
        "evaluation_notes": {
            "top_n_metrics_only_include_rows_with_valid_outcomes": True,
            "ranks_are_assigned_within_each_feature_season": True,
            "score_inputs_are_feature_season_fields_only": True,
            "cohort_expectations_are_historical_only": True,
            "role_usage_inputs_are_feature_season_only": True,
        },
        "component_weights": recipe.component_weights,
    }
    return summary


def build_top_candidates_markdown(scored_candidates: Iterable[ScoredCandidate], limit: int = 20) -> str:
    rows = list(scored_candidates)
    sections = [
        "# WR Top Candidates",
        "",
        "Deterministic candidate rankings built only from feature-season fields.",
        "",
    ]
    for feature_season in sorted({row.feature_season for row in rows}):
        season_rows = [row for row in rows if row.feature_season == feature_season][:limit]
        sections.extend(
            [
                f"## Feature season {feature_season}",
                "",
                _markdown_table(season_rows),
                "",
            ]
        )
    return "\n".join(sections)


def build_false_positives_markdown(scored_candidates: Iterable[ScoredCandidate], limit: int = 20) -> str:
    rows = [
        row
        for row in scored_candidates
        if row.has_valid_outcome and row.rank <= limit and not row.breakout_label_default
    ]
    rows.sort(key=lambda row: (row.feature_season, row.rank, row.player_id))
    return "\n".join(
        [
            "# WR False Positives",
            "",
            f"Non-breakout players who still appeared in the top {limit} ranks for their feature season.",
            "",
            _markdown_table(rows, include_reason=True),
            "",
        ]
    )


def build_false_negatives_markdown(scored_candidates: Iterable[ScoredCandidate], cutoff: int = 30) -> str:
    rows = [
        row
        for row in scored_candidates
        if row.has_valid_outcome and row.breakout_label_default and row.rank > cutoff
    ]
    rows.sort(key=lambda row: (row.feature_season, row.rank, row.player_id))
    return "\n".join(
        [
            "# WR False Negatives",
            "",
            f"Actual breakout labels that landed outside the top {cutoff} ranks for their feature season.",
            "",
            _markdown_table(rows, include_reason=True),
            "",
        ]
    )


def _score_candidate(row: dict[str, object], recipe: SignalRecipe = DEFAULT_RECIPE) -> dict[str, object]:
    feature_row = _feature_only_view(row)
    thresholds = recipe.thresholds

    feature_games_played = int(feature_row["feature_games_played"])
    feature_total_ppr = float(feature_row["feature_total_ppr"])
    feature_ppg = float(feature_row["feature_ppg"])
    feature_finish = int(feature_row["feature_finish"])
    feature_targets_per_game = float(feature_row["feature_targets_per_game"])
    feature_target_share = float(feature_row["feature_target_share"] or 0.0)
    expected_ppg_baseline = float(feature_row["expected_ppg_baseline"])
    cohort_player_count = float(feature_row.get("cohort_player_count") or 0.0)
    expected_finish_from_cohort = _parse_optional_float(feature_row.get("expected_finish_from_cohort"))
    feature_ppg_minus_cohort_expected = _parse_optional_float(feature_row.get("feature_ppg_minus_cohort_expected")) or 0.0
    route_participation_season_avg = _parse_optional_float(feature_row.get("route_participation_season_avg")) or 0.0
    target_share_season_avg = _parse_optional_float(feature_row.get("target_share_season_avg")) or 0.0
    air_yard_share_season_avg = _parse_optional_float(feature_row.get("air_yard_share_season_avg")) or 0.0
    routes_consistency_index = _parse_optional_float(feature_row.get("routes_consistency_index")) or 0.0
    target_earning_index = _parse_optional_float(feature_row.get("target_earning_index")) or 0.0
    opportunity_concentration_score = _parse_optional_float(feature_row.get("opportunity_concentration_score")) or 0.0
    estimated_targets = max(feature_targets_per_game * max(feature_games_played, 1), 1.0)
    feature_ppg_per_target = feature_total_ppr / estimated_targets

    usage_signal = round(
        recipe.usage_weights["targets_per_game"]
        * _scaled(
            feature_targets_per_game,
            thresholds.usage_targets_per_game_floor,
            thresholds.usage_targets_per_game_ceiling,
        )
        + recipe.usage_weights["target_share"]
        * _scaled(
            feature_target_share,
            thresholds.usage_target_share_floor,
            thresholds.usage_target_share_ceiling,
        ),
        4,
    )
    efficiency_signal = round(
        recipe.efficiency_weights["ppg_per_target"]
        * _scaled(
            feature_ppg_per_target,
            thresholds.efficiency_ppg_per_target_floor,
            thresholds.efficiency_ppg_per_target_ceiling,
        )
        + recipe.efficiency_weights["ppg"]
        * _scaled(feature_ppg, thresholds.efficiency_ppg_floor, thresholds.efficiency_ppg_ceiling),
        4,
    )
    development_signal = round(
        recipe.development_weights["finish_room"]
        * _scaled(
            thresholds.development_finish_anchor - feature_finish,
            thresholds.development_finish_floor,
            thresholds.development_finish_ceiling,
        )
        + recipe.development_weights["expected_gap"]
        * _scaled(
            expected_ppg_baseline - feature_ppg,
            thresholds.development_expected_gap_floor,
            thresholds.development_expected_gap_ceiling,
        ),
        4,
    )
    cohort_finish_room = (
        expected_finish_from_cohort - feature_finish if expected_finish_from_cohort is not None else 0.0
    )

    stability_signal = round(
        recipe.stability_weights["games_played"]
        * _scaled(feature_games_played, thresholds.stability_games_floor, thresholds.stability_games_ceiling)
        + recipe.stability_weights["total_ppr"]
        * _scaled(feature_total_ppr, thresholds.stability_total_ppr_floor, thresholds.stability_total_ppr_ceiling),
        4,
    )
    cohort_signal = round(
        recipe.cohort_weights["ppg_delta"]
        * _scaled(
            feature_ppg_minus_cohort_expected,
            thresholds.cohort_ppg_delta_floor,
            thresholds.cohort_ppg_delta_ceiling,
        )
        + recipe.cohort_weights["finish_delta"]
        * _scaled(
            cohort_finish_room,
            thresholds.cohort_finish_delta_floor,
            thresholds.cohort_finish_delta_ceiling,
        )
        + recipe.cohort_weights["cohort_count"]
        * _scaled(
            cohort_player_count,
            thresholds.cohort_count_floor,
            thresholds.cohort_count_ceiling,
        ),
        4,
    )
    role_signal = round(
        recipe.role_weights["route_participation"]
        * _scaled(
            route_participation_season_avg,
            thresholds.role_route_participation_floor,
            thresholds.role_route_participation_ceiling,
        )
        + recipe.role_weights["target_share"]
        * _scaled(
            target_share_season_avg,
            thresholds.role_target_share_floor,
            thresholds.role_target_share_ceiling,
        )
        + recipe.role_weights["air_yard_share"]
        * _scaled(
            air_yard_share_season_avg,
            thresholds.role_air_yard_share_floor,
            thresholds.role_air_yard_share_ceiling,
        )
        + recipe.role_weights["routes_consistency"]
        * _scaled(
            routes_consistency_index,
            thresholds.role_routes_consistency_floor,
            thresholds.role_routes_consistency_ceiling,
        )
        + recipe.role_weights["target_earning_index"]
        * _scaled(
            target_earning_index,
            thresholds.role_target_earning_floor,
            thresholds.role_target_earning_ceiling,
        )
        + recipe.role_weights["opportunity_concentration"]
        * _scaled(
            opportunity_concentration_score,
            thresholds.role_opportunity_concentration_floor,
            thresholds.role_opportunity_concentration_ceiling,
        ),
        4,
    )
    penalty_signal = round(
        recipe.penalty_weights["already_elite"]
        * _scaled(
            thresholds.penalty_finish_anchor - feature_finish,
            thresholds.penalty_finish_floor,
            thresholds.penalty_finish_ceiling,
        )
        + recipe.penalty_weights["missed_games"]
        * _scaled(
            thresholds.penalty_games_anchor - feature_games_played,
            thresholds.penalty_games_floor,
            thresholds.penalty_games_ceiling,
        )
        + recipe.penalty_weights["thin_share"]
        * _scaled(
            thresholds.penalty_target_share_anchor - feature_target_share,
            thresholds.penalty_target_share_floor,
            thresholds.penalty_target_share_ceiling,
        ),
        4,
    )
    wr_signal_score = round(
        usage_signal * recipe.component_weights["usage_signal"]
        + efficiency_signal * recipe.component_weights["efficiency_signal"]
        + development_signal * recipe.component_weights["development_signal"]
        + stability_signal * recipe.component_weights["stability_signal"]
        + cohort_signal * recipe.component_weights["cohort_signal"]
        + role_signal * recipe.component_weights["role_signal"]
        + penalty_signal * recipe.component_weights["penalty_signal"],
        4,
    )

    return {
        **row,
        "usage_signal": usage_signal,
        "efficiency_signal": efficiency_signal,
        "development_signal": development_signal,
        "stability_signal": stability_signal,
        "cohort_signal": cohort_signal,
        "role_signal": role_signal,
        "penalty_signal": penalty_signal,
        "wr_signal_score": wr_signal_score,
    }


def _feature_only_view(row: dict[str, object]) -> dict[str, object]:
    missing = [column for column in REQUIRED_FEATURE_COLUMNS if column not in row]
    if missing:
        raise ValueError(f"score row is missing required feature columns: {sorted(missing)}")
    return dict(row)


def _scaled(value: float, floor: float, ceiling: float) -> float:
    if ceiling <= floor:
        raise ValueError("ceiling must be greater than floor")
    bounded = min(max(value, floor), ceiling)
    return round(((bounded - floor) / (ceiling - floor)) * 100.0, 4)


def _precision_at_n(rows: list[ScoredCandidate], n: int) -> float:
    top_rows = [row for row in rows if row.rank <= n]
    if not top_rows:
        return 0.0
    return round(sum(1 for row in top_rows if row.breakout_label_default) / len(top_rows), 4)


def _recall_at_n(breakouts: list[ScoredCandidate], n: int) -> float:
    if not breakouts:
        return 0.0
    return round(sum(1 for row in breakouts if row.rank <= n) / len(breakouts), 4)


def _average_rank(rows: list[ScoredCandidate]) -> float | None:
    if not rows:
        return None
    return round(sum(row.rank for row in rows) / len(rows), 4)


def _median_rank(rows: list[ScoredCandidate]) -> float | None:
    if not rows:
        return None
    return float(median([row.rank for row in rows]))


def _normalize_dataset_row(row: dict[str, str]) -> dict[str, object]:
    normalized = {
        "player_id": row["player_id"],
        "player_name": row["player_name"],
        "feature_season": int(row["feature_season"]),
        "outcome_season": int(row["outcome_season"]),
        "position": row["position"],
        "feature_team": row["feature_team"],
        "has_valid_outcome": _parse_bool(row["has_valid_outcome"]),
        "feature_games_played": int(row["feature_games_played"]),
        "feature_total_ppr": float(row["feature_total_ppr"]),
        "feature_ppg": float(row["feature_ppg"]),
        "feature_finish": int(row["feature_finish"]),
        "feature_targets_per_game": float(row["feature_targets_per_game"]),
        "feature_target_share": _parse_optional_float(row.get("feature_target_share", "")),
        "expected_ppg_baseline": float(row["expected_ppg_baseline"]),
        "cohort_player_count": _parse_optional_float(row.get("cohort_player_count", "")) or 0.0,
        "expected_ppg_from_cohort": _parse_optional_float(row.get("expected_ppg_from_cohort", "")),
        "expected_finish_from_cohort": _parse_optional_float(row.get("expected_finish_from_cohort", "")),
        "feature_ppg_minus_cohort_expected": _parse_optional_float(row.get("feature_ppg_minus_cohort_expected", "")),
        "actual_minus_cohort_expected_ppg": _parse_optional_float(row.get("actual_minus_cohort_expected_ppg", "")),
        "route_participation_season_avg": _parse_optional_float(row.get("route_participation_season_avg", "")),
        "target_share_season_avg": _parse_optional_float(row.get("target_share_season_avg", "")),
        "air_yard_share_season_avg": _parse_optional_float(row.get("air_yard_share_season_avg", "")),
        "routes_consistency_index": _parse_optional_float(row.get("routes_consistency_index", "")),
        "target_earning_index": _parse_optional_float(row.get("target_earning_index", "")),
        "opportunity_concentration_score": _parse_optional_float(row.get("opportunity_concentration_score", "")),
        "breakout_label_default": _parse_bool(row["breakout_label_default"]),
        "breakout_reason": row["breakout_reason"],
    }
    for key, value in row.items():
        if key not in normalized:
            normalized[key] = value
    return normalized


def _parse_bool(value: str) -> bool:
    return value.strip().lower() == "true"


def _parse_optional_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _serialize_value(row.get(field)) for field in fieldnames})


def _serialize_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.4f}"
    return value


def _markdown_table(rows: list[ScoredCandidate], include_reason: bool = False) -> str:
    if not rows:
        return "_No rows in this category._"
    if include_reason:
        header = "| feature_season | rank | player_id | player_name | score | breakout_label | breakout_reason |"
        separator = "| ---: | ---: | --- | --- | ---: | --- | --- |"
    else:
        header = "| feature_season | rank | player_id | player_name | score | breakout_label |"
        separator = "| ---: | ---: | --- | --- | ---: | --- |"

    lines = [header, separator]
    for row in rows:
        line = (
            f"| {row.feature_season} | {row.rank} | {row.player_id} | {row.player_name} "
            f"| {row.wr_signal_score:.4f} | {'true' if row.breakout_label_default else 'false'} |"
        )
        if include_reason:
            line = line[:-1] + f" {row.breakout_reason} |"
        lines.append(line)
    return "\n".join(lines)
