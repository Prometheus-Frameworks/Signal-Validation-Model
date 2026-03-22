"""Deterministic cohort-baseline enrichment for WR validation datasets."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Iterable

from src.labels.wr_breakouts import WR_VALIDATION_DATASET_COLUMNS
from src.validation import ValidationError

CAREER_YEAR_BUCKET_DEFINITIONS = {
    "yr1": "First recorded WR feature season for the player.",
    "yr2": "Second recorded WR feature season for the player.",
    "yr3": "Third recorded WR feature season for the player.",
    "yr4_plus": "Fourth or later recorded WR feature season for the player.",
}

AGE_BUCKET_DEFINITIONS = {
    "age_21_or_younger": "Age on Sept. 1 is less than 22.0 when present.",
    "age_22_to_24": "Age on Sept. 1 is at least 22.0 and less than 25.0 when present.",
    "age_25_to_27": "Age on Sept. 1 is at least 25.0 and less than 28.0 when present.",
    "age_28_plus": "Age on Sept. 1 is at least 28.0 when present.",
    "age_unknown": "Age is not available in the current processed WR tables, so the row is grouped into an explicit unknown bucket.",
}

COHORT_DATASET_COLUMNS = WR_VALIDATION_DATASET_COLUMNS + [
    "career_year",
    "career_year_bucket",
    "age_bucket",
    "cohort_key",
    "cohort_player_count",
    "expected_ppg_from_cohort",
    "expected_finish_from_cohort",
    "feature_ppg_minus_cohort_expected",
    "outcome_ppg_minus_cohort_expected",
    "actual_minus_cohort_expected_ppg",
]


@dataclass(frozen=True)
class CohortArtifacts:
    enriched_dataset_path: Path
    summary_path: Path
    examples_path: Path


@dataclass(frozen=True)
class CohortAssignment:
    player_id: str
    player_name: str
    feature_season: int
    position: str
    career_year: int
    career_year_bucket: str
    age_bucket: str

    @property
    def cohort_key(self) -> str:
        return f"{self.position}|{self.career_year_bucket}|{self.age_bucket}"


@dataclass(frozen=True)
class CohortObservation:
    cohort_key: str
    historical_feature_season: int
    player_id: str
    feature_ppg: float
    outcome_ppg: float | None
    outcome_finish: int | None



def write_wr_cohort_outputs(
    processed_dir: str | Path,
    validation_dataset_path: str | Path,
    output_dir: str | Path,
) -> CohortArtifacts:
    processed_dir = Path(processed_dir)
    validation_dataset_path = Path(validation_dataset_path)
    output_dir = Path(output_dir)

    if not validation_dataset_path.exists():
        raise ValidationError(f"validation dataset does not exist: {validation_dataset_path}")

    feature_rows = _read_csv_rows(processed_dir / "wr_feature_seasons.csv")
    validation_rows = _read_csv_rows(validation_dataset_path)
    enriched_rows = enrich_wr_validation_dataset(feature_rows=feature_rows, validation_rows=validation_rows)
    summary = build_cohort_summary(enriched_rows)
    examples = build_cohort_examples_markdown(enriched_rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    enriched_dataset_path = output_dir / "wr_validation_dataset_enriched.csv"
    summary_path = output_dir / "wr_cohort_baseline_summary.json"
    examples_path = output_dir / "wr_cohort_examples.md"

    _write_csv(enriched_dataset_path, COHORT_DATASET_COLUMNS, enriched_rows)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    examples_path.write_text(examples, encoding="utf-8")

    return CohortArtifacts(
        enriched_dataset_path=enriched_dataset_path,
        summary_path=summary_path,
        examples_path=examples_path,
    )



def enrich_wr_validation_dataset(
    feature_rows: Iterable[dict[str, object]],
    validation_rows: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    assignments = assign_wr_cohorts(feature_rows)
    validation = [_normalize_validation_row(row) for row in validation_rows]
    observations = _build_historical_observations(validation, assignments)

    enriched_rows: list[dict[str, object]] = []
    for row in sorted(validation, key=lambda item: (int(item["feature_season"]), str(item["player_id"]))):
        key = (str(row["player_id"]), int(row["feature_season"]))
        if key not in assignments:
            raise ValidationError(f"missing cohort assignment for validation row {key}")
        assignment = assignments[key]
        baseline = _compute_cohort_baseline(
            row=row,
            assignment=assignment,
            observations=observations.get(assignment.cohort_key, []),
        )
        enriched_rows.append(
            {
                **row,
                "career_year": assignment.career_year,
                "career_year_bucket": assignment.career_year_bucket,
                "age_bucket": assignment.age_bucket,
                "cohort_key": assignment.cohort_key,
                **baseline,
            }
        )
    return [{column: row[column] for column in COHORT_DATASET_COLUMNS} for row in enriched_rows]



def assign_wr_cohorts(feature_rows: Iterable[dict[str, object]]) -> dict[tuple[str, int], CohortAssignment]:
    normalized = [_normalize_feature_row(row) for row in feature_rows]
    by_player: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in normalized:
        by_player[str(row["player_id"])].append(row)

    assignments: dict[tuple[str, int], CohortAssignment] = {}
    for player_id, rows in sorted(by_player.items()):
        ordered = sorted(rows, key=lambda item: (int(item["season"]), str(item["player_id"])))
        for index, row in enumerate(ordered, start=1):
            feature_season = int(row["season"])
            assignment = CohortAssignment(
                player_id=player_id,
                player_name=str(row["player_name"]),
                feature_season=feature_season,
                position=str(row["position"]),
                career_year=index,
                career_year_bucket=_career_year_bucket(index),
                age_bucket=_age_bucket(_parse_optional_float(row.get("age_on_sept_1"))),
            )
            assignments[(player_id, feature_season)] = assignment
    return assignments



def build_cohort_summary(rows: Iterable[dict[str, object]]) -> dict[str, object]:
    ordered_rows = list(rows)
    bucket_counts: dict[str, int] = defaultdict(int)
    season_coverage: dict[int, dict[str, int]] = defaultdict(lambda: {"row_count": 0, "rows_with_history": 0})
    example_cohorts: dict[str, list[dict[str, object]]] = defaultdict(list)

    for row in ordered_rows:
        bucket_counts[str(row["cohort_key"])] += 1
        season = int(row["feature_season"])
        season_coverage[season]["row_count"] += 1
        if int(row["cohort_player_count"]) > 0:
            season_coverage[season]["rows_with_history"] += 1
        if len(example_cohorts[str(row["cohort_key"])]) < 3:
            example_cohorts[str(row["cohort_key"])].append(
                {
                    "player_id": row["player_id"],
                    "player_name": row["player_name"],
                    "feature_season": row["feature_season"],
                    "expected_ppg_from_cohort": row["expected_ppg_from_cohort"],
                    "outcome_ppg_minus_cohort_expected": row["outcome_ppg_minus_cohort_expected"],
                }
            )

    history_counts = [int(row["cohort_player_count"]) for row in ordered_rows]
    rows_with_history = [count for count in history_counts if count > 0]
    return {
        "position": "WR",
        "row_count": len(ordered_rows),
        "feature_seasons": sorted({int(row["feature_season"]) for row in ordered_rows}),
        "bucket_definitions": {
            "position": {"WR": "All rows are restricted to WRs."},
            "career_year_bucket": CAREER_YEAR_BUCKET_DEFINITIONS,
            "age_bucket": AGE_BUCKET_DEFINITIONS,
        },
        "leakage_guardrails": {
            "historical_rows_only": True,
            "rule": "Each feature-season row uses only cohort observations with feature_season strictly less than the current feature_season.",
            "position_locked_to_wr": True,
        },
        "cohort_history_coverage": {
            "rows_with_any_historical_cohort": len(rows_with_history),
            "rows_without_historical_cohort": len(ordered_rows) - len(rows_with_history),
            "max_historical_peer_count": max(history_counts) if history_counts else 0,
            "median_historical_peer_count": float(median(history_counts)) if history_counts else 0.0,
        },
        "season_coverage": {str(season): values for season, values in sorted(season_coverage.items())},
        "cohort_counts": dict(sorted(bucket_counts.items())),
        "cohort_examples": dict(sorted(example_cohorts.items())),
    }



def build_cohort_examples_markdown(rows: Iterable[dict[str, object]]) -> str:
    ordered_rows = sorted(
        list(rows),
        key=lambda row: (
            -int(row["cohort_player_count"]),
            row["career_year_bucket"],
            row["feature_season"],
            row["player_id"],
        ),
    )
    with_history = [row for row in ordered_rows if int(row["cohort_player_count"]) > 0][:8]
    without_history = [row for row in ordered_rows if int(row["cohort_player_count"]) == 0][:5]
    positive_delta = [
        row
        for row in ordered_rows
        if row["outcome_ppg_minus_cohort_expected"] is not None and float(row["outcome_ppg_minus_cohort_expected"]) > 0
    ][:5]

    return "\n".join(
        [
            "# WR Cohort Baseline Examples",
            "",
            "The examples below show deterministic cohort-relative context derived only from earlier feature seasons.",
            "",
            "## Rows with historical cohort coverage",
            _examples_table(with_history),
            "",
            "## Rows without historical cohort coverage",
            _examples_table(without_history),
            "",
            "## Positive outcome-vs-cohort deltas",
            _examples_table(positive_delta),
            "",
        ]
    )



def _compute_cohort_baseline(
    row: dict[str, object],
    assignment: CohortAssignment,
    observations: list[CohortObservation],
) -> dict[str, object]:
    eligible = [obs for obs in observations if obs.historical_feature_season < int(row["feature_season"])]
    expected_ppg = _mean([obs.outcome_ppg for obs in eligible if obs.outcome_ppg is not None])
    expected_finish = _mean([float(obs.outcome_finish) for obs in eligible if obs.outcome_finish is not None])
    cohort_player_count = len({obs.player_id for obs in eligible})
    feature_ppg = float(row["feature_ppg"])
    outcome_ppg = row["outcome_ppg"]
    feature_delta = round(feature_ppg - expected_ppg, 4) if expected_ppg is not None else None
    outcome_delta = round(float(outcome_ppg) - expected_ppg, 4) if expected_ppg is not None and outcome_ppg is not None else None
    return {
        "cohort_player_count": cohort_player_count,
        "expected_ppg_from_cohort": expected_ppg,
        "expected_finish_from_cohort": round(expected_finish, 4) if expected_finish is not None else None,
        "feature_ppg_minus_cohort_expected": feature_delta,
        "outcome_ppg_minus_cohort_expected": outcome_delta,
        "actual_minus_cohort_expected_ppg": outcome_delta,
    }



def _build_historical_observations(
    rows: Iterable[dict[str, object]],
    assignments: dict[tuple[str, int], CohortAssignment],
) -> dict[str, list[CohortObservation]]:
    observations: dict[str, list[CohortObservation]] = defaultdict(list)
    for row in rows:
        key = (str(row["player_id"]), int(row["feature_season"]))
        assignment = assignments.get(key)
        if assignment is None:
            continue
        observations[assignment.cohort_key].append(
            CohortObservation(
                cohort_key=assignment.cohort_key,
                historical_feature_season=int(row["feature_season"]),
                player_id=str(row["player_id"]),
                feature_ppg=float(row["feature_ppg"]),
                outcome_ppg=float(row["outcome_ppg"]) if row["outcome_ppg"] is not None else None,
                outcome_finish=int(row["outcome_finish"]) if row["outcome_finish"] is not None else None,
            )
        )
    return observations



def _examples_table(rows: list[dict[str, object]]) -> str:
    if not rows:
        return "_No rows in this category._"
    lines = [
        "| feature_season | player_id | career_year_bucket | age_bucket | cohort_count | expected_ppg | feature_minus_expected | outcome_minus_expected |",
        "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {feature_season} | {player_id} | {career_year_bucket} | {age_bucket} | {cohort_player_count} | {expected_ppg} | {feature_delta} | {outcome_delta} |".format(
                feature_season=row["feature_season"],
                player_id=row["player_id"],
                career_year_bucket=row["career_year_bucket"],
                age_bucket=row["age_bucket"],
                cohort_player_count=row["cohort_player_count"],
                expected_ppg=_format_metric(row["expected_ppg_from_cohort"]),
                feature_delta=_format_metric(row["feature_ppg_minus_cohort_expected"]),
                outcome_delta=_format_metric(row["outcome_ppg_minus_cohort_expected"]),
            )
        )
    return "\n".join(lines)



def _career_year_bucket(career_year: int) -> str:
    if career_year <= 1:
        return "yr1"
    if career_year == 2:
        return "yr2"
    if career_year == 3:
        return "yr3"
    return "yr4_plus"



def _age_bucket(age_on_sept_1: float | None) -> str:
    if age_on_sept_1 is None:
        return "age_unknown"
    if age_on_sept_1 < 22.0:
        return "age_21_or_younger"
    if age_on_sept_1 < 25.0:
        return "age_22_to_24"
    if age_on_sept_1 < 28.0:
        return "age_25_to_27"
    return "age_28_plus"



def _normalize_feature_row(row: dict[str, object]) -> dict[str, object]:
    normalized = dict(row)
    normalized["player_id"] = str(row["player_id"])
    normalized["player_name"] = str(row["player_name"])
    normalized["season"] = int(row["season"])
    normalized["position"] = str(row["position"])
    if normalized["position"] != "WR":
        raise ValidationError("cohort baseline generation only supports WR rows")
    return normalized



def _normalize_validation_row(row: dict[str, object]) -> dict[str, object]:
    normalized = dict(row)
    normalized["player_id"] = str(row["player_id"])
    normalized["player_name"] = str(row["player_name"])
    normalized["feature_season"] = int(row["feature_season"])
    normalized["outcome_season"] = int(row["outcome_season"])
    normalized["position"] = str(row["position"])
    normalized["has_valid_outcome"] = _parse_bool(row["has_valid_outcome"])
    normalized["feature_games_played"] = int(row["feature_games_played"])
    normalized["feature_total_ppr"] = float(row["feature_total_ppr"])
    normalized["feature_ppg"] = float(row["feature_ppg"])
    normalized["feature_finish"] = int(row["feature_finish"])
    normalized["feature_targets_per_game"] = float(row["feature_targets_per_game"])
    normalized["feature_target_share"] = _parse_optional_float(row.get("feature_target_share"))
    normalized["expected_ppg_baseline"] = float(row["expected_ppg_baseline"])
    normalized["breakout_label_default"] = _parse_bool(row["breakout_label_default"])
    normalized["breakout_label_ppg_jump"] = _parse_bool(row["breakout_label_ppg_jump"])
    normalized["breakout_label_top24_jump"] = _parse_bool(row["breakout_label_top24_jump"])
    normalized["outcome_ppg"] = _parse_optional_float(row.get("outcome_ppg"))
    normalized["outcome_finish"] = _parse_optional_int(row.get("outcome_finish"))
    normalized["outcome_games_played"] = _parse_optional_int(row.get("outcome_games_played"))
    normalized["outcome_total_ppr"] = _parse_optional_float(row.get("outcome_total_ppr"))
    normalized["ppg_delta_next_season"] = _parse_optional_float(row.get("ppg_delta_next_season"))
    normalized["finish_delta_next_season"] = _parse_optional_int(row.get("finish_delta_next_season"))
    normalized["outcome_targets_per_game"] = _parse_optional_float(row.get("outcome_targets_per_game"))
    normalized["actual_minus_expected_ppg"] = _parse_optional_float(row.get("actual_minus_expected_ppg"))
    normalized["is_new_fantasy_starter"] = _parse_bool(row["is_new_fantasy_starter"])
    return normalized



def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ValidationError(f"required CSV does not exist: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValidationError(f"CSV must contain a header row: {path}")
        return list(reader)



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



def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)



def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"



def _parse_optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)



def _parse_optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(value)



def _format_metric(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.4f}"
