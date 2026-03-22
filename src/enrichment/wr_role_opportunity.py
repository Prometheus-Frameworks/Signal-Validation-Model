"""Deterministic WR role-and-opportunity enrichment for validation datasets."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Iterable

from src.enrichment.wr_cohort_baselines import COHORT_DATASET_COLUMNS
from src.validation import ValidationError

ROLE_DATASET_COLUMNS = COHORT_DATASET_COLUMNS + [
    "route_participation_season_avg",
    "target_share_season_avg",
    "air_yard_share_season_avg",
    "routes_consistency_index",
    "target_earning_index",
    "opportunity_concentration_score",
]

ROLE_FIELD_DESCRIPTIONS = {
    "route_participation_season_avg": (
        "Average prior-season route participation from canonical WR season rows."
    ),
    "target_share_season_avg": (
        "Average prior-season weekly target share from canonical WR season rows when present."
    ),
    "air_yard_share_season_avg": (
        "Average prior-season weekly air-yard share from canonical WR season rows when present."
    ),
    "routes_consistency_index": (
        "1 - mean absolute deviation divided by mean route participation, clipped to [0, 1], using only feature-season weekly rows with route participation present."
    ),
    "target_earning_index": (
        "target_share_season_avg divided by route_participation_season_avg when both inputs are present and route participation is positive."
    ),
    "opportunity_concentration_score": (
        "Weighted average of available route_participation (40%), target_share (35%), and air_yard_share (25%) inputs, renormalized across present fields only."
    ),
}


@dataclass(frozen=True)
class RoleArtifacts:
    enriched_dataset_path: Path
    summary_path: Path
    examples_path: Path


@dataclass(frozen=True)
class RoleSeasonMetrics:
    player_id: str
    feature_season: int
    route_participation_season_avg: float | None
    target_share_season_avg: float | None
    air_yard_share_season_avg: float | None
    routes_consistency_index: float | None
    target_earning_index: float | None
    opportunity_concentration_score: float | None

    def as_dict(self) -> dict[str, object]:
        return {
            "route_participation_season_avg": self.route_participation_season_avg,
            "target_share_season_avg": self.target_share_season_avg,
            "air_yard_share_season_avg": self.air_yard_share_season_avg,
            "routes_consistency_index": self.routes_consistency_index,
            "target_earning_index": self.target_earning_index,
            "opportunity_concentration_score": self.opportunity_concentration_score,
        }


ROLE_CONCENTRATION_WEIGHTS = {
    "route_participation": 0.40,
    "target_share": 0.35,
    "air_yard_share": 0.25,
}


def write_wr_role_outputs(
    processed_dir: str | Path,
    validation_dataset_path: str | Path,
    output_dir: str | Path,
) -> RoleArtifacts:
    processed_dir = Path(processed_dir)
    validation_dataset_path = Path(validation_dataset_path)
    output_dir = Path(output_dir)

    if not validation_dataset_path.exists():
        raise ValidationError(f"validation dataset does not exist: {validation_dataset_path}")

    season_rows = _read_csv_rows(processed_dir / "wr_player_seasons.csv")
    weekly_rows = _read_csv_rows(processed_dir / "wr_player_weeks.csv")
    validation_rows = _read_csv_rows(validation_dataset_path)

    enriched_rows = enrich_wr_role_dataset(
        player_season_rows=season_rows,
        weekly_rows=weekly_rows,
        validation_rows=validation_rows,
    )
    summary = build_role_summary(enriched_rows)
    examples = build_role_examples_markdown(enriched_rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    enriched_dataset_path = output_dir / "wr_validation_dataset_role_enriched.csv"
    summary_path = output_dir / "wr_role_enrichment_summary.json"
    examples_path = output_dir / "wr_role_examples.md"

    _write_csv(enriched_dataset_path, ROLE_DATASET_COLUMNS, enriched_rows)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    examples_path.write_text(examples, encoding="utf-8")

    return RoleArtifacts(
        enriched_dataset_path=enriched_dataset_path,
        summary_path=summary_path,
        examples_path=examples_path,
    )


def enrich_wr_role_dataset(
    player_season_rows: Iterable[dict[str, object]],
    weekly_rows: Iterable[dict[str, object]],
    validation_rows: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    metrics_by_key = build_wr_role_metrics(player_season_rows=player_season_rows, weekly_rows=weekly_rows)
    normalized_validation = [_normalize_validation_row(row) for row in validation_rows]

    enriched_rows: list[dict[str, object]] = []
    for row in sorted(normalized_validation, key=lambda item: (int(item["feature_season"]), str(item["player_id"]))):
        key = (str(row["player_id"]), int(row["feature_season"]))
        metrics = metrics_by_key.get(key)
        if metrics is None:
            raise ValidationError(f"missing role metrics for validation row {key}")
        enriched_rows.append({**row, **metrics.as_dict()})

    return [{column: row.get(column) for column in ROLE_DATASET_COLUMNS} for row in enriched_rows]


def build_wr_role_metrics(
    player_season_rows: Iterable[dict[str, object]],
    weekly_rows: Iterable[dict[str, object]],
) -> dict[tuple[str, int], RoleSeasonMetrics]:
    normalized_season_rows = [_normalize_player_season_row(row) for row in player_season_rows]
    normalized_weekly_rows = [_normalize_weekly_row(row) for row in weekly_rows]

    weekly_by_key: dict[tuple[str, int], list[dict[str, object]]] = {}
    for row in normalized_weekly_rows:
        key = (str(row["player_id"]), int(row["season"]))
        weekly_by_key.setdefault(key, []).append(row)

    metrics_by_key: dict[tuple[str, int], RoleSeasonMetrics] = {}
    for row in sorted(normalized_season_rows, key=lambda item: (int(item["season"]), str(item["player_id"]))):
        key = (str(row["player_id"]), int(row["season"]))
        route_participation_season_avg = _parse_optional_float(row.get("avg_route_participation"))
        target_share_season_avg = _parse_optional_float(row.get("avg_target_share"))
        air_yard_share_season_avg = _parse_optional_float(row.get("avg_air_yard_share"))
        routes_consistency_index = _compute_routes_consistency_index(weekly_by_key.get(key, []))
        target_earning_index = _compute_target_earning_index(
            target_share_season_avg=target_share_season_avg,
            route_participation_season_avg=route_participation_season_avg,
        )
        opportunity_concentration_score = _compute_opportunity_concentration_score(
            route_participation_season_avg=route_participation_season_avg,
            target_share_season_avg=target_share_season_avg,
            air_yard_share_season_avg=air_yard_share_season_avg,
        )
        metrics_by_key[key] = RoleSeasonMetrics(
            player_id=str(row["player_id"]),
            feature_season=int(row["season"]),
            route_participation_season_avg=route_participation_season_avg,
            target_share_season_avg=target_share_season_avg,
            air_yard_share_season_avg=air_yard_share_season_avg,
            routes_consistency_index=routes_consistency_index,
            target_earning_index=target_earning_index,
            opportunity_concentration_score=opportunity_concentration_score,
        )
    return metrics_by_key


def build_role_summary(rows: Iterable[dict[str, object]]) -> dict[str, object]:
    ordered_rows = list(rows)
    role_coverage = {
        field: sum(1 for row in ordered_rows if row.get(field) not in (None, ""))
        for field in ROLE_DATASET_COLUMNS
        if field in ROLE_FIELD_DESCRIPTIONS
    }
    concentration_values = [
        float(row["opportunity_concentration_score"])
        for row in ordered_rows
        if row.get("opportunity_concentration_score") not in (None, "")
    ]
    routes_consistency_values = [
        float(row["routes_consistency_index"])
        for row in ordered_rows
        if row.get("routes_consistency_index") not in (None, "")
    ]

    top_examples = sorted(
        [row for row in ordered_rows if row.get("opportunity_concentration_score") not in (None, "")],
        key=lambda item: (
            -float(item["opportunity_concentration_score"]),
            -float(item.get("target_share_season_avg") or 0.0),
            item["player_id"],
        ),
    )[:5]

    return {
        "position": "WR",
        "row_count": len(ordered_rows),
        "feature_seasons": sorted({int(row["feature_season"]) for row in ordered_rows}),
        "role_fields": ROLE_FIELD_DESCRIPTIONS,
        "formulas": {
            "routes_consistency_index": ROLE_FIELD_DESCRIPTIONS["routes_consistency_index"],
            "target_earning_index": ROLE_FIELD_DESCRIPTIONS["target_earning_index"],
            "opportunity_concentration_score": ROLE_FIELD_DESCRIPTIONS["opportunity_concentration_score"],
            "opportunity_concentration_weights": ROLE_CONCENTRATION_WEIGHTS,
        },
        "coverage": role_coverage,
        "distribution": {
            "opportunity_concentration_score_median": (
                round(median(concentration_values), 4) if concentration_values else None
            ),
            "opportunity_concentration_score_max": (
                round(max(concentration_values), 4) if concentration_values else None
            ),
            "routes_consistency_index_median": (
                round(median(routes_consistency_values), 4) if routes_consistency_values else None
            ),
        },
        "leakage_guardrails": {
            "feature_season_only": True,
            "weekly_input_scope": "Only canonical wr_player_weeks rows from the same feature season are used.",
            "season_input_scope": "Only canonical wr_player_seasons rows from the same feature season are used.",
            "next_season_outcomes_used": False,
        },
        "top_opportunity_examples": [
            {
                "player_id": row["player_id"],
                "player_name": row["player_name"],
                "feature_season": row["feature_season"],
                "route_participation_season_avg": row["route_participation_season_avg"],
                "target_share_season_avg": row["target_share_season_avg"],
                "air_yard_share_season_avg": row["air_yard_share_season_avg"],
                "opportunity_concentration_score": row["opportunity_concentration_score"],
            }
            for row in top_examples
        ],
    }


def build_role_examples_markdown(rows: Iterable[dict[str, object]]) -> str:
    materialized_rows = list(rows)
    ordered_rows = sorted(
        materialized_rows,
        key=lambda row: (
            -(float(row.get("opportunity_concentration_score") or -1.0)),
            -(float(row.get("target_earning_index") or -1.0)),
            row["feature_season"],
            row["player_id"],
        ),
    )
    high_role_rows = [row for row in ordered_rows if row.get("opportunity_concentration_score") not in (None, "")][:5]
    missing_rows = [
        row
        for row in sorted(materialized_rows, key=lambda item: (item["feature_season"], item["player_id"]))
        if row_has_missing_role_inputs(row)
    ][:5]

    return "\n".join(
        [
            "# WR Role Enrichment Examples",
            "",
            "Deterministic examples from the WR role-and-opportunity enriched validation dataset.",
            "",
            "## Highest opportunity concentration profiles",
            "",
            _markdown_examples(high_role_rows),
            "",
            "## Rows with incomplete role inputs",
            "",
            _markdown_examples(missing_rows),
            "",
        ]
    )


def row_has_missing_role_inputs(row: dict[str, object]) -> bool:
    return any(row.get(field) in (None, "") for field in ROLE_FIELD_DESCRIPTIONS)


def _compute_routes_consistency_index(weekly_rows: list[dict[str, object]]) -> float | None:
    values = [
        float(row["route_participation"])
        for row in sorted(weekly_rows, key=lambda item: int(item["week"]))
        if _parse_bool(row.get("week_is_active")) and row.get("route_participation") not in (None, "")
    ]
    if len(values) < 2:
        return None
    mean_value = sum(values) / len(values)
    if mean_value <= 0:
        return None
    mean_absolute_deviation = sum(abs(value - mean_value) for value in values) / len(values)
    return round(max(0.0, min(1.0, 1.0 - (mean_absolute_deviation / mean_value))), 4)


def _compute_target_earning_index(
    *,
    target_share_season_avg: float | None,
    route_participation_season_avg: float | None,
) -> float | None:
    if target_share_season_avg is None or route_participation_season_avg in (None, 0.0):
        return None
    return round(target_share_season_avg / route_participation_season_avg, 4)


def _compute_opportunity_concentration_score(
    *,
    route_participation_season_avg: float | None,
    target_share_season_avg: float | None,
    air_yard_share_season_avg: float | None,
) -> float | None:
    values = {
        "route_participation": route_participation_season_avg,
        "target_share": target_share_season_avg,
        "air_yard_share": air_yard_share_season_avg,
    }
    available = {
        name: value
        for name, value in values.items()
        if value is not None
    }
    if not available:
        return None
    total_weight = sum(ROLE_CONCENTRATION_WEIGHTS[name] for name in available)
    weighted_sum = sum(float(value) * ROLE_CONCENTRATION_WEIGHTS[name] for name, value in available.items())
    return round(weighted_sum / total_weight, 4)


def _normalize_player_season_row(row: dict[str, object]) -> dict[str, object]:
    normalized = dict(row)
    normalized["player_id"] = str(row["player_id"])
    normalized["season"] = int(row["season"])
    normalized["position"] = str(row["position"])
    if normalized["position"] != "WR":
        raise ValidationError("role enrichment only supports WR rows")
    normalized["avg_route_participation"] = _parse_optional_float(row.get("avg_route_participation"))
    normalized["avg_target_share"] = _parse_optional_float(row.get("avg_target_share"))
    normalized["avg_air_yard_share"] = _parse_optional_float(row.get("avg_air_yard_share"))
    return normalized


def _normalize_weekly_row(row: dict[str, object]) -> dict[str, object]:
    normalized = dict(row)
    normalized["player_id"] = str(row["player_id"])
    normalized["season"] = int(row["season"])
    normalized["week"] = int(row["week"])
    normalized["position"] = str(row["position"])
    if normalized["position"] != "WR":
        raise ValidationError("role enrichment only supports WR rows")
    normalized["week_is_active"] = _parse_bool(row.get("week_is_active"))
    normalized["route_participation"] = _parse_optional_float(row.get("route_participation"))
    normalized["target_share"] = _parse_optional_float(row.get("target_share"))
    normalized["air_yard_share"] = _parse_optional_float(row.get("air_yard_share"))
    return normalized


def _normalize_validation_row(row: dict[str, object]) -> dict[str, object]:
    normalized = dict(row)
    normalized["player_id"] = str(row["player_id"])
    normalized["player_name"] = str(row["player_name"])
    normalized["feature_season"] = int(row["feature_season"])
    normalized["position"] = str(row["position"])
    if normalized["position"] != "WR":
        raise ValidationError("role enrichment only supports WR rows")
    for field in ROLE_DATASET_COLUMNS:
        normalized.setdefault(field, row.get(field))
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


def _parse_optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _markdown_examples(rows: list[dict[str, object]]) -> str:
    if not rows:
        return "_No rows in this category._"
    lines = [
        "| feature_season | player_id | player_name | route_participation | target_share | air_yard_share | consistency | target_earning | opportunity_concentration |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {feature_season} | {player_id} | {player_name} | {route_participation} | {target_share} | {air_yard_share} | {consistency} | {target_earning} | {concentration} |".format(
                feature_season=row["feature_season"],
                player_id=row["player_id"],
                player_name=row["player_name"],
                route_participation=_format_metric(row.get("route_participation_season_avg")),
                target_share=_format_metric(row.get("target_share_season_avg")),
                air_yard_share=_format_metric(row.get("air_yard_share_season_avg")),
                consistency=_format_metric(row.get("routes_consistency_index")),
                target_earning=_format_metric(row.get("target_earning_index")),
                concentration=_format_metric(row.get("opportunity_concentration_score")),
            )
        )
    return "\n".join(lines)


def _format_metric(value: object) -> str:
    if value in (None, ""):
        return "n/a"
    return f"{float(value):.4f}"
