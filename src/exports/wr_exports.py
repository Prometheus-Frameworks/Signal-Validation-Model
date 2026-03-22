"""Deterministic downstream export adapters for WR breakout research artifacts."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.reporting.wr_case_study import load_best_recipe_from_summary
from src.scoring.recipe_comparison import BEST_RECIPE_RULE
from src.scoring.wr_signal_score import read_validation_dataset

EXPORT_SCHEMA_VERSION = "wr_exports_v1"
PLAYER_SIGNAL_CARD_COLUMNS = [
    "player_id",
    "player_name",
    "feature_season",
    "outcome_season",
    "feature_team",
    "best_recipe_name",
    "candidate_rank",
    "final_signal_score",
    "breakout_label_default",
    "breakout_reason",
    "usage_signal",
    "efficiency_signal",
    "development_signal",
    "stability_signal",
    "cohort_signal",
    "role_signal",
    "penalty_signal",
    "career_year",
    "career_year_bucket",
    "age_bucket",
    "cohort_key",
    "cohort_player_count",
    "feature_ppg",
    "feature_finish",
    "feature_targets_per_game",
    "feature_target_share",
    "expected_ppg_baseline",
    "route_participation_season_avg",
    "target_share_season_avg",
    "air_yard_share_season_avg",
    "routes_consistency_index",
    "target_earning_index",
    "opportunity_concentration_score",
    "has_valid_outcome",
]
CANDIDATE_BOARD_FIELDS = [
    "player_id",
    "player_name",
    "feature_season",
    "outcome_season",
    "best_recipe_name",
    "candidate_rank",
    "final_signal_score",
    "breakout_label_default",
    "breakout_reason",
    "component_scores",
    "cohort_context",
    "role_context",
    "source_artifacts",
]


@dataclass(frozen=True)
class ExportArtifacts:
    breakout_candidates_path: Path
    best_recipe_summary_path: Path
    case_study_summary_path: Path
    player_signal_cards_path: Path
    manifest_path: Path


@dataclass(frozen=True)
class ExportInputPaths:
    validation_dataset_path: Path
    comparison_summary_path: Path
    candidate_dir: Path
    case_study_dir: Path
    output_dir: Path


def export_wr_results(
    validation_dataset_path: str | Path,
    comparison_summary_path: str | Path,
    candidate_dir: str | Path,
    case_study_dir: str | Path,
    output_dir: str | Path,
    feature_season: int,
    outcome_season: int,
    generated_at: str | None = None,
) -> ExportArtifacts:
    """Build canonical downstream WR export artifacts using existing validated outputs only."""

    paths = ExportInputPaths(
        validation_dataset_path=Path(validation_dataset_path),
        comparison_summary_path=Path(comparison_summary_path),
        candidate_dir=Path(candidate_dir),
        case_study_dir=Path(case_study_dir),
        output_dir=Path(output_dir),
    )
    paths.output_dir.mkdir(parents=True, exist_ok=True)

    created_at = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    validation_rows = read_validation_dataset(paths.validation_dataset_path)
    best_recipe = load_best_recipe_from_summary(paths.comparison_summary_path)
    comparison_summary = json.loads(paths.comparison_summary_path.read_text(encoding="utf-8"))

    candidate_rows = _read_csv_dicts(paths.candidate_dir / f"wr_candidate_rankings_{best_recipe.recipe_name}.csv")
    component_rows = _read_csv_dicts(paths.candidate_dir / f"wr_signal_component_scores_{best_recipe.recipe_name}.csv")
    case_study_winner = json.loads(
        (paths.case_study_dir / f"wr_recipe_winner_{feature_season}_to_{outcome_season}.json").read_text(encoding="utf-8")
    )
    hits_rows = _read_csv_dicts(paths.case_study_dir / f"wr_breakout_hits_{feature_season}_to_{outcome_season}.csv")
    false_positive_rows = _read_csv_dicts(
        paths.case_study_dir / f"wr_breakout_false_positives_{feature_season}_to_{outcome_season}.csv"
    )
    false_negative_rows = _read_csv_dicts(
        paths.case_study_dir / f"wr_breakout_false_negatives_{feature_season}_to_{outcome_season}.csv"
    )

    validation_by_key = {
        _row_key(row): row
        for row in validation_rows
        if int(row["feature_season"]) == feature_season and int(row["outcome_season"]) == outcome_season
    }
    candidate_by_key = {
        _row_key(row): row
        for row in candidate_rows
        if int(row["feature_season"]) == feature_season and int(row["outcome_season"]) == outcome_season
    }
    component_by_key = {
        _row_key(row): row
        for row in component_rows
        if int(row["feature_season"]) == feature_season and int(row["outcome_season"]) == outcome_season
    }

    merged_cards = []
    for key in sorted(candidate_by_key, key=lambda item: (int(candidate_by_key[item]["rank"]), str(item[0]))):
        if key not in validation_by_key:
            continue
        if key not in component_by_key:
            raise ValueError(f"missing component score row for {key}")
        merged_cards.append(
            _build_player_signal_card_row(
                validation_row=validation_by_key[key],
                candidate_row=candidate_by_key[key],
                component_row=component_by_key[key],
                best_recipe_name=best_recipe.recipe_name,
            )
        )

    if not merged_cards:
        raise ValueError(f"no candidate rows found for season pair {feature_season} -> {outcome_season}")

    breakout_candidates = [_build_candidate_board_entry(row, paths) for row in merged_cards]
    best_recipe_summary = _build_best_recipe_summary(
        comparison_summary=comparison_summary,
        best_recipe_name=best_recipe.recipe_name,
        generated_at=created_at,
        source_paths=paths,
    )
    case_study_summary = _build_case_study_summary(
        case_study_winner=case_study_winner,
        hits_rows=hits_rows,
        false_positive_rows=false_positive_rows,
        false_negative_rows=false_negative_rows,
        all_cards=merged_cards,
        generated_at=created_at,
        best_recipe_name=best_recipe.recipe_name,
        source_paths=paths,
    )
    manifest = _build_manifest(
        paths=paths,
        feature_season=feature_season,
        outcome_season=outcome_season,
        best_recipe_name=best_recipe.recipe_name,
        generated_at=created_at,
        breakout_candidates=breakout_candidates,
        case_study_summary=case_study_summary,
    )

    breakout_candidates_path = paths.output_dir / "wr_breakout_candidates_latest.json"
    best_recipe_summary_path = paths.output_dir / "wr_best_recipe_summary.json"
    case_study_summary_path = paths.output_dir / f"wr_case_study_summary_{feature_season}_to_{outcome_season}.json"
    player_signal_cards_path = paths.output_dir / f"wr_player_signal_cards_{feature_season}.csv"
    manifest_path = paths.output_dir / "export_manifest.json"

    breakout_candidates_path.write_text(
        json.dumps(
            {
                "export_name": "wr_breakout_candidates_latest",
                "schema_version": EXPORT_SCHEMA_VERSION,
                "position": "WR",
                "feature_season": feature_season,
                "outcome_season": outcome_season,
                "best_recipe_name": best_recipe.recipe_name,
                "candidate_count": len(breakout_candidates),
                "candidates": breakout_candidates,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    best_recipe_summary_path.write_text(json.dumps(best_recipe_summary, indent=2) + "\n", encoding="utf-8")
    case_study_summary_path.write_text(json.dumps(case_study_summary, indent=2) + "\n", encoding="utf-8")
    _write_csv(player_signal_cards_path, PLAYER_SIGNAL_CARD_COLUMNS, merged_cards)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return ExportArtifacts(
        breakout_candidates_path=breakout_candidates_path,
        best_recipe_summary_path=best_recipe_summary_path,
        case_study_summary_path=case_study_summary_path,
        player_signal_cards_path=player_signal_cards_path,
        manifest_path=manifest_path,
    )


def _build_player_signal_card_row(
    *,
    validation_row: dict[str, Any],
    candidate_row: dict[str, Any],
    component_row: dict[str, Any],
    best_recipe_name: str,
) -> dict[str, Any]:
    return {
        "player_id": str(validation_row["player_id"]),
        "player_name": str(validation_row["player_name"]),
        "feature_season": int(validation_row["feature_season"]),
        "outcome_season": int(validation_row["outcome_season"]),
        "feature_team": str(validation_row["feature_team"]),
        "best_recipe_name": best_recipe_name,
        "candidate_rank": int(candidate_row["rank"]),
        "final_signal_score": float(candidate_row["wr_signal_score"]),
        "breakout_label_default": bool(validation_row["breakout_label_default"]),
        "breakout_reason": str(validation_row["breakout_reason"]),
        "usage_signal": float(component_row["usage_signal"]),
        "efficiency_signal": float(component_row["efficiency_signal"]),
        "development_signal": float(component_row["development_signal"]),
        "stability_signal": float(component_row["stability_signal"]),
        "cohort_signal": float(component_row["cohort_signal"]),
        "role_signal": float(component_row["role_signal"]),
        "penalty_signal": float(component_row["penalty_signal"]),
        "career_year": int(validation_row["career_year"]),
        "career_year_bucket": str(validation_row["career_year_bucket"]),
        "age_bucket": str(validation_row["age_bucket"]),
        "cohort_key": str(validation_row["cohort_key"]),
        "cohort_player_count": int(validation_row["cohort_player_count"]),
        "feature_ppg": float(validation_row["feature_ppg"]),
        "feature_finish": int(validation_row["feature_finish"]),
        "feature_targets_per_game": float(validation_row["feature_targets_per_game"]),
        "feature_target_share": _optional_float(validation_row.get("feature_target_share")),
        "expected_ppg_baseline": float(validation_row["expected_ppg_baseline"]),
        "route_participation_season_avg": _optional_float(validation_row.get("route_participation_season_avg")),
        "target_share_season_avg": _optional_float(validation_row.get("target_share_season_avg")),
        "air_yard_share_season_avg": _optional_float(validation_row.get("air_yard_share_season_avg")),
        "routes_consistency_index": _optional_float(validation_row.get("routes_consistency_index")),
        "target_earning_index": _optional_float(validation_row.get("target_earning_index")),
        "opportunity_concentration_score": _optional_float(validation_row.get("opportunity_concentration_score")),
        "has_valid_outcome": bool(validation_row["has_valid_outcome"]),
    }


def _build_candidate_board_entry(row: dict[str, Any], paths: ExportInputPaths) -> dict[str, Any]:
    return {
        "player_id": row["player_id"],
        "player_name": row["player_name"],
        "feature_season": row["feature_season"],
        "outcome_season": row["outcome_season"],
        "best_recipe_name": row["best_recipe_name"],
        "candidate_rank": row["candidate_rank"],
        "final_signal_score": row["final_signal_score"],
        "breakout_label_default": row["breakout_label_default"],
        "breakout_reason": row["breakout_reason"],
        "component_scores": {
            "usage_signal": row["usage_signal"],
            "efficiency_signal": row["efficiency_signal"],
            "development_signal": row["development_signal"],
            "stability_signal": row["stability_signal"],
            "cohort_signal": row["cohort_signal"],
            "role_signal": row["role_signal"],
            "penalty_signal": row["penalty_signal"],
        },
        "cohort_context": {
            "career_year": row["career_year"],
            "career_year_bucket": row["career_year_bucket"],
            "age_bucket": row["age_bucket"],
            "cohort_key": row["cohort_key"],
            "cohort_player_count": row["cohort_player_count"],
            "expected_ppg_baseline": row["expected_ppg_baseline"],
        },
        "role_context": {
            "feature_team": row["feature_team"],
            "feature_ppg": row["feature_ppg"],
            "feature_finish": row["feature_finish"],
            "feature_targets_per_game": row["feature_targets_per_game"],
            "feature_target_share": row["feature_target_share"],
            "route_participation_season_avg": row["route_participation_season_avg"],
            "target_share_season_avg": row["target_share_season_avg"],
            "air_yard_share_season_avg": row["air_yard_share_season_avg"],
            "routes_consistency_index": row["routes_consistency_index"],
            "target_earning_index": row["target_earning_index"],
            "opportunity_concentration_score": row["opportunity_concentration_score"],
        },
        "source_artifacts": {
            "validation_dataset_path": str(paths.validation_dataset_path),
            "comparison_summary_path": str(paths.comparison_summary_path),
            "candidate_dir": str(paths.candidate_dir),
        },
    }


def _build_best_recipe_summary(
    *,
    comparison_summary: dict[str, Any],
    best_recipe_name: str,
    generated_at: str,
    source_paths: ExportInputPaths,
) -> dict[str, Any]:
    best_recipe = dict(comparison_summary["best_recipe"])
    metrics = dict(best_recipe["metrics"])
    return {
        "export_name": "wr_best_recipe_summary",
        "schema_version": EXPORT_SCHEMA_VERSION,
        "position": "WR",
        "best_recipe_name": best_recipe_name,
        "recipe_family": metrics.get("recipe_family"),
        "best_recipe_selection_rule": comparison_summary.get("best_recipe_rule", BEST_RECIPE_RULE),
        "key_metrics": {
            "candidate_count": metrics.get("candidate_count"),
            "breakout_count": metrics.get("breakout_count"),
            "precision_at_10": metrics.get("precision_at_10"),
            "precision_at_20": metrics.get("precision_at_20"),
            "precision_at_30": metrics.get("precision_at_30"),
            "recall_at_10": metrics.get("recall_at_10"),
            "recall_at_20": metrics.get("recall_at_20"),
            "recall_at_30": metrics.get("recall_at_30"),
            "average_breakout_rank": metrics.get("average_breakout_rank"),
            "median_breakout_rank": metrics.get("median_breakout_rank"),
            "false_positives_in_top_20": metrics.get("false_positives_in_top_20"),
            "false_negatives_outside_top_30": metrics.get("false_negatives_outside_top_30"),
        },
        "scoring_version": best_recipe.get("scoring_version"),
        "generated_at": generated_at,
        "source_artifacts": {
            "validation_dataset_path": str(source_paths.validation_dataset_path),
            "comparison_summary_path": str(source_paths.comparison_summary_path),
        },
    }


def _build_case_study_summary(
    *,
    case_study_winner: dict[str, Any],
    hits_rows: list[dict[str, Any]],
    false_positive_rows: list[dict[str, Any]],
    false_negative_rows: list[dict[str, Any]],
    all_cards: list[dict[str, Any]],
    generated_at: str,
    best_recipe_name: str,
    source_paths: ExportInputPaths,
) -> dict[str, Any]:
    actual_breakout_names = [
        row["player_name"]
        for row in all_cards
        if bool(row["breakout_label_default"]) and bool(row["has_valid_outcome"])
    ]
    surfaced_names = [row["player_name"] for row in sorted(all_cards, key=lambda row: (row["candidate_rank"], row["player_id"]))[:10]]
    return {
        "export_name": "wr_case_study_summary",
        "schema_version": EXPORT_SCHEMA_VERSION,
        "position": "WR",
        "feature_season": case_study_winner["feature_season"],
        "outcome_season": case_study_winner["outcome_season"],
        "best_recipe_name": best_recipe_name,
        "hit_count": case_study_winner["season_pair_summary"]["hit_count"],
        "false_positive_count": case_study_winner["season_pair_summary"]["false_positive_count"],
        "false_negative_count": case_study_winner["season_pair_summary"]["false_negative_count"],
        "top_flagged_names": surfaced_names,
        "actual_breakout_names": sorted(actual_breakout_names),
        "hit_names": [row["player_name"] for row in hits_rows],
        "false_positive_names": [row["player_name"] for row in false_positive_rows],
        "false_negative_names": [row["player_name"] for row in false_negative_rows],
        "generated_at": generated_at,
        "source_artifacts": {
            "case_study_dir": str(source_paths.case_study_dir),
            "winner_summary_path": str(source_paths.case_study_dir / f"wr_recipe_winner_{case_study_winner['feature_season']}_to_{case_study_winner['outcome_season']}.json"),
        },
    }


def _build_manifest(
    *,
    paths: ExportInputPaths,
    feature_season: int,
    outcome_season: int,
    best_recipe_name: str,
    generated_at: str,
    breakout_candidates: list[dict[str, Any]],
    case_study_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "export_name": "wr_export_manifest",
        "schema_version": EXPORT_SCHEMA_VERSION,
        "position": "WR",
        "feature_season": feature_season,
        "outcome_season": outcome_season,
        "best_recipe_name": best_recipe_name,
        "generated_at": generated_at,
        "artifacts": [
            {
                "artifact_name": "wr_breakout_candidates_latest.json",
                "relative_path": "wr_breakout_candidates_latest.json",
                "format": "json",
                "record_count": len(breakout_candidates),
                "primary_keys": ["player_id", "feature_season", "outcome_season"],
            },
            {
                "artifact_name": "wr_best_recipe_summary.json",
                "relative_path": "wr_best_recipe_summary.json",
                "format": "json",
                "record_count": 1,
                "primary_keys": ["best_recipe_name"],
            },
            {
                "artifact_name": f"wr_case_study_summary_{feature_season}_to_{outcome_season}.json",
                "relative_path": f"wr_case_study_summary_{feature_season}_to_{outcome_season}.json",
                "format": "json",
                "record_count": 1,
                "primary_keys": ["feature_season", "outcome_season"],
            },
            {
                "artifact_name": f"wr_player_signal_cards_{feature_season}.csv",
                "relative_path": f"wr_player_signal_cards_{feature_season}.csv",
                "format": "csv",
                "record_count": len(breakout_candidates),
                "primary_keys": ["player_id", "feature_season", "outcome_season"],
                "field_order": PLAYER_SIGNAL_CARD_COLUMNS,
            },
        ],
        "input_artifacts": {
            "validation_dataset_path": str(paths.validation_dataset_path),
            "comparison_summary_path": str(paths.comparison_summary_path),
            "candidate_dir": str(paths.candidate_dir),
            "case_study_dir": str(paths.case_study_dir),
        },
        "season_pair_summary": {
            "hit_count": case_study_summary["hit_count"],
            "false_positive_count": case_study_summary["false_positive_count"],
            "false_negative_count": case_study_summary["false_negative_count"],
        },
    }


def _row_key(row: dict[str, Any]) -> tuple[str, int, int]:
    return (str(row["player_id"]), int(row["feature_season"]), int(row["outcome_season"]))


def _read_csv_dicts(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"required export source does not exist: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _serialize_value(row.get(field)) for field in fieldnames})


def _serialize_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.4f}"
    return value


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
