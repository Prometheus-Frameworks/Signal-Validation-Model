"""Deterministic public-facing WR report pack generator."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PUBLIC_REPORT_SCHEMA_VERSION = "wr_public_reports_v1"
PUBLIC_TOP_CANDIDATE_COLUMNS = [
    "rank",
    "player_name",
    "team",
    "signal_score",
    "feature_ppg",
    "feature_targets_per_game",
    "breakout_result",
    "breakout_reason",
]
PUBLIC_HITS_AND_MISSES_COLUMNS = [
    "category",
    "rank",
    "player_name",
    "team",
    "signal_score",
    "feature_ppg",
    "outcome_ppg",
    "breakout_result",
    "breakout_reason",
]


@dataclass(frozen=True)
class PublicReportArtifacts:
    report_markdown_path: Path
    report_json_path: Path
    top_candidates_csv_path: Path
    hits_and_misses_csv_path: Path
    methodology_summary_path: Path
    disclaimer_path: Path


@dataclass(frozen=True)
class PublicInputPaths:
    exports_dir: Path
    case_study_dir: Path
    comparison_summary_path: Path
    output_dir: Path


def build_wr_public_report(
    *,
    exports_dir: str | Path,
    case_study_dir: str | Path,
    comparison_summary_path: str | Path,
    output_dir: str | Path,
    feature_season: int,
    outcome_season: int,
    top_candidate_limit: int = 10,
) -> PublicReportArtifacts:
    """Build a deterministic public-facing WR report pack from existing export artifacts only."""

    if top_candidate_limit <= 0:
        raise ValueError("top_candidate_limit must be positive")

    paths = PublicInputPaths(
        exports_dir=Path(exports_dir),
        case_study_dir=Path(case_study_dir),
        comparison_summary_path=Path(comparison_summary_path),
        output_dir=Path(output_dir),
    )
    paths.output_dir.mkdir(parents=True, exist_ok=True)

    season_suffix = f"{feature_season}_to_{outcome_season}"
    breakout_candidates = _read_json(paths.exports_dir / "wr_breakout_candidates_latest.json")
    case_study_summary = _read_json(paths.exports_dir / f"wr_case_study_summary_{season_suffix}.json")
    player_signal_cards = _read_csv_dicts(paths.exports_dir / f"wr_player_signal_cards_{feature_season}.csv")
    comparison_summary = _read_json(paths.comparison_summary_path)
    hits_rows = _read_csv_dicts(paths.case_study_dir / f"wr_breakout_hits_{season_suffix}.csv")
    false_positive_rows = _read_csv_dicts(paths.case_study_dir / f"wr_breakout_false_positives_{season_suffix}.csv")
    false_negative_rows = _read_csv_dicts(paths.case_study_dir / f"wr_breakout_false_negatives_{season_suffix}.csv")

    _validate_requested_pair(breakout_candidates, feature_season, outcome_season, "wr_breakout_candidates_latest.json")
    _validate_requested_pair(case_study_summary, feature_season, outcome_season, f"wr_case_study_summary_{season_suffix}.json")

    best_recipe = comparison_summary["best_recipe"]
    best_recipe_name = str(best_recipe["recipe_name"])
    recipe_family = _recipe_family(best_recipe)
    outcome_status = _season_pair_outcome_status(
        player_signal_cards,
        feature_season=feature_season,
        outcome_season=outcome_season,
    )

    all_candidates = list(breakout_candidates["candidates"])
    top_candidates = [
        _public_candidate_row(candidate)
        for candidate in all_candidates[:top_candidate_limit]
    ]
    hits = [_public_outcome_row("hit", row) for row in hits_rows]
    false_positives = [_public_outcome_row("false_positive", row) for row in false_positive_rows]
    false_negatives = [_public_outcome_row("false_negative", row) for row in false_negative_rows]
    actual_breakouts = _build_actual_breakouts(hits_rows, false_negative_rows)
    report_json = _build_report_json(
        feature_season=feature_season,
        outcome_season=outcome_season,
        best_recipe_name=best_recipe_name,
        recipe_family=recipe_family,
        case_study_summary=case_study_summary,
        top_candidates=top_candidates,
        hits=hits,
        false_positives=false_positives,
        false_negatives=false_negatives,
        actual_breakouts=actual_breakouts,
        signal_takeaways=_build_signal_takeaways(
            all_candidates,
            hits_rows,
            false_positive_rows,
            false_negative_rows,
            outcomes_pending=outcome_status["outcomes_pending"],
            outcome_season=outcome_season,
        ),
        outcomes_pending=outcome_status["outcomes_pending"],
    )
    report_markdown = _build_report_markdown(report_json, outcomes_pending=outcome_status["outcomes_pending"])
    methodology_summary = _build_methodology_summary()
    disclaimer = _build_disclaimer()

    report_markdown_path = paths.output_dir / f"wr_public_breakout_report_{season_suffix}.md"
    report_json_path = paths.output_dir / f"wr_public_breakout_report_{season_suffix}.json"
    top_candidates_csv_path = paths.output_dir / f"wr_public_top_candidates_{season_suffix}.csv"
    hits_and_misses_csv_path = paths.output_dir / f"wr_public_hits_and_misses_{season_suffix}.csv"
    methodology_summary_path = paths.output_dir / "wr_public_methodology_summary.md"
    disclaimer_path = paths.output_dir / "wr_public_disclaimer.md"

    report_markdown_path.write_text(report_markdown, encoding="utf-8")
    report_json_path.write_text(json.dumps(report_json, indent=2) + "\n", encoding="utf-8")
    _write_csv(top_candidates_csv_path, PUBLIC_TOP_CANDIDATE_COLUMNS, top_candidates)
    _write_csv(
        hits_and_misses_csv_path,
        PUBLIC_HITS_AND_MISSES_COLUMNS,
        hits + false_positives + false_negatives,
    )
    methodology_summary_path.write_text(methodology_summary, encoding="utf-8")
    disclaimer_path.write_text(disclaimer, encoding="utf-8")

    return PublicReportArtifacts(
        report_markdown_path=report_markdown_path,
        report_json_path=report_json_path,
        top_candidates_csv_path=top_candidates_csv_path,
        hits_and_misses_csv_path=hits_and_misses_csv_path,
        methodology_summary_path=methodology_summary_path,
        disclaimer_path=disclaimer_path,
    )


def _build_report_json(
    *,
    feature_season: int,
    outcome_season: int,
    best_recipe_name: str,
    recipe_family: str,
    case_study_summary: dict[str, Any],
    top_candidates: list[dict[str, Any]],
    hits: list[dict[str, Any]],
    false_positives: list[dict[str, Any]],
    false_negatives: list[dict[str, Any]],
    actual_breakouts: list[dict[str, Any]],
    signal_takeaways: list[str],
    outcomes_pending: bool,
) -> dict[str, Any]:
    hit_count = int(case_study_summary["hit_count"])
    false_positive_count = int(case_study_summary["false_positive_count"])
    false_negative_count = int(case_study_summary["false_negative_count"])
    if outcomes_pending:
        executive_summary = (
            f"The {feature_season}→{outcome_season} report is a forward-looking candidate board. "
            f"Using feature-season {feature_season} information, {best_recipe_name} is the current top-performing "
            f"{recipe_family} recipe for this pending-outcome season pair. Final hit/miss evaluation will be "
            f"available once {outcome_season} outcome data is complete."
        )
    else:
        executive_summary = (
            f"Using feature-season {feature_season} information, the retrospective {outcome_season} review "
            f"shows {best_recipe_name} as the top-performing {recipe_family} recipe. "
            f"The surfaced list produced {hit_count} hits, {false_positive_count} false positives, "
            f"and {false_negative_count} false negatives."
        )
    return {
        "report_name": "wr_public_breakout_report",
        "schema_version": PUBLIC_REPORT_SCHEMA_VERSION,
        "position": "WR",
        "title": f"WR Public Breakout Report: {feature_season} to {outcome_season}",
        "feature_season": feature_season,
        "outcome_season": outcome_season,
        "executive_summary": executive_summary,
        "best_recipe": {
            "recipe_name": best_recipe_name,
            "recipe_family": recipe_family,
        },
        "season_pair_summary": {
            "hit_count": hit_count,
            "false_positive_count": false_positive_count,
            "false_negative_count": false_negative_count,
            "actual_breakout_count": len(actual_breakouts),
        },
        "top_candidates": top_candidates,
        "actual_breakouts": actual_breakouts,
        "correctly_surfaced_breakouts": hits,
        "notable_false_positives": false_positives,
        "notable_misses": false_negatives,
        "signal_takeaways": signal_takeaways,
        "methodology_summary_artifact": "wr_public_methodology_summary.md",
        "disclaimer_artifact": "wr_public_disclaimer.md",
        "source_artifacts": {
            "breakout_candidates": "wr_breakout_candidates_latest.json",
            "case_study_summary": f"wr_case_study_summary_{feature_season}_to_{outcome_season}.json",
            "hits_csv": f"wr_breakout_hits_{feature_season}_to_{outcome_season}.csv",
            "false_positives_csv": f"wr_breakout_false_positives_{feature_season}_to_{outcome_season}.csv",
            "false_negatives_csv": f"wr_breakout_false_negatives_{feature_season}_to_{outcome_season}.csv",
            "comparison_summary": "wr_recipe_comparison_summary.json",
        },
    }


def _build_report_markdown(report: dict[str, Any], *, outcomes_pending: bool) -> str:
    best_recipe = report["best_recipe"]
    pair = f"{report['feature_season']} to {report['outcome_season']}"
    outcome_season = int(report["outcome_season"])
    sections = [
        f"# {report['title']}",
        "",
        f"Season pair: **{pair}**.",
        "",
        *(
            [
                (
                    f"The {report['feature_season']}→{report['outcome_season']} report is a forward-looking candidate board. "
                    f"Final hit/miss evaluation will be available once {report['outcome_season']} outcome data is complete."
                ),
                "",
            ]
            if outcomes_pending
            else []
        ),
        "## Executive summary",
        "",
        report["executive_summary"],
        "",
        "## Best recipe",
        "",
        f"- Recipe name: `{best_recipe['recipe_name']}`.",
        f"- Recipe family: `{best_recipe['recipe_family']}`.",
        "",
        "## Top candidate list",
        "",
        _markdown_table(report["top_candidates"], PUBLIC_TOP_CANDIDATE_COLUMNS),
        "",
        "## Actual breakouts",
        "",
        _pending_outcome_note(outcome_season) if outcomes_pending else _markdown_table(report["actual_breakouts"], PUBLIC_HITS_AND_MISSES_COLUMNS),
        "",
        "## Correctly surfaced breakouts",
        "",
        _pending_outcome_note(outcome_season) if outcomes_pending else _markdown_table(report["correctly_surfaced_breakouts"], PUBLIC_HITS_AND_MISSES_COLUMNS),
        "",
        "## Notable misses / false positives",
        "",
        "### False positives",
        "",
        _pending_outcome_note(outcome_season) if outcomes_pending else _markdown_table(report["notable_false_positives"], PUBLIC_HITS_AND_MISSES_COLUMNS),
        "",
        "### Misses",
        "",
        _pending_outcome_note(outcome_season) if outcomes_pending else _markdown_table(report["notable_misses"], PUBLIC_HITS_AND_MISSES_COLUMNS),
        "",
        "## Signal takeaways",
        "",
        *[f"- {line}" for line in report["signal_takeaways"]],
        "",
        "## Methodology summary",
        "",
        "See `wr_public_methodology_summary.md` for the source rules and public-safe formatting choices.",
        "",
        "## Limitations / disclaimer",
        "",
        "See `wr_public_disclaimer.md` for the retrospective-reporting guardrails and limitations.",
        "",
    ]
    return "\n".join(sections)


def _build_methodology_summary() -> str:
    return "\n".join(
        [
            "# WR Public Methodology Summary",
            "",
            "This report pack is a public-safe presentation layer built only from existing validated/exported artifacts.",
            "",
            "## What is included",
            "",
            "- Best-recipe selection copied from the deterministic recipe comparison summary.",
            "- Candidate ordering copied from the existing export candidate board.",
            "- Hits, false positives, and false negatives copied from the season-pair case-study outputs.",
            "- Simple descriptive averages and rounded numeric formatting for readability.",
            "",
            "## What is deliberately omitted",
            "",
            "- Internal-only IDs for source tables beyond player IDs already present in exports.",
            "- Formula-note fields, threshold debug fields, and implementation scaffolding.",
            "- Any rescoring, relabeling, or hidden adjustment of validated conclusions.",
            "",
            "## Public formatting rules",
            "",
            "- Numeric values are rounded for readability.",
            "- CSV columns are reduced to the most relevant public-facing fields.",
            "- Markdown sections and JSON keys are written in stable order for deterministic outputs.",
            "",
            "## Retrospective scope",
            "",
            "This pack describes what happened in the historical validation slice for one season pair. It is not a production forecasting workflow.",
            "",
        ]
    )


def _build_disclaimer() -> str:
    return "\n".join(
        [
            "# WR Public Disclaimer",
            "",
            "This material is retrospective validation reporting only.",
            "",
            "- It does not train a model.",
            "- It does not create live rankings or guarantees about future seasons.",
            "- Breakout outcomes come from the repository's existing label definitions and inherit their simplifications.",
            "- Surfaced hits and misses depend on the documented cutoff used in the upstream case study.",
            "- Public artifacts intentionally omit internal scaffolding and formula-level implementation detail for clarity.",
            "",
            "Use these outputs as a readable summary of validated research, not as a promise machine.",
            "",
        ]
    )


def _build_actual_breakouts(
    hits_rows: list[dict[str, Any]],
    false_negative_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = [_public_outcome_row("actual_breakout", row) for row in hits_rows + false_negative_rows]
    return sorted(rows, key=lambda row: (int(row["rank"]), row["player_name"]))


def _build_signal_takeaways(
    all_candidates: list[dict[str, Any]],
    hits_rows: list[dict[str, Any]],
    false_positive_rows: list[dict[str, Any]],
    false_negative_rows: list[dict[str, Any]],
    *,
    outcomes_pending: bool,
    outcome_season: int,
) -> list[str]:
    top_slice = all_candidates[: min(5, len(all_candidates))]
    takeaways = [
        (
            "The top surfaced candidates averaged "
            f"{_average_nested(top_slice, ('component_scores', 'usage_signal'))} usage, "
            f"{_average_nested(top_slice, ('component_scores', 'efficiency_signal'))} efficiency, and "
            f"{_average_nested(top_slice, ('component_scores', 'development_signal'))} development signal."
        )
    ]
    if outcomes_pending:
        takeaways.extend(
            [
                (
                    f"This season pair is still waiting on complete {outcome_season} outcome data, so hit/miss "
                    f"comparisons remain pending."
                ),
                "Player-level miss labels will populate after the pending outcome season is complete.",
            ]
        )
    else:
        takeaways.extend(
            [
                (
                    "Correctly surfaced breakouts averaged "
                    f"{_average_field(hits_rows, 'actual_minus_expected_ppg')} actual-minus-expected PPG, versus "
                    f"{_average_field(false_positive_rows, 'actual_minus_expected_ppg')} for false positives."
                ),
                (
                    "Missed breakouts outside the surfaced cutoff still carried "
                    f"{_average_field(false_negative_rows, 'usage_signal')} average usage signal and "
                    f"{_average_field(false_negative_rows, 'development_signal')} average development signal."
                ),
            ]
        )
    return takeaways


def _season_pair_outcome_status(
    rows: list[dict[str, Any]],
    *,
    feature_season: int,
    outcome_season: int,
) -> dict[str, int | bool]:
    pair_rows = [
        row
        for row in rows
        if int(row["feature_season"]) == feature_season and int(row["outcome_season"]) == outcome_season
    ]
    valid_outcome_rows = sum(1 for row in pair_rows if _as_bool(row.get("has_valid_outcome")))
    missing_outcome_rows = len(pair_rows) - valid_outcome_rows
    return {
        "total_pair_rows": len(pair_rows),
        "valid_outcome_rows": valid_outcome_rows,
        "missing_outcome_rows": missing_outcome_rows,
        "outcomes_pending": bool(pair_rows) and valid_outcome_rows == 0 and missing_outcome_rows == len(pair_rows),
    }


def _pending_outcome_note(outcome_season: int) -> str:
    return (
        f"Outcomes pending: final {outcome_season} hit/miss evaluation will appear here once "
        f"valid outcome data is complete."
    )


def _public_candidate_row(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank": int(candidate["candidate_rank"]),
        "player_name": str(candidate["player_name"]),
        "team": str(candidate["role_context"].get("feature_team", "")),
        "signal_score": _format_number(candidate["final_signal_score"]),
        "feature_ppg": _format_number(candidate["role_context"].get("feature_ppg"), digits=1),
        "feature_targets_per_game": _format_number(candidate["role_context"].get("feature_targets_per_game"), digits=1),
        "breakout_result": "actual_breakout" if bool(candidate["breakout_label_default"]) else "no_breakout",
        "breakout_reason": str(candidate["breakout_reason"]),
    }


def _public_outcome_row(category: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "category": category,
        "rank": int(row["rank"]),
        "player_name": str(row["player_name"]),
        "team": str(row["feature_team"]),
        "signal_score": _format_number(row["wr_signal_score"]),
        "feature_ppg": _format_number(row["feature_ppg"], digits=1),
        "outcome_ppg": _format_number(row.get("outcome_ppg"), digits=1),
        "breakout_result": "actual_breakout" if _as_bool(row["breakout_label_default"]) else "no_breakout",
        "breakout_reason": str(row["breakout_reason"]),
    }


def _validate_requested_pair(payload: dict[str, Any], feature_season: int, outcome_season: int, label: str) -> None:
    if int(payload["feature_season"]) != feature_season or int(payload["outcome_season"]) != outcome_season:
        raise ValueError(
            f"{label} does not match requested season pair {feature_season} -> {outcome_season}"
        )


def _recipe_family(best_recipe: dict[str, Any]) -> str:
    metrics = best_recipe.get("metrics")
    if isinstance(metrics, dict) and metrics.get("recipe_family"):
        return str(metrics["recipe_family"])
    recipe_name = str(best_recipe["recipe_name"])
    if recipe_name.startswith("role_"):
        return "role"
    if recipe_name.startswith("cohort_"):
        return "cohort"
    return "base"


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
    values = [float(row[field]) for row in rows if row.get(field) not in (None, "")]
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
        raise ValueError(f"required public-report source does not exist: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv_dicts(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"required public-report source does not exist: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _format_number(value: Any, digits: int = 2) -> str:
    if value in (None, ""):
        return "n/a"
    return f"{float(value):.{digits}f}"


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"
