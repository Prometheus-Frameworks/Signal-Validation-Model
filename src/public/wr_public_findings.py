"""Deterministic public-facing WR findings/narrative pack generator."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PUBLIC_FINDINGS_SCHEMA_VERSION = "wr_public_findings_v1"
PUBLIC_RECIPE_COMPARISON_COLUMNS = [
    "comparison_scope",
    "recipe_name",
    "recipe_family",
    "precision_at_20",
    "recall_at_20",
    "average_breakout_rank",
    "false_positives_in_top_20",
    "false_negatives_outside_top_30",
    "is_best_overall",
    "is_best_in_family",
]
PUBLIC_NOTABLE_HIT_COLUMNS = [
    "notable_rank",
    "player_name",
    "team",
    "case_type",
    "candidate_rank",
    "signal_score",
    "feature_ppg",
    "outcome_ppg",
    "actual_minus_expected_ppg",
    "breakout_reason",
]
PUBLIC_NOTABLE_MISS_COLUMNS = [
    "notable_rank",
    "player_name",
    "team",
    "miss_type",
    "candidate_rank",
    "signal_score",
    "feature_ppg",
    "outcome_ppg",
    "actual_minus_expected_ppg",
    "breakout_reason",
]

DEFAULT_NOTABLE_HIT_LIMIT = 5
DEFAULT_NOTABLE_MISS_LIMIT = 6


@dataclass(frozen=True)
class PublicFindingsArtifacts:
    findings_markdown_path: Path
    recipe_comparison_csv_path: Path
    notable_hits_csv_path: Path
    notable_misses_csv_path: Path
    key_takeaways_json_path: Path


def build_wr_public_findings(
    *,
    comparison_summary_path: str | Path,
    case_study_dir: str | Path,
    output_dir: str | Path,
    feature_season: int,
    outcome_season: int,
    exports_dir: str | Path = "outputs/exports",
    notable_hit_limit: int = DEFAULT_NOTABLE_HIT_LIMIT,
    notable_miss_limit: int = DEFAULT_NOTABLE_MISS_LIMIT,
) -> PublicFindingsArtifacts:
    """Build a deterministic public-safe findings pack from existing validated/exported artifacts only."""

    if notable_hit_limit <= 0:
        raise ValueError("notable_hit_limit must be positive")
    if notable_miss_limit <= 0:
        raise ValueError("notable_miss_limit must be positive")

    comparison_summary_path = Path(comparison_summary_path)
    case_study_dir = Path(case_study_dir)
    output_dir = Path(output_dir)
    exports_dir = Path(exports_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    season_suffix = f"{feature_season}_to_{outcome_season}"
    comparison_summary = _read_json(comparison_summary_path)
    breakout_candidates = _read_json(exports_dir / "wr_breakout_candidates_latest.json")
    case_study_summary = _read_json(exports_dir / f"wr_case_study_summary_{season_suffix}.json")
    hits_rows = _read_csv_dicts(case_study_dir / f"wr_breakout_hits_{season_suffix}.csv")
    false_positive_rows = _read_csv_dicts(case_study_dir / f"wr_breakout_false_positives_{season_suffix}.csv")
    false_negative_rows = _read_csv_dicts(case_study_dir / f"wr_breakout_false_negatives_{season_suffix}.csv")

    _validate_requested_pair(breakout_candidates, feature_season, outcome_season, "wr_breakout_candidates_latest.json")
    _validate_requested_pair(case_study_summary, feature_season, outcome_season, f"wr_case_study_summary_{season_suffix}.json")

    recipe_comparison_rows = _build_recipe_comparison_rows(comparison_summary)
    notable_hits = _select_notable_hits(hits_rows, limit=notable_hit_limit)
    notable_misses = _select_notable_misses(
        false_negative_rows=false_negative_rows,
        false_positive_rows=false_positive_rows,
        limit=notable_miss_limit,
    )
    comparison_snapshot = _build_comparison_snapshot(comparison_summary)
    signal_takeaways = _build_signal_takeaways(
        breakout_candidates=breakout_candidates,
        notable_hits=notable_hits,
        notable_misses=notable_misses,
        case_study_summary=case_study_summary,
        comparison_snapshot=comparison_snapshot,
    )
    takeaways_payload = _build_takeaways_json(
        feature_season=feature_season,
        outcome_season=outcome_season,
        comparison_summary_path=comparison_summary_path,
        case_study_dir=case_study_dir,
        exports_dir=exports_dir,
        case_study_summary=case_study_summary,
        comparison_snapshot=comparison_snapshot,
        notable_hits=notable_hits,
        notable_misses=notable_misses,
        signal_takeaways=signal_takeaways,
        notable_hit_limit=notable_hit_limit,
        notable_miss_limit=notable_miss_limit,
    )
    findings_markdown = _build_findings_markdown(
        feature_season=feature_season,
        outcome_season=outcome_season,
        case_study_summary=case_study_summary,
        comparison_snapshot=comparison_snapshot,
        notable_hits=notable_hits,
        notable_misses=notable_misses,
        signal_takeaways=signal_takeaways,
    )

    findings_markdown_path = output_dir / f"wr_public_findings_{season_suffix}.md"
    recipe_comparison_csv_path = output_dir / f"wr_public_recipe_comparison_{season_suffix}.csv"
    notable_hits_csv_path = output_dir / f"wr_public_notable_hits_{season_suffix}.csv"
    notable_misses_csv_path = output_dir / f"wr_public_notable_misses_{season_suffix}.csv"
    key_takeaways_json_path = output_dir / f"wr_public_key_takeaways_{season_suffix}.json"

    findings_markdown_path.write_text(findings_markdown, encoding="utf-8")
    _write_csv(recipe_comparison_csv_path, PUBLIC_RECIPE_COMPARISON_COLUMNS, recipe_comparison_rows)
    _write_csv(notable_hits_csv_path, PUBLIC_NOTABLE_HIT_COLUMNS, notable_hits)
    _write_csv(notable_misses_csv_path, PUBLIC_NOTABLE_MISS_COLUMNS, notable_misses)
    key_takeaways_json_path.write_text(json.dumps(takeaways_payload, indent=2) + "\n", encoding="utf-8")

    return PublicFindingsArtifacts(
        findings_markdown_path=findings_markdown_path,
        recipe_comparison_csv_path=recipe_comparison_csv_path,
        notable_hits_csv_path=notable_hits_csv_path,
        notable_misses_csv_path=notable_misses_csv_path,
        key_takeaways_json_path=key_takeaways_json_path,
    )


def _build_recipe_comparison_rows(comparison_summary: dict[str, Any]) -> list[dict[str, Any]]:
    best_overall_name = str(comparison_summary["best_recipe"]["recipe_name"])
    best_by_family = {
        "base": _recipe_name_or_none(comparison_summary.get("best_base_recipe")),
        "cohort": _recipe_name_or_none(comparison_summary.get("best_cohort_recipe")),
        "role": _recipe_name_or_none(comparison_summary.get("best_role_recipe")),
    }
    rows = []
    for metrics in sorted(
        comparison_summary["recipe_metrics"],
        key=lambda item: (_family_order(str(item["recipe_family"])), _recipe_sort_key(item)),
    ):
        recipe_family = str(metrics["recipe_family"])
        recipe_name = str(metrics["recipe_name"])
        rows.append(
            {
                "comparison_scope": "family_recipe",
                "recipe_name": recipe_name,
                "recipe_family": recipe_family,
                "precision_at_20": _format_number(metrics.get("precision_at_20")),
                "recall_at_20": _format_number(metrics.get("recall_at_20")),
                "average_breakout_rank": _format_number(metrics.get("average_breakout_rank")),
                "false_positives_in_top_20": str(int(metrics.get("false_positives_in_top_20", 0))),
                "false_negatives_outside_top_30": str(int(metrics.get("false_negatives_outside_top_30", 0))),
                "is_best_overall": _format_bool(recipe_name == best_overall_name),
                "is_best_in_family": _format_bool(recipe_name == best_by_family.get(recipe_family)),
            }
        )
    return rows


def _select_notable_hits(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    ordered_rows = sorted(rows, key=_notable_hit_sort_key)
    return [
        _public_notable_hit_row(index=index, row=row)
        for index, row in enumerate(ordered_rows[:limit], start=1)
    ]


def _select_notable_misses(
    *,
    false_negative_rows: list[dict[str, Any]],
    false_positive_rows: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    false_negative_limit = limit // 2 + limit % 2
    false_positive_limit = limit // 2

    chosen_false_negatives = sorted(false_negative_rows, key=_notable_false_negative_sort_key)[:false_negative_limit]
    chosen_false_positives = sorted(false_positive_rows, key=_notable_false_positive_sort_key)[:false_positive_limit]

    remaining = limit - len(chosen_false_negatives) - len(chosen_false_positives)
    if remaining > 0:
        remaining_false_negatives = [
            row for row in sorted(false_negative_rows, key=_notable_false_negative_sort_key)
            if row not in chosen_false_negatives
        ]
        remaining_false_positives = [
            row for row in sorted(false_positive_rows, key=_notable_false_positive_sort_key)
            if row not in chosen_false_positives
        ]
        refill_pool = [
            ("false_negative", row) for row in remaining_false_negatives
        ] + [
            ("false_positive", row) for row in remaining_false_positives
        ]
        refill_pool = sorted(refill_pool, key=_notable_miss_refill_sort_key)
        for miss_type, row in refill_pool[:remaining]:
            if miss_type == "false_negative":
                chosen_false_negatives.append(row)
            else:
                chosen_false_positives.append(row)

    combined_rows = [("false_negative", row) for row in chosen_false_negatives] + [
        ("false_positive", row) for row in chosen_false_positives
    ]
    combined_rows = sorted(combined_rows, key=_public_notable_miss_sort_key)
    return [
        _public_notable_miss_row(index=index, miss_type=miss_type, row=row)
        for index, (miss_type, row) in enumerate(combined_rows, start=1)
    ]


def _build_comparison_snapshot(comparison_summary: dict[str, Any]) -> dict[str, Any]:
    best_overall = comparison_summary["best_recipe"]
    best_base = comparison_summary.get("best_base_recipe")
    best_cohort = comparison_summary.get("best_cohort_recipe")
    best_role = comparison_summary.get("best_role_recipe")
    cohort_status = _delta_status(
        comparison_summary.get("cohort_vs_base_delta"),
        compared_label="best cohort-aware recipe vs. best base recipe",
    )
    role_vs_base_status = _delta_status(
        comparison_summary.get("role_vs_base_delta"),
        compared_label="best role-aware recipe vs. best base recipe",
    )
    role_vs_cohort_status = _delta_status(
        comparison_summary.get("role_vs_cohort_delta"),
        compared_label="best role-aware recipe vs. best cohort-aware recipe",
    )
    return {
        "best_overall": _public_recipe_snapshot(best_overall),
        "best_base": _public_recipe_snapshot(best_base),
        "best_cohort": _public_recipe_snapshot(best_cohort),
        "best_role": _public_recipe_snapshot(best_role),
        "cohort_vs_base": cohort_status,
        "role_vs_base": role_vs_base_status,
        "role_vs_cohort": role_vs_cohort_status,
        "best_recipe_rule": comparison_summary["best_recipe_rule"],
    }


def _build_takeaways_json(
    *,
    feature_season: int,
    outcome_season: int,
    comparison_summary_path: Path,
    case_study_dir: Path,
    exports_dir: Path,
    case_study_summary: dict[str, Any],
    comparison_snapshot: dict[str, Any],
    notable_hits: list[dict[str, Any]],
    notable_misses: list[dict[str, Any]],
    signal_takeaways: list[str],
    notable_hit_limit: int,
    notable_miss_limit: int,
) -> dict[str, Any]:
    return {
        "report_name": "wr_public_key_takeaways",
        "schema_version": PUBLIC_FINDINGS_SCHEMA_VERSION,
        "position": "WR",
        "feature_season": feature_season,
        "outcome_season": outcome_season,
        "best_overall_recipe": comparison_snapshot["best_overall"],
        "best_base_recipe": comparison_snapshot["best_base"],
        "best_cohort_recipe": comparison_snapshot["best_cohort"],
        "best_role_recipe": comparison_snapshot["best_role"],
        "family_improvement_checks": {
            "cohort_vs_base": comparison_snapshot["cohort_vs_base"],
            "role_vs_base": comparison_snapshot["role_vs_base"],
            "role_vs_cohort": comparison_snapshot["role_vs_cohort"],
        },
        "season_pair_summary": {
            "hit_count": int(case_study_summary["hit_count"]),
            "false_positive_count": int(case_study_summary["false_positive_count"]),
            "false_negative_count": int(case_study_summary["false_negative_count"]),
        },
        "notable_selection_rule": {
            "hit_rule": (
                "Hits are sorted by highest actual_minus_expected_ppg, then highest outcome_ppg, "
                "then best candidate rank, then alphabetical player name."
            ),
            "miss_rule": (
                "Misses reserve half the list for false negatives sorted by highest "
                "actual_minus_expected_ppg and half for false positives sorted by lowest "
                "actual_minus_expected_ppg; any unused slots are refilled by the remaining rows "
                "with the largest miss magnitude."
            ),
            "notable_hit_limit": notable_hit_limit,
            "notable_miss_limit": notable_miss_limit,
        },
        "notable_hits": notable_hits,
        "notable_misses": notable_misses,
        "key_takeaways": signal_takeaways,
        "best_recipe_rule": comparison_snapshot["best_recipe_rule"],
        "source_artifacts": {
            "comparison_summary": str(comparison_summary_path),
            "case_study_dir": str(case_study_dir),
            "exports_dir": str(exports_dir),
        },
    }


def _build_findings_markdown(
    *,
    feature_season: int,
    outcome_season: int,
    case_study_summary: dict[str, Any],
    comparison_snapshot: dict[str, Any],
    notable_hits: list[dict[str, Any]],
    notable_misses: list[dict[str, Any]],
    signal_takeaways: list[str],
) -> str:
    best_overall = comparison_snapshot["best_overall"]
    best_base = comparison_snapshot["best_base"]
    best_cohort = comparison_snapshot["best_cohort"]
    best_role = comparison_snapshot["best_role"]
    executive_summary = (
        f"For the {feature_season} to {outcome_season} WR retrospective, "
        f"`{best_overall['recipe_name']}` finished as the best overall recipe and the winning "
        f"recipe family was `{best_overall['recipe_family']}`. The season-pair review logged "
        f"{case_study_summary['hit_count']} hits, {case_study_summary['false_positive_count']} false positives, "
        f"and {case_study_summary['false_negative_count']} false negatives."
    )
    lines = [
        f"# WR Public Findings: {feature_season} to {outcome_season}",
        "",
        "## Executive summary",
        "",
        executive_summary,
        "",
        "## Best overall recipe and family",
        "",
        f"- Best overall recipe: `{best_overall['recipe_name']}`.",
        f"- Winning family: `{best_overall['recipe_family']}`.",
        f"- Best base recipe: `{_recipe_label(best_base)}`.",
        f"- Best cohort-aware recipe: `{_recipe_label(best_cohort)}`.",
        f"- Best role-aware recipe: `{_recipe_label(best_role)}`.",
        "",
        "## Did cohort / role context help?",
        "",
        f"- Cohort over base: {_status_sentence(comparison_snapshot['cohort_vs_base'])}",
        f"- Role over base: {_status_sentence(comparison_snapshot['role_vs_base'])}",
        f"- Role over cohort: {_status_sentence(comparison_snapshot['role_vs_cohort'])}",
        "",
        "## Notable player hits",
        "",
        _markdown_table(notable_hits, PUBLIC_NOTABLE_HIT_COLUMNS),
        "",
        "## Notable player misses",
        "",
        _markdown_table(notable_misses, PUBLIC_NOTABLE_MISS_COLUMNS),
        "",
        "## Public-safe signal takeaways",
        "",
        *[f"- {takeaway}" for takeaway in signal_takeaways],
        "",
        "## Limitations and cautions",
        "",
        "- This pack is retrospective only and uses existing validated/exported artifacts without rescoring.",
        "- Recipe-family improvement checks are inferences from published comparison deltas, not new experiments.",
        "- Notable hits and misses follow a deterministic ranking rule and are examples, not an exhaustive narrative.",
        "- Public formatting intentionally simplifies the lower-level scoring details and omits internal scaffolding.",
        "",
    ]
    return "\n".join(lines)


def _build_signal_takeaways(
    *,
    breakout_candidates: dict[str, Any],
    notable_hits: list[dict[str, Any]],
    notable_misses: list[dict[str, Any]],
    case_study_summary: dict[str, Any],
    comparison_snapshot: dict[str, Any],
) -> list[str]:
    top_candidates = list(breakout_candidates["candidates"])[: min(5, len(breakout_candidates["candidates"]))]
    top_role_signal = _average_nested(top_candidates, ("component_scores", "role_signal"))
    top_cohort_signal = _average_nested(top_candidates, ("component_scores", "cohort_signal"))
    hit_outcome_ppg = _average_field(notable_hits, "outcome_ppg")
    miss_outcome_ppg = _average_field(notable_misses, "outcome_ppg")
    return [
        (
            f"The best overall recipe came from the `{comparison_snapshot['best_overall']['recipe_family']}` family, "
            f"with `{comparison_snapshot['best_overall']['recipe_name']}` winning under the published recipe-selection rule."
        ),
        (
            "Among the top exported candidates, the average public-safe role signal was "
            f"{top_role_signal} and the average cohort signal was {top_cohort_signal}."
        ),
        (
            "The selected notable hits averaged "
            f"{hit_outcome_ppg} outcome PPG, compared with {miss_outcome_ppg} for the selected notable misses."
        ),
        (
            "The season-pair case study recorded "
            f"{case_study_summary['hit_count']} hits, {case_study_summary['false_positive_count']} false positives, "
            f"and {case_study_summary['false_negative_count']} false negatives."
        ),
    ]


def _public_recipe_snapshot(recipe_block: dict[str, Any] | None) -> dict[str, Any] | None:
    if recipe_block is None:
        return None
    metrics = dict(recipe_block["metrics"])
    return {
        "recipe_name": str(recipe_block["recipe_name"]),
        "recipe_family": str(metrics["recipe_family"]),
        "precision_at_20": _format_number(metrics.get("precision_at_20")),
        "recall_at_20": _format_number(metrics.get("recall_at_20")),
        "average_breakout_rank": _format_number(metrics.get("average_breakout_rank")),
    }


def _public_notable_hit_row(*, index: int, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "notable_rank": index,
        "player_name": str(row["player_name"]),
        "team": str(row["feature_team"]),
        "case_type": "hit",
        "candidate_rank": int(row["rank"]),
        "signal_score": _format_number(row["wr_signal_score"]),
        "feature_ppg": _format_number(row["feature_ppg"], digits=1),
        "outcome_ppg": _format_number(row.get("outcome_ppg"), digits=1),
        "actual_minus_expected_ppg": _format_number(row.get("actual_minus_expected_ppg")),
        "breakout_reason": str(row["breakout_reason"]),
    }


def _public_notable_miss_row(*, index: int, miss_type: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "notable_rank": index,
        "player_name": str(row["player_name"]),
        "team": str(row["feature_team"]),
        "miss_type": miss_type,
        "candidate_rank": int(row["rank"]),
        "signal_score": _format_number(row["wr_signal_score"]),
        "feature_ppg": _format_number(row["feature_ppg"], digits=1),
        "outcome_ppg": _format_number(row.get("outcome_ppg"), digits=1),
        "actual_minus_expected_ppg": _format_number(row.get("actual_minus_expected_ppg")),
        "breakout_reason": str(row["breakout_reason"]),
    }


def _status_sentence(status: dict[str, Any]) -> str:
    label = str(status["status"]).replace("_", " ")
    return f"{label.capitalize()} ({status['reason']})."


def _delta_status(delta: dict[str, Any] | None, *, compared_label: str) -> dict[str, Any]:
    if delta is None:
        return {"status": "not_available", "improved": None, "reason": f"No published delta was available for {compared_label}"}
    precision_delta = float(delta.get("precision_at_20_delta", 0.0))
    recall_delta = float(delta.get("recall_at_20_delta", 0.0))
    average_rank_delta = delta.get("average_breakout_rank_delta")
    if precision_delta > 0:
        return {"status": "improved", "improved": True, "reason": f"precision@20 improved by {_format_signed_number(precision_delta)}"}
    if precision_delta < 0:
        return {"status": "declined", "improved": False, "reason": f"precision@20 declined by {_format_signed_number(precision_delta)}"}
    if recall_delta > 0:
        return {"status": "improved", "improved": True, "reason": f"precision@20 was flat and recall@20 improved by {_format_signed_number(recall_delta)}"}
    if recall_delta < 0:
        return {"status": "declined", "improved": False, "reason": f"precision@20 was flat and recall@20 declined by {_format_signed_number(recall_delta)}"}
    if average_rank_delta is not None and float(average_rank_delta) < 0:
        return {
            "status": "improved",
            "improved": True,
            "reason": f"precision/recall were flat and average breakout rank improved by {_format_signed_number(abs(float(average_rank_delta)))}",
        }
    if average_rank_delta is not None and float(average_rank_delta) > 0:
        return {
            "status": "declined",
            "improved": False,
            "reason": f"precision/recall were flat and average breakout rank worsened by {_format_signed_number(float(average_rank_delta))}",
        }
    return {"status": "matched", "improved": False, "reason": f"{compared_label} matched on the published comparison metrics"}


def _average_nested(rows: list[dict[str, Any]], path: tuple[str, str]) -> str:
    values = []
    for row in rows:
        current: Any = row
        for part in path:
            current = current.get(part) if isinstance(current, dict) else None
        if current not in (None, ""):
            values.append(float(current))
    return _format_average(values)


def _average_field(rows: list[dict[str, Any]], field: str) -> str:
    values = [float(row[field]) for row in rows if row.get(field) not in (None, "", "n/a")]
    return _format_average(values)


def _format_average(values: list[float]) -> str:
    if not values:
        return "n/a"
    return f"{sum(values) / len(values):.2f}"


def _markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    if not rows:
        return "\n".join([header, divider, "| " + " | ".join("n/a" for _ in columns) + " |"])
    body = [
        "| " + " | ".join(str(row.get(column, "")) for column in columns) + " |"
        for row in rows
    ]
    return "\n".join([header, divider, *body])


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"required public-findings source does not exist: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv_dicts(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"required public-findings source does not exist: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _validate_requested_pair(payload: dict[str, Any], feature_season: int, outcome_season: int, label: str) -> None:
    if int(payload["feature_season"]) != feature_season or int(payload["outcome_season"]) != outcome_season:
        raise ValueError(f"{label} does not match requested season pair {feature_season} -> {outcome_season}")


def _recipe_name_or_none(recipe_block: dict[str, Any] | None) -> str | None:
    if recipe_block is None:
        return None
    return str(recipe_block["recipe_name"])


def _recipe_label(recipe_block: dict[str, Any] | None) -> str:
    if recipe_block is None:
        return "n/a"
    return str(recipe_block["recipe_name"])


def _family_order(recipe_family: str) -> int:
    order = {"base": 0, "cohort": 1, "role": 2}
    return order.get(recipe_family, 99)


def _recipe_sort_key(metrics: dict[str, Any]) -> tuple[float, float, float, str]:
    average_breakout_rank = metrics.get("average_breakout_rank")
    if average_breakout_rank is None:
        average_breakout_rank = float("inf")
    return (
        -float(metrics.get("precision_at_20", 0.0)),
        -float(metrics.get("recall_at_20", 0.0)),
        float(average_breakout_rank),
        str(metrics["recipe_name"]),
    )


def _notable_hit_sort_key(row: dict[str, Any]) -> tuple[float, float, int, str]:
    return (
        -float(row.get("actual_minus_expected_ppg") or 0.0),
        -float(row.get("outcome_ppg") or 0.0),
        int(row["rank"]),
        str(row["player_name"]),
    )


def _notable_false_negative_sort_key(row: dict[str, Any]) -> tuple[float, float, int, str]:
    return (
        -float(row.get("actual_minus_expected_ppg") or 0.0),
        -float(row.get("outcome_ppg") or 0.0),
        int(row["rank"]),
        str(row["player_name"]),
    )


def _notable_false_positive_sort_key(row: dict[str, Any]) -> tuple[float, float, int, str]:
    actual_minus_expected = float(row.get("actual_minus_expected_ppg") or 0.0)
    return (
        actual_minus_expected,
        -float(row.get("wr_signal_score") or 0.0),
        int(row["rank"]),
        str(row["player_name"]),
    )


def _notable_miss_refill_sort_key(item: tuple[str, dict[str, Any]]) -> tuple[float, int, int, str]:
    miss_type, row = item
    actual_minus_expected = float(row.get("actual_minus_expected_ppg") or 0.0)
    magnitude = abs(actual_minus_expected)
    miss_type_order = 0 if miss_type == "false_negative" else 1
    return (
        -magnitude,
        miss_type_order,
        int(row["rank"]),
        str(row["player_name"]),
    )


def _public_notable_miss_sort_key(item: tuple[str, dict[str, Any]]) -> tuple[int, float, int, str]:
    miss_type, row = item
    miss_type_order = 0 if miss_type == "false_negative" else 1
    actual_minus_expected = float(row.get("actual_minus_expected_ppg") or 0.0)
    magnitude = abs(actual_minus_expected)
    return (
        miss_type_order,
        -magnitude,
        int(row["rank"]),
        str(row["player_name"]),
    )


def _format_number(value: Any, digits: int = 2) -> str:
    if value in (None, ""):
        return "n/a"
    return f"{float(value):.{digits}f}"


def _format_signed_number(value: float, digits: int = 2) -> str:
    return f"{float(value):+.{digits}f}"


def _format_bool(value: bool) -> str:
    return "true" if value else "false"
