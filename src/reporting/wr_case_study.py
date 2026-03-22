"""Deterministic WR season-pair case-study reporting."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.scoring.recipes import RECIPES, SignalRecipe
from src.scoring.wr_signal_score import build_scored_candidates, read_validation_dataset

DEFAULT_SURFACED_RANK_CUTOFF = 20
CASE_STUDY_TABLE_LIMIT = 10
CASE_STUDY_OUTPUT_COLUMNS = [
    "player_id",
    "player_name",
    "feature_season",
    "outcome_season",
    "rank",
    "wr_signal_score",
    "breakout_label_default",
    "breakout_reason",
    "feature_team",
    "feature_ppg",
    "feature_finish",
    "feature_targets_per_game",
    "feature_target_share",
    "expected_ppg_baseline",
    "outcome_ppg",
    "outcome_finish",
    "ppg_delta_next_season",
    "actual_minus_expected_ppg",
    "usage_signal",
    "efficiency_signal",
    "development_signal",
    "stability_signal",
    "cohort_signal",
    "penalty_signal",
]


@dataclass(frozen=True)
class CaseStudyBestRecipe:
    recipe_name: str
    scoring_version: str
    metrics: dict[str, object]
    selection_rule: dict[str, object]


@dataclass(frozen=True)
class CaseStudyArtifacts:
    case_study_markdown_path: Path
    hits_csv_path: Path
    false_positives_csv_path: Path
    false_negatives_csv_path: Path
    winner_json_path: Path
    signal_patterns_markdown_path: Path


@dataclass(frozen=True)
class CaseStudyRow:
    player_id: str
    player_name: str
    feature_season: int
    outcome_season: int
    feature_team: str
    rank: int
    wr_signal_score: float
    breakout_label_default: bool
    breakout_reason: str
    feature_ppg: float
    feature_finish: int
    feature_targets_per_game: float
    feature_target_share: float | None
    expected_ppg_baseline: float
    outcome_ppg: float | None
    outcome_finish: int | None
    ppg_delta_next_season: float | None
    actual_minus_expected_ppg: float | None
    usage_signal: float
    efficiency_signal: float
    development_signal: float
    stability_signal: float
    cohort_signal: float
    penalty_signal: float

    def to_csv_row(self) -> dict[str, object]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "feature_season": self.feature_season,
            "outcome_season": self.outcome_season,
            "rank": self.rank,
            "wr_signal_score": self.wr_signal_score,
            "breakout_label_default": self.breakout_label_default,
            "breakout_reason": self.breakout_reason,
            "feature_team": self.feature_team,
            "feature_ppg": self.feature_ppg,
            "feature_finish": self.feature_finish,
            "feature_targets_per_game": self.feature_targets_per_game,
            "feature_target_share": self.feature_target_share,
            "expected_ppg_baseline": self.expected_ppg_baseline,
            "outcome_ppg": self.outcome_ppg,
            "outcome_finish": self.outcome_finish,
            "ppg_delta_next_season": self.ppg_delta_next_season,
            "actual_minus_expected_ppg": self.actual_minus_expected_ppg,
            "usage_signal": self.usage_signal,
            "efficiency_signal": self.efficiency_signal,
            "development_signal": self.development_signal,
            "stability_signal": self.stability_signal,
            "cohort_signal": self.cohort_signal,
            "penalty_signal": self.penalty_signal,
        }


def build_wr_case_study(
    validation_dataset_path: str | Path,
    comparison_summary_path: str | Path,
    candidate_dir: str | Path,
    output_dir: str | Path,
    feature_season: int,
    outcome_season: int,
    surfaced_rank_cutoff: int = DEFAULT_SURFACED_RANK_CUTOFF,
) -> CaseStudyArtifacts:
    """Build deterministic season-pair WR case-study artifacts from existing validation outputs."""

    if surfaced_rank_cutoff <= 0:
        raise ValueError("surfaced_rank_cutoff must be positive")

    dataset_path = Path(validation_dataset_path)
    comparison_path = Path(comparison_summary_path)
    candidate_dir = Path(candidate_dir)
    output_dir = Path(output_dir)

    validation_rows = read_validation_dataset(dataset_path)
    best_recipe = load_best_recipe_from_summary(comparison_path)
    recipe = _recipe_from_best_recipe(best_recipe)
    candidate_rows = read_candidate_rankings(candidate_dir / f"wr_candidate_rankings_{best_recipe.recipe_name}.csv")
    season_rows = build_case_study_rows(
        validation_rows=validation_rows,
        candidate_rows=candidate_rows,
        recipe=recipe,
        feature_season=feature_season,
        outcome_season=outcome_season,
    )

    if not season_rows:
        raise ValueError(
            f"no validation rows found for season pair {feature_season} -> {outcome_season}"
        )

    pair_rows = [row for row in season_rows if row.feature_season == feature_season and row.outcome_season == outcome_season]
    valid_rows = [row for row in pair_rows if row.outcome_ppg is not None]
    missing_outcomes = [row for row in pair_rows if row.outcome_ppg is None]

    hits = [row for row in valid_rows if row.rank <= surfaced_rank_cutoff and row.breakout_label_default]
    false_positives = [row for row in valid_rows if row.rank <= surfaced_rank_cutoff and not row.breakout_label_default]
    false_negatives = [row for row in valid_rows if row.rank > surfaced_rank_cutoff and row.breakout_label_default]
    actual_breakouts = [row for row in valid_rows if row.breakout_label_default]
    surfaced_candidates = [row for row in valid_rows if row.rank <= surfaced_rank_cutoff]

    output_dir.mkdir(parents=True, exist_ok=True)
    season_suffix = f"{feature_season}_to_{outcome_season}"
    case_study_markdown_path = output_dir / f"wr_breakout_case_study_{season_suffix}.md"
    hits_csv_path = output_dir / f"wr_breakout_hits_{season_suffix}.csv"
    false_positives_csv_path = output_dir / f"wr_breakout_false_positives_{season_suffix}.csv"
    false_negatives_csv_path = output_dir / f"wr_breakout_false_negatives_{season_suffix}.csv"
    winner_json_path = output_dir / f"wr_recipe_winner_{season_suffix}.json"
    signal_patterns_markdown_path = output_dir / f"wr_signal_patterns_{season_suffix}.md"

    _write_csv(hits_csv_path, CASE_STUDY_OUTPUT_COLUMNS, [row.to_csv_row() for row in hits])
    _write_csv(
        false_positives_csv_path,
        CASE_STUDY_OUTPUT_COLUMNS,
        [row.to_csv_row() for row in false_positives],
    )
    _write_csv(
        false_negatives_csv_path,
        CASE_STUDY_OUTPUT_COLUMNS,
        [row.to_csv_row() for row in false_negatives],
    )

    signal_patterns = build_signal_patterns_markdown(
        hits=hits,
        false_positives=false_positives,
        false_negatives=false_negatives,
        actual_breakouts=actual_breakouts,
        surfaced_candidates=surfaced_candidates,
        surfaced_rank_cutoff=surfaced_rank_cutoff,
        feature_season=feature_season,
        outcome_season=outcome_season,
    )
    signal_patterns_markdown_path.write_text(signal_patterns, encoding="utf-8")

    case_study_markdown_path.write_text(
        build_case_study_markdown(
            best_recipe=best_recipe,
            pair_rows=pair_rows,
            valid_rows=valid_rows,
            missing_outcomes=missing_outcomes,
            hits=hits,
            false_positives=false_positives,
            false_negatives=false_negatives,
            actual_breakouts=actual_breakouts,
            surfaced_candidates=surfaced_candidates,
            surfaced_rank_cutoff=surfaced_rank_cutoff,
            feature_season=feature_season,
            outcome_season=outcome_season,
        ),
        encoding="utf-8",
    )

    winner_json_path.write_text(
        json.dumps(
            build_case_study_winner_summary(
                best_recipe=best_recipe,
                feature_season=feature_season,
                outcome_season=outcome_season,
                surfaced_rank_cutoff=surfaced_rank_cutoff,
                total_pair_rows=len(pair_rows),
                valid_outcome_rows=len(valid_rows),
                missing_outcome_rows=len(missing_outcomes),
                hit_count=len(hits),
                false_positive_count=len(false_positives),
                false_negative_count=len(false_negatives),
                actual_breakout_count=len(actual_breakouts),
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return CaseStudyArtifacts(
        case_study_markdown_path=case_study_markdown_path,
        hits_csv_path=hits_csv_path,
        false_positives_csv_path=false_positives_csv_path,
        false_negatives_csv_path=false_negatives_csv_path,
        winner_json_path=winner_json_path,
        signal_patterns_markdown_path=signal_patterns_markdown_path,
    )


def load_best_recipe_from_summary(path: str | Path) -> CaseStudyBestRecipe:
    summary_path = Path(path)
    if not summary_path.exists():
        raise ValueError(f"recipe comparison summary does not exist: {summary_path}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    best_recipe = summary.get("best_recipe")
    if not isinstance(best_recipe, dict):
        raise ValueError("recipe comparison summary is missing best_recipe")

    recipe_name = best_recipe.get("recipe_name")
    scoring_version = best_recipe.get("scoring_version")
    metrics = best_recipe.get("metrics")
    selection_rule = summary.get("best_recipe_rule")
    if not isinstance(recipe_name, str) or not recipe_name:
        raise ValueError("best_recipe.recipe_name must be a non-empty string")
    if not isinstance(scoring_version, str) or not scoring_version:
        raise ValueError("best_recipe.scoring_version must be a non-empty string")
    if not isinstance(metrics, dict):
        raise ValueError("best_recipe.metrics must be an object")
    if not isinstance(selection_rule, dict):
        raise ValueError("best_recipe_rule must be an object")

    return CaseStudyBestRecipe(
        recipe_name=recipe_name,
        scoring_version=scoring_version,
        metrics=metrics,
        selection_rule=selection_rule,
    )


def read_candidate_rankings(path: str | Path) -> list[dict[str, object]]:
    ranking_path = Path(path)
    if not ranking_path.exists():
        raise ValueError(f"candidate rankings do not exist: {ranking_path}")

    with ranking_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("candidate rankings must contain a header row")
        required = {"player_id", "feature_season", "outcome_season", "rank", "wr_signal_score"}
        missing = sorted(required - set(reader.fieldnames))
        if missing:
            raise ValueError(f"candidate rankings are missing required columns: {missing}")
        return [_normalize_candidate_row(row) for row in reader]


def build_case_study_rows(
    validation_rows: Iterable[dict[str, object]],
    candidate_rows: Iterable[dict[str, object]],
    recipe: SignalRecipe,
    feature_season: int,
    outcome_season: int,
) -> list[CaseStudyRow]:
    filtered_validation_rows = [
        row
        for row in validation_rows
        if int(row["feature_season"]) == feature_season and int(row["outcome_season"]) == outcome_season
    ]
    scored_rows = build_scored_candidates(filtered_validation_rows, recipe=recipe)
    scored_by_key = {(row.player_id, row.feature_season, row.outcome_season): row for row in scored_rows}
    validation_by_key = {
        (str(row["player_id"]), int(row["feature_season"]), int(row["outcome_season"])): row
        for row in filtered_validation_rows
    }

    merged_rows: list[CaseStudyRow] = []
    for candidate in sorted(candidate_rows, key=lambda row: (row["feature_season"], row["rank"], row["player_id"])):
        key = (str(candidate["player_id"]), int(candidate["feature_season"]), int(candidate["outcome_season"]))
        if key not in validation_by_key or key not in scored_by_key:
            continue
        if key[1] != feature_season or key[2] != outcome_season:
            continue
        validation = validation_by_key[key]
        scored = scored_by_key[key]
        merged_rows.append(
            CaseStudyRow(
                player_id=str(validation["player_id"]),
                player_name=str(validation["player_name"]),
                feature_season=int(validation["feature_season"]),
                outcome_season=int(validation["outcome_season"]),
                feature_team=str(validation["feature_team"]),
                rank=int(candidate["rank"]),
                wr_signal_score=float(candidate["wr_signal_score"]),
                breakout_label_default=bool(validation["breakout_label_default"]),
                breakout_reason=str(validation["breakout_reason"]),
                feature_ppg=float(validation["feature_ppg"]),
                feature_finish=int(validation["feature_finish"]),
                feature_targets_per_game=float(validation["feature_targets_per_game"]),
                feature_target_share=_optional_float(validation.get("feature_target_share")),
                expected_ppg_baseline=float(validation["expected_ppg_baseline"]),
                outcome_ppg=_optional_float(validation.get("outcome_ppg")),
                outcome_finish=_optional_int(validation.get("outcome_finish")),
                ppg_delta_next_season=_optional_float(validation.get("ppg_delta_next_season")),
                actual_minus_expected_ppg=_optional_float(validation.get("actual_minus_expected_ppg")),
                usage_signal=scored.usage_signal,
                efficiency_signal=scored.efficiency_signal,
                development_signal=scored.development_signal,
                stability_signal=scored.stability_signal,
                cohort_signal=scored.cohort_signal,
                penalty_signal=scored.penalty_signal,
            )
        )

    return merged_rows


def build_case_study_winner_summary(
    *,
    best_recipe: CaseStudyBestRecipe,
    feature_season: int,
    outcome_season: int,
    surfaced_rank_cutoff: int,
    total_pair_rows: int,
    valid_outcome_rows: int,
    missing_outcome_rows: int,
    hit_count: int,
    false_positive_count: int,
    false_negative_count: int,
    actual_breakout_count: int,
) -> dict[str, object]:
    return {
        "position": "WR",
        "feature_season": feature_season,
        "outcome_season": outcome_season,
        "surfaced_rank_cutoff": surfaced_rank_cutoff,
        "best_recipe": {
            "recipe_name": best_recipe.recipe_name,
            "scoring_version": best_recipe.scoring_version,
            "metrics": best_recipe.metrics,
            "selection_rule": best_recipe.selection_rule,
        },
        "season_pair_summary": {
            "total_pair_rows": total_pair_rows,
            "valid_outcome_rows": valid_outcome_rows,
            "missing_outcome_rows": missing_outcome_rows,
            "actual_breakout_count": actual_breakout_count,
            "hit_count": hit_count,
            "false_positive_count": false_positive_count,
            "false_negative_count": false_negative_count,
        },
    }


def build_case_study_markdown(
    *,
    best_recipe: CaseStudyBestRecipe,
    pair_rows: list[CaseStudyRow],
    valid_rows: list[CaseStudyRow],
    missing_outcomes: list[CaseStudyRow],
    hits: list[CaseStudyRow],
    false_positives: list[CaseStudyRow],
    false_negatives: list[CaseStudyRow],
    actual_breakouts: list[CaseStudyRow],
    surfaced_candidates: list[CaseStudyRow],
    surfaced_rank_cutoff: int,
    feature_season: int,
    outcome_season: int,
) -> str:
    reason_counts = Counter(row.breakout_reason for row in hits)
    top_reason_text = ", ".join(
        f"`{reason}` ({count})" for reason, count in sorted(reason_counts.items())
    ) or "none"

    sections = [
        f"# WR Breakout Case Study: {feature_season} to {outcome_season}",
        "",
        "## Executive summary",
        "",
        (
            f"- Best recipe from the comparison summary: `{best_recipe.recipe_name}` "
            f"(`{best_recipe.scoring_version}`)."
        ),
        (
            f"- Evaluated {len(valid_rows)} of {len(pair_rows)} rows for this season pair; "
            f"{len(missing_outcomes)} rows were excluded because the outcome season is missing."
        ),
        (
            f"- Using a surfaced cutoff of top {surfaced_rank_cutoff}, the model produced "
            f"{len(hits)} hits, {len(false_positives)} false positives, and {len(false_negatives)} false negatives."
        ),
        (
            f"- Actual breakout count for {outcome_season}: {len(actual_breakouts)}. "
            f"Hit-rate within surfaced candidates: {_ratio(len(hits), len(surfaced_candidates))}."
        ),
        f"- Breakout reasons represented among hits: {top_reason_text}.",
        "",
        "## Best recipe for this season pair",
        "",
        f"- Recipe selection is sourced from the deterministic recipe comparison summary, not from the case-study layer.",
        f"- Primary metric: `{best_recipe.selection_rule.get('primary_metric', 'unknown')}`.",
        (
            f"- Tie-breakers: {', '.join(best_recipe.selection_rule.get('tie_breakers', [])) or 'none documented'}."
        ),
        (
            f"- Pair-level comparison metrics copied from the summary: precision@20="
            f"{_format_metric(best_recipe.metrics.get('precision_at_20'))}, recall@20="
            f"{_format_metric(best_recipe.metrics.get('recall_at_20'))}, average breakout rank="
            f"{_format_metric(best_recipe.metrics.get('average_breakout_rank'))}."
        ),
        "",
        f"## Top flagged candidates from `{best_recipe.recipe_name}`",
        "",
        _markdown_table(surfaced_candidates[:CASE_STUDY_TABLE_LIMIT]),
        "",
        "## Actual breakouts",
        "",
        _markdown_table(actual_breakouts, include_outcome=True),
        "",
        "## Correctly surfaced breakouts",
        "",
        _markdown_table(hits, include_outcome=True),
        "",
        "## False positives",
        "",
        _markdown_table(false_positives, include_outcome=True),
        "",
        "## False negatives",
        "",
        _markdown_table(false_negatives, include_outcome=True),
        "",
        "## Key signal patterns in hits vs misses",
        "",
        f"- Average usage signal — hits: {_mean(hits, 'usage_signal')}, false positives: {_mean(false_positives, 'usage_signal')}, false negatives: {_mean(false_negatives, 'usage_signal')}." ,
        f"- Average efficiency signal — hits: {_mean(hits, 'efficiency_signal')}, false positives: {_mean(false_positives, 'efficiency_signal')}, false negatives: {_mean(false_negatives, 'efficiency_signal')}." ,
        f"- Average development signal — hits: {_mean(hits, 'development_signal')}, false positives: {_mean(false_positives, 'development_signal')}, false negatives: {_mean(false_negatives, 'development_signal')}." ,
        (
            f"- Average actual-minus-expected PPG — hits: {_mean(hits, 'actual_minus_expected_ppg')}, "
            f"false positives: {_mean(false_positives, 'actual_minus_expected_ppg')}, "
            f"false negatives: {_mean(false_negatives, 'actual_minus_expected_ppg')}."
        ),
        (
            f"- False-positive miss pattern counts: below-hit-average usage="
            f"{_count_below_reference(false_positives, hits, 'usage_signal')}, below-hit-average efficiency="
            f"{_count_below_reference(false_positives, hits, 'efficiency_signal')}, non-positive actual-minus-expected PPG="
            f"{_count_non_positive(false_positives, 'actual_minus_expected_ppg')}."
        ),
        "",
        "## Limitations / cautions",
        "",
        "- This report is a deterministic retrospective validation slice, not a live projection engine or a claim of predictive certainty.",
        (
            f"- Hits, false positives, and false negatives are defined relative to the surfaced cutoff of top {surfaced_rank_cutoff}; changing that cutoff changes the case-study counts."
        ),
        "- Breakout labels come from the existing label engine and inherit its threshold definitions and simplifications.",
        "- If the validation dataset has missing outcome rows for the requested pair, those players are excluded from hit/miss accounting rather than guessed forward.",
        "",
    ]
    return "\n".join(sections)


def build_signal_patterns_markdown(
    *,
    hits: list[CaseStudyRow],
    false_positives: list[CaseStudyRow],
    false_negatives: list[CaseStudyRow],
    actual_breakouts: list[CaseStudyRow],
    surfaced_candidates: list[CaseStudyRow],
    surfaced_rank_cutoff: int,
    feature_season: int,
    outcome_season: int,
) -> str:
    lines = [
        f"# WR Signal Patterns: {feature_season} to {outcome_season}",
        "",
        (
            f"All summaries below are deterministic aggregates from the best-recipe rankings and the "
            f"validation dataset using a surfaced cutoff of top {surfaced_rank_cutoff}."
        ),
        "",
        "## Average component table",
        "",
        "| category | count | avg_score | avg_usage | avg_efficiency | avg_development | avg_stability | avg_cohort | avg_penalty | avg_actual_minus_expected_ppg |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for label, rows in [
        ("surfaced_candidates", surfaced_candidates),
        ("actual_breakouts", actual_breakouts),
        ("hits", hits),
        ("false_positives", false_positives),
        ("false_negatives", false_negatives),
    ]:
        lines.append(
            "| {label} | {count} | {score} | {usage} | {efficiency} | {development} | {stability} | {cohort} | {penalty} | {actual} |".format(
                label=label,
                count=len(rows),
                score=_mean(rows, "wr_signal_score"),
                usage=_mean(rows, "usage_signal"),
                efficiency=_mean(rows, "efficiency_signal"),
                development=_mean(rows, "development_signal"),
                stability=_mean(rows, "stability_signal"),
                cohort=_mean(rows, "cohort_signal"),
                penalty=_mean(rows, "penalty_signal"),
                actual=_mean(rows, "actual_minus_expected_ppg"),
            )
        )

    lines.extend(
        [
            "",
            "## Breakout reasons among hits",
            "",
            _markdown_count_table(Counter(row.breakout_reason for row in hits), header_name="breakout_reason"),
            "",
            "## False-positive miss patterns",
            "",
            f"- Below-hit-average usage signal: {_count_below_reference(false_positives, hits, 'usage_signal')}.",
            f"- Below-hit-average efficiency signal: {_count_below_reference(false_positives, hits, 'efficiency_signal')}.",
            f"- Below-hit-average development signal: {_count_below_reference(false_positives, hits, 'development_signal')}.",
            f"- Non-positive actual-minus-expected PPG: {_count_non_positive(false_positives, 'actual_minus_expected_ppg')}.",
            f"- Target share below 0.20: {_count_threshold(false_positives, 'feature_target_share', 0.20)}.",
            "",
            "## False-negative miss patterns",
            "",
            f"- Below-surfaced average usage signal: {_count_below_reference(false_negatives, surfaced_candidates, 'usage_signal')}.",
            f"- Below-surfaced average efficiency signal: {_count_below_reference(false_negatives, surfaced_candidates, 'efficiency_signal')}.",
            f"- Below-surfaced average stability signal: {_count_below_reference(false_negatives, surfaced_candidates, 'stability_signal')}.",
            f"- Positive actual-minus-expected PPG despite missing the cutoff: {_count_positive(false_negatives, 'actual_minus_expected_ppg')}.",
            "",
        ]
    )
    return "\n".join(lines)


def _recipe_from_best_recipe(best_recipe: CaseStudyBestRecipe) -> SignalRecipe:
    if best_recipe.recipe_name not in RECIPES:
        raise ValueError(f"best recipe is not defined locally: {best_recipe.recipe_name}")
    recipe = RECIPES[best_recipe.recipe_name]
    if recipe.scoring_version != best_recipe.scoring_version:
        raise ValueError(
            "best recipe scoring version mismatch: "
            f"summary={best_recipe.scoring_version}, local={recipe.scoring_version}"
        )
    return recipe


def _normalize_candidate_row(row: dict[str, str]) -> dict[str, object]:
    return {
        "player_id": row["player_id"],
        "feature_season": int(row["feature_season"]),
        "outcome_season": int(row["outcome_season"]),
        "rank": int(row["rank"]),
        "wr_signal_score": float(row["wr_signal_score"]),
    }


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


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


def _mean(rows: list[CaseStudyRow], attribute: str) -> str:
    values = [getattr(row, attribute) for row in rows]
    numeric_values = [float(value) for value in values if value is not None]
    if not numeric_values:
        return "n/a"
    return f"{sum(numeric_values) / len(numeric_values):.4f}"


def _ratio(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{numerator / denominator:.4f}"


def _format_metric(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _count_below_reference(rows: list[CaseStudyRow], reference_rows: list[CaseStudyRow], attribute: str) -> str:
    reference_values = [float(getattr(row, attribute)) for row in reference_rows if getattr(row, attribute) is not None]
    candidate_values = [float(getattr(row, attribute)) for row in rows if getattr(row, attribute) is not None]
    if not reference_values or not candidate_values:
        return "n/a"
    reference_mean = sum(reference_values) / len(reference_values)
    count = sum(1 for value in candidate_values if value < reference_mean)
    return f"{count}/{len(candidate_values)}"


def _count_non_positive(rows: list[CaseStudyRow], attribute: str) -> str:
    values = [getattr(row, attribute) for row in rows if getattr(row, attribute) is not None]
    if not values:
        return "n/a"
    count = sum(1 for value in values if float(value) <= 0.0)
    return f"{count}/{len(values)}"


def _count_positive(rows: list[CaseStudyRow], attribute: str) -> str:
    values = [getattr(row, attribute) for row in rows if getattr(row, attribute) is not None]
    if not values:
        return "n/a"
    count = sum(1 for value in values if float(value) > 0.0)
    return f"{count}/{len(values)}"


def _count_threshold(rows: list[CaseStudyRow], attribute: str, threshold: float) -> str:
    values = [getattr(row, attribute) for row in rows if getattr(row, attribute) is not None]
    if not values:
        return "n/a"
    count = sum(1 for value in values if float(value) < threshold)
    return f"{count}/{len(values)}"


def _markdown_count_table(counter: Counter[str], header_name: str) -> str:
    if not counter:
        return "_No rows in this category._"
    lines = [f"| {header_name} | count |", "| --- | ---: |"]
    for label, count in sorted(counter.items()):
        lines.append(f"| {label} | {count} |")
    return "\n".join(lines)


def _markdown_table(rows: list[CaseStudyRow], include_outcome: bool = False) -> str:
    if not rows:
        return "_No rows in this category._"

    if include_outcome:
        lines = [
            "| rank | player_name | feature_team | score | breakout_reason | outcome_ppg | outcome_finish | actual_minus_expected_ppg |",
            "| ---: | --- | --- | ---: | --- | ---: | ---: | ---: |",
        ]
        for row in rows:
            lines.append(
                "| {rank} | {player_name} | {team} | {score:.4f} | {reason} | {outcome_ppg} | {outcome_finish} | {actual_minus_expected} |".format(
                    rank=row.rank,
                    player_name=row.player_name,
                    team=row.feature_team,
                    score=row.wr_signal_score,
                    reason=row.breakout_reason,
                    outcome_ppg=_display_number(row.outcome_ppg),
                    outcome_finish=_display_number(row.outcome_finish),
                    actual_minus_expected=_display_number(row.actual_minus_expected_ppg),
                )
            )
        return "\n".join(lines)

    lines = [
        "| rank | player_name | feature_team | score | breakout_label | breakout_reason |",
        "| ---: | --- | --- | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {rank} | {player_name} | {team} | {score:.4f} | {label} | {reason} |".format(
                rank=row.rank,
                player_name=row.player_name,
                team=row.feature_team,
                score=row.wr_signal_score,
                label="true" if row.breakout_label_default else "false",
                reason=row.breakout_reason,
            )
        )
    return "\n".join(lines)


def _display_number(value: float | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    return f"{value:.4f}"
