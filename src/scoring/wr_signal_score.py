"""Deterministic WR breakout signal scoring, ranking, and validation reporting."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Iterable

FEATURE_ONLY_COLUMNS = {
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

REQUIRED_DATASET_COLUMNS = FEATURE_ONLY_COLUMNS | {
    "has_valid_outcome",
    "breakout_label_default",
    "breakout_reason",
}

COMPONENT_WEIGHTS = {
    "usage_signal": 0.35,
    "efficiency_signal": 0.20,
    "development_signal": 0.20,
    "stability_signal": 0.15,
    "penalty_signal": -0.10,
}

SCORING_VERSION = "wr_signal_score_v1"
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
    "penalty_signal",
    "wr_signal_score",
    "scoring_version",
    "usage_formula_notes",
    "efficiency_formula_notes",
    "development_formula_notes",
    "stability_formula_notes",
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

    def component_row(self) -> dict[str, object]:
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
            "penalty_signal": self.penalty_signal,
            "wr_signal_score": self.wr_signal_score,
            "scoring_version": self.scoring_version,
            "usage_formula_notes": (
                "0.55*scale(feature_targets_per_game,4,10)+"
                "0.45*scale(feature_target_share,0.12,0.30)"
            ),
            "efficiency_formula_notes": (
                "0.60*scale(feature_ppg_per_target,0.8,2.5)+"
                "0.40*scale(feature_ppg,6,18)"
            ),
            "development_formula_notes": (
                "0.50*scale(48-feature_finish,0,36)+"
                "0.50*scale(expected_ppg_baseline-feature_ppg,0,4)"
            ),
            "stability_formula_notes": (
                "0.65*scale(feature_games_played,8,17)+"
                "0.35*scale(feature_total_ppr,80,260)"
            ),
            "penalty_formula_notes": (
                "0.60*scale(12-feature_finish,0,12)+"
                "0.25*scale(11-feature_games_played,0,11)+"
                "0.15*scale(0.14-feature_target_share,0,0.14)"
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
) -> ScoreArtifacts:
    """Score WR candidates from the PR3 validation dataset and write deterministic artifacts."""

    dataset_path = Path(validation_dataset_path)
    output_dir = Path(output_dir)
    rows = read_validation_dataset(dataset_path)
    scored_candidates = build_scored_candidates(rows)
    summary = build_validation_summary(scored_candidates)

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
    _write_csv(component_scores_path, COMPONENT_OUTPUT_COLUMNS, [row.component_row() for row in scored_candidates])
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


def build_scored_candidates(rows: Iterable[dict[str, object]]) -> list[ScoredCandidate]:
    by_season: dict[int, list[dict[str, object]]] = {}
    for row in rows:
        by_season.setdefault(int(row["feature_season"]), []).append(row)

    scored: list[ScoredCandidate] = []
    for feature_season, season_rows in sorted(by_season.items()):
        season_candidates = [_score_candidate(row) for row in season_rows]
        ordered = sorted(
            season_candidates,
            key=lambda row: (
                -row["wr_signal_score"],
                -row["usage_signal"],
                -row["efficiency_signal"],
                -row["development_signal"],
                -row["stability_signal"],
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
                    penalty_signal=float(row["penalty_signal"]),
                    wr_signal_score=float(row["wr_signal_score"]),
                    rank=rank,
                )
            )
    return scored


def build_validation_summary(scored_candidates: Iterable[ScoredCandidate]) -> dict[str, object]:
    rows = list(scored_candidates)
    evaluable_rows = [row for row in rows if row.has_valid_outcome]
    breakouts = [row for row in evaluable_rows if row.breakout_label_default]

    summary: dict[str, object] = {
        "position": "WR",
        "scoring_version": SCORING_VERSION,
        "candidate_count": len(rows),
        "evaluated_candidate_count": len(evaluable_rows),
        "breakout_count": len(breakouts),
        "feature_seasons": sorted({row.feature_season for row in rows}),
        "precision_at_10": _precision_at_n(evaluable_rows, 10),
        "precision_at_20": _precision_at_n(evaluable_rows, 20),
        "precision_at_30": _precision_at_n(evaluable_rows, 30),
        "recall_at_10": _recall_at_n(evaluable_rows, breakouts, 10),
        "recall_at_20": _recall_at_n(evaluable_rows, breakouts, 20),
        "recall_at_30": _recall_at_n(evaluable_rows, breakouts, 30),
        "average_rank_of_actual_breakouts": _average_rank(breakouts),
        "median_rank_of_actual_breakouts": _median_rank(breakouts),
        "false_positives_in_top_20": sum(
            1 for row in evaluable_rows if row.rank <= 20 and not row.breakout_label_default
        ),
        "false_negatives_outside_top_30": sum(
            1 for row in breakouts if row.rank > 30
        ),
        "evaluation_notes": {
            "top_n_metrics_only_include_rows_with_valid_outcomes": True,
            "ranks_are_assigned_within_each_feature_season": True,
            "score_inputs_are_feature_season_fields_only": True,
        },
        "component_weights": COMPONENT_WEIGHTS,
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


def _score_candidate(row: dict[str, object]) -> dict[str, object]:
    feature_row = _feature_only_view(row)

    feature_games_played = int(feature_row["feature_games_played"])
    feature_total_ppr = float(feature_row["feature_total_ppr"])
    feature_ppg = float(feature_row["feature_ppg"])
    feature_finish = int(feature_row["feature_finish"])
    feature_targets_per_game = float(feature_row["feature_targets_per_game"])
    feature_target_share = float(feature_row["feature_target_share"] or 0.0)
    expected_ppg_baseline = float(feature_row["expected_ppg_baseline"])
    estimated_targets = max(feature_targets_per_game * max(feature_games_played, 1), 1.0)
    feature_ppg_per_target = feature_total_ppr / estimated_targets

    usage_signal = round(
        0.55 * _scaled(feature_targets_per_game, 4.0, 10.0)
        + 0.45 * _scaled(feature_target_share, 0.12, 0.30),
        4,
    )
    efficiency_signal = round(
        0.60 * _scaled(feature_ppg_per_target, 0.8, 2.5)
        + 0.40 * _scaled(feature_ppg, 6.0, 18.0),
        4,
    )
    development_signal = round(
        0.50 * _scaled(48.0 - feature_finish, 0.0, 36.0)
        + 0.50 * _scaled(expected_ppg_baseline - feature_ppg, 0.0, 4.0),
        4,
    )
    stability_signal = round(
        0.65 * _scaled(feature_games_played, 8.0, 17.0)
        + 0.35 * _scaled(feature_total_ppr, 80.0, 260.0),
        4,
    )
    penalty_signal = round(
        0.60 * _scaled(12.0 - feature_finish, 0.0, 12.0)
        + 0.25 * _scaled(11.0 - feature_games_played, 0.0, 11.0)
        + 0.15 * _scaled(0.14 - feature_target_share, 0.0, 0.14),
        4,
    )
    wr_signal_score = round(
        usage_signal * COMPONENT_WEIGHTS["usage_signal"]
        + efficiency_signal * COMPONENT_WEIGHTS["efficiency_signal"]
        + development_signal * COMPONENT_WEIGHTS["development_signal"]
        + stability_signal * COMPONENT_WEIGHTS["stability_signal"]
        + penalty_signal * COMPONENT_WEIGHTS["penalty_signal"],
        4,
    )

    return {
        **row,
        "usage_signal": usage_signal,
        "efficiency_signal": efficiency_signal,
        "development_signal": development_signal,
        "stability_signal": stability_signal,
        "penalty_signal": penalty_signal,
        "wr_signal_score": wr_signal_score,
    }


def _feature_only_view(row: dict[str, object]) -> dict[str, object]:
    missing = [column for column in FEATURE_ONLY_COLUMNS if column not in row]
    if missing:
        raise ValueError(f"score row is missing required feature columns: {sorted(missing)}")
    return {column: row[column] for column in FEATURE_ONLY_COLUMNS}


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


def _recall_at_n(rows: list[ScoredCandidate], breakouts: list[ScoredCandidate], n: int) -> float:
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
