"""Deterministic WR breakout labeling and validation dataset assembly."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from src.validation import ValidationError

TOP_24_FINISH_THRESHOLD = 24
PPG_JUMP_THRESHOLD = 3.0
EXPECTED_PPG_BEAT_THRESHOLD = 2.0
EXPECTED_PPG_BASELINE_WEIGHTS = {
    "feature_ppg": 0.7,
    "targets_per_game": 0.2,
    "target_share": 10.0,
}

WR_VALIDATION_DATASET_COLUMNS = [
    "player_id",
    "player_name",
    "feature_season",
    "outcome_season",
    "position",
    "feature_team",
    "outcome_team",
    "has_valid_outcome",
    "feature_games_played",
    "outcome_games_played",
    "feature_total_ppr",
    "outcome_total_ppr",
    "feature_ppg",
    "outcome_ppg",
    "ppg_delta_next_season",
    "feature_finish",
    "outcome_finish",
    "finish_delta_next_season",
    "feature_targets_per_game",
    "outcome_targets_per_game",
    "feature_target_share",
    "expected_ppg_baseline",
    "actual_minus_expected_ppg",
    "is_new_fantasy_starter",
    "breakout_reason",
    "breakout_label_default",
    "breakout_label_ppg_jump",
    "breakout_label_top24_jump",
]

WR_BREAKOUT_LABEL_COLUMNS = [
    "player_id",
    "player_name",
    "feature_season",
    "outcome_season",
    "has_valid_outcome",
    "breakout_label_default",
    "breakout_label_ppg_jump",
    "breakout_label_top24_jump",
    "breakout_reason",
]


def build_wr_validation_dataset(
    feature_rows: Iterable[dict[str, object]],
    outcome_rows: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    """Build a canonical joined WR validation dataset from feature and outcome season rows."""

    normalized_features = [_normalize_feature_row(row) for row in feature_rows]
    normalized_outcomes = [_normalize_outcome_row(row) for row in outcome_rows]

    _validate_feature_rows(normalized_features)
    _validate_outcome_rows(normalized_outcomes)

    feature_finishes = _compute_finish_ranks(
        rows=normalized_features,
        season_key="feature_season",
        ppg_key="feature_ppg",
        total_ppr_key="feature_total_ppr",
    )
    outcome_finishes = _compute_finish_ranks(
        rows=normalized_outcomes,
        season_key="outcome_season",
        ppg_key="outcome_ppg",
        total_ppr_key="outcome_total_ppr",
    )

    outcomes_by_key = {
        (row["player_id"], row["feature_season"], row["outcome_season"]): row
        for row in normalized_outcomes
    }

    dataset_rows: list[dict[str, object]] = []
    for feature_row in sorted(
        normalized_features,
        key=lambda row: (row["player_id"], row["feature_season"], row["outcome_season"]),
    ):
        key = (feature_row["player_id"], feature_row["feature_season"], feature_row["outcome_season"])
        outcome_row = outcomes_by_key.get(key)
        dataset_rows.append(
            _build_dataset_row(
                feature_row=feature_row,
                outcome_row=outcome_row,
                feature_finish=feature_finishes[(feature_row["feature_season"], feature_row["player_id"])],
                outcome_finish=(
                    outcome_finishes[(outcome_row["outcome_season"], outcome_row["player_id"])]
                    if outcome_row is not None
                    else None
                ),
            )
        )

    return [
        {column: row[column] for column in WR_VALIDATION_DATASET_COLUMNS}
        for row in dataset_rows
    ]


def write_wr_label_outputs(
    processed_dir: str | Path,
    output_dir: str | Path,
) -> dict[str, Path]:
    """Read processed WR tables, build labels, and write deterministic validation artifacts."""

    processed_dir = Path(processed_dir)
    output_dir = Path(output_dir)
    feature_path = processed_dir / "wr_feature_seasons.csv"
    outcome_path = processed_dir / "wr_outcome_seasons.csv"

    if not feature_path.exists():
        raise ValidationError(f"processed feature table does not exist: {feature_path}")
    if not outcome_path.exists():
        raise ValidationError(f"processed outcome table does not exist: {outcome_path}")

    feature_rows = _read_csv_rows(feature_path)
    outcome_rows = _read_csv_rows(outcome_path)
    dataset_rows = build_wr_validation_dataset(feature_rows=feature_rows, outcome_rows=outcome_rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    validation_dataset_path = output_dir / "wr_validation_dataset.csv"
    label_path = output_dir / "wr_breakout_labels.csv"
    summary_path = output_dir / "wr_label_summary.json"
    examples_path = output_dir / "wr_label_examples.md"

    _write_csv(validation_dataset_path, WR_VALIDATION_DATASET_COLUMNS, dataset_rows)
    _write_csv(
        label_path,
        WR_BREAKOUT_LABEL_COLUMNS,
        [{column: row[column] for column in WR_BREAKOUT_LABEL_COLUMNS} for row in dataset_rows],
    )

    summary = build_label_summary(dataset_rows)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    examples_path.write_text(build_label_examples_markdown(dataset_rows), encoding="utf-8")

    return {
        "wr_breakout_labels": label_path,
        "wr_validation_dataset": validation_dataset_path,
        "wr_label_summary": summary_path,
        "wr_label_examples": examples_path,
    }


def build_label_summary(dataset_rows: Iterable[dict[str, object]]) -> dict[str, object]:
    """Build a deterministic JSON-serializable summary for labeled WR validation rows."""

    rows = list(dataset_rows)
    reason_counts = Counter(str(row["breakout_reason"]) for row in rows)
    label_counts = {
        "breakout_label_default": sum(1 for row in rows if bool(row["breakout_label_default"])),
        "breakout_label_ppg_jump": sum(1 for row in rows if bool(row["breakout_label_ppg_jump"])),
        "breakout_label_top24_jump": sum(1 for row in rows if bool(row["breakout_label_top24_jump"])),
    }

    return {
        "position": "WR",
        "row_count": len(rows),
        "valid_outcome_count": sum(1 for row in rows if bool(row["has_valid_outcome"])),
        "missing_outcome_count": sum(1 for row in rows if not bool(row["has_valid_outcome"])),
        "feature_seasons": sorted({int(row["feature_season"]) for row in rows}),
        "outcome_seasons": sorted({int(row["outcome_season"]) for row in rows}),
        "label_counts": label_counts,
        "breakout_reason_counts": dict(sorted(reason_counts.items())),
        "thresholds": {
            "top_24_finish_threshold": TOP_24_FINISH_THRESHOLD,
            "ppg_jump_threshold": PPG_JUMP_THRESHOLD,
            "expected_ppg_beat_threshold": EXPECTED_PPG_BEAT_THRESHOLD,
            "expected_ppg_baseline_weights": EXPECTED_PPG_BASELINE_WEIGHTS,
        },
    }


def build_label_examples_markdown(dataset_rows: Iterable[dict[str, object]]) -> str:
    """Build deterministic markdown examples for breakout labels and edge cases."""

    rows = sorted(
        list(dataset_rows),
        key=lambda row: (
            not bool(row["breakout_label_default"]),
            row["breakout_reason"],
            row["feature_season"],
            row["player_id"],
        ),
    )

    positives = [row for row in rows if bool(row["breakout_label_default"])]
    negatives = [row for row in rows if not bool(row["breakout_label_default"]) and bool(row["has_valid_outcome"])]
    missing = [row for row in rows if not bool(row["has_valid_outcome"])]

    sections = [
        "# WR Breakout Label Examples",
        "",
        "These examples are deterministic slices of the joined WR validation dataset.",
        "",
        "## Default-label breakouts",
        _build_examples_table(positives[:5]),
        "",
        "## Non-breakout rows with valid outcomes",
        _build_examples_table(negatives[:5]),
        "",
        "## Missing-outcome rows",
        _build_examples_table(missing[:5]),
        "",
    ]
    return "\n".join(sections)


def _build_dataset_row(
    feature_row: dict[str, object],
    outcome_row: dict[str, object] | None,
    feature_finish: int,
    outcome_finish: int | None,
) -> dict[str, object]:
    has_valid_outcome = outcome_row is not None
    feature_ppg = float(feature_row["feature_ppg"])
    expected_ppg_baseline = _compute_expected_ppg_baseline(feature_row)

    outcome_ppg = float(outcome_row["outcome_ppg"]) if outcome_row is not None else None
    ppg_delta_next_season = (
        round(outcome_ppg - feature_ppg, 4) if outcome_ppg is not None else None
    )
    actual_minus_expected_ppg = (
        round(outcome_ppg - expected_ppg_baseline, 4) if outcome_ppg is not None else None
    )
    finish_delta_next_season = (
        feature_finish - outcome_finish if outcome_finish is not None else None
    )

    breakout_label_top24_jump = bool(
        has_valid_outcome
        and outcome_finish is not None
        and outcome_finish <= TOP_24_FINISH_THRESHOLD
        and feature_finish > TOP_24_FINISH_THRESHOLD
    )
    breakout_label_ppg_jump = bool(
        has_valid_outcome
        and ppg_delta_next_season is not None
        and ppg_delta_next_season > PPG_JUMP_THRESHOLD
    )
    breakout_label_expected_baseline = bool(
        has_valid_outcome
        and actual_minus_expected_ppg is not None
        and actual_minus_expected_ppg > EXPECTED_PPG_BEAT_THRESHOLD
    )
    breakout_label_default = bool(
        breakout_label_top24_jump or breakout_label_ppg_jump or breakout_label_expected_baseline
    )

    if not has_valid_outcome:
        breakout_reason = "missing_outcome"
    elif breakout_label_top24_jump:
        breakout_reason = "top24_jump"
    elif breakout_label_ppg_jump:
        breakout_reason = "ppg_jump"
    elif breakout_label_expected_baseline:
        breakout_reason = "beat_expected_baseline"
    else:
        breakout_reason = "no_breakout_trigger"

    return {
        "player_id": feature_row["player_id"],
        "player_name": feature_row["player_name"],
        "feature_season": feature_row["feature_season"],
        "outcome_season": feature_row["outcome_season"],
        "position": "WR",
        "feature_team": feature_row["feature_team"],
        "outcome_team": outcome_row["outcome_team"] if outcome_row is not None else None,
        "has_valid_outcome": has_valid_outcome,
        "feature_games_played": feature_row["feature_games_played"],
        "outcome_games_played": outcome_row["outcome_games_played"] if outcome_row is not None else None,
        "feature_total_ppr": feature_row["feature_total_ppr"],
        "outcome_total_ppr": outcome_row["outcome_total_ppr"] if outcome_row is not None else None,
        "feature_ppg": feature_ppg,
        "outcome_ppg": outcome_ppg,
        "ppg_delta_next_season": ppg_delta_next_season,
        "feature_finish": feature_finish,
        "outcome_finish": outcome_finish,
        "finish_delta_next_season": finish_delta_next_season,
        "feature_targets_per_game": feature_row["feature_targets_per_game"],
        "outcome_targets_per_game": (
            outcome_row["outcome_targets_per_game"] if outcome_row is not None else None
        ),
        "feature_target_share": feature_row["feature_target_share"],
        "expected_ppg_baseline": expected_ppg_baseline,
        "actual_minus_expected_ppg": actual_minus_expected_ppg,
        "is_new_fantasy_starter": breakout_label_top24_jump,
        "breakout_reason": breakout_reason,
        "breakout_label_default": breakout_label_default,
        "breakout_label_ppg_jump": breakout_label_ppg_jump,
        "breakout_label_top24_jump": breakout_label_top24_jump,
    }


def _compute_expected_ppg_baseline(feature_row: dict[str, object]) -> float:
    target_share = float(feature_row["feature_target_share"] or 0.0)
    baseline = (
        float(feature_row["feature_ppg"]) * EXPECTED_PPG_BASELINE_WEIGHTS["feature_ppg"]
        + float(feature_row["feature_targets_per_game"])
        * EXPECTED_PPG_BASELINE_WEIGHTS["targets_per_game"]
        + target_share * EXPECTED_PPG_BASELINE_WEIGHTS["target_share"]
    )
    return round(baseline, 4)


def _compute_finish_ranks(
    rows: Iterable[dict[str, object]],
    season_key: str,
    ppg_key: str,
    total_ppr_key: str,
) -> dict[tuple[int, str], int]:
    by_season: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_season[int(row[season_key])].append(row)

    ranks: dict[tuple[int, str], int] = {}
    for season, season_rows in by_season.items():
        ordered = sorted(
            season_rows,
            key=lambda row: (
                -float(row[ppg_key]),
                -float(row[total_ppr_key]),
                str(row["player_id"]),
            ),
        )
        for index, row in enumerate(ordered, start=1):
            ranks[(season, str(row["player_id"]))] = index
    return ranks


def _normalize_feature_row(row: dict[str, object]) -> dict[str, object]:
    feature_season = _coerce_int(row.get("feature_season", row.get("season")), "feature season")
    outcome_season = _coerce_int(
        row.get("outcome_season", row.get("target_outcome_season")),
        "target outcome season",
    )
    return {
        "player_id": _coerce_str(row.get("player_id"), "player_id"),
        "player_name": _coerce_str(row.get("player_name"), "player_name"),
        "feature_season": feature_season,
        "outcome_season": outcome_season,
        "position": _coerce_str(row.get("position"), "position"),
        "feature_team": _coerce_str(row.get("team"), "team"),
        "feature_games_played": _coerce_int(row.get("games_played"), "games_played"),
        "feature_total_ppr": _coerce_float(row.get("total_ppr"), "total_ppr"),
        "feature_ppg": _coerce_float(row.get("ppg"), "ppg"),
        "feature_targets_per_game": _coerce_float(
            row.get("targets_per_game"),
            "targets_per_game",
        ),
        "feature_target_share": _coerce_optional_float(row.get("avg_target_share")),
    }


def _normalize_outcome_row(row: dict[str, object]) -> dict[str, object]:
    return {
        "player_id": _coerce_str(row.get("player_id"), "player_id"),
        "player_name": _coerce_str(row.get("player_name"), "player_name"),
        "feature_season": _coerce_int(row.get("feature_season"), "feature_season"),
        "outcome_season": _coerce_int(row.get("outcome_season"), "outcome_season"),
        "position": _coerce_str(row.get("position"), "position"),
        "outcome_team": _coerce_str(row.get("team"), "team"),
        "outcome_games_played": _coerce_int(
            row.get("outcome_games_played"),
            "outcome_games_played",
        ),
        "outcome_total_ppr": _coerce_float(
            row.get("outcome_total_ppr"),
            "outcome_total_ppr",
        ),
        "outcome_ppg": _coerce_float(row.get("outcome_ppg"), "outcome_ppg"),
        "outcome_targets_per_game": _coerce_float(
            row.get("outcome_targets_per_game"),
            "outcome_targets_per_game",
        ),
    }


def _validate_feature_rows(rows: list[dict[str, object]]) -> None:
    seen_keys: set[tuple[str, int, int]] = set()
    for row in rows:
        if row["position"] != "WR":
            raise ValidationError("feature rows may only contain WR players")
        if row["outcome_season"] != row["feature_season"] + 1:
            raise ValidationError("feature rows must target exactly the next season")
        key = (row["player_id"], row["feature_season"], row["outcome_season"])
        if key in seen_keys:
            raise ValidationError(f"duplicate feature key encountered: {key}")
        seen_keys.add(key)


def _validate_outcome_rows(rows: list[dict[str, object]]) -> None:
    seen_keys: set[tuple[str, int, int]] = set()
    for row in rows:
        if row["position"] != "WR":
            raise ValidationError("outcome rows may only contain WR players")
        if row["outcome_season"] != row["feature_season"] + 1:
            raise ValidationError("outcome rows must align to the immediately next season")
        key = (row["player_id"], row["feature_season"], row["outcome_season"])
        if key in seen_keys:
            raise ValidationError(f"duplicate outcome key encountered: {key}")
        seen_keys.add(key)


def _build_examples_table(rows: list[dict[str, object]]) -> str:
    if not rows:
        return "_No rows in this category._"

    lines = [
        "| player_id | feature_season | outcome_season | feature_ppg | outcome_ppg | reason |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        outcome_ppg = "" if row["outcome_ppg"] is None else f"{float(row['outcome_ppg']):.4f}"
        lines.append(
            "| {player_id} | {feature_season} | {outcome_season} | {feature_ppg:.4f} | {outcome_ppg} | {reason} |".format(
                player_id=row["player_id"],
                feature_season=row["feature_season"],
                outcome_season=row["outcome_season"],
                feature_ppg=float(row["feature_ppg"]),
                outcome_ppg=outcome_ppg,
                reason=row["breakout_reason"],
            )
        )
    return "\n".join(lines)


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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


def _coerce_str(value: object, label: str) -> str:
    if value is None or value == "":
        raise ValidationError(f"missing required {label}")
    return str(value)


def _coerce_int(value: object, label: str) -> int:
    if value is None or value == "":
        raise ValidationError(f"missing required {label}")
    return int(value)


def _coerce_float(value: object, label: str) -> float:
    if value is None or value == "":
        raise ValidationError(f"missing required {label}")
    return round(float(value), 4)


def _coerce_optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return round(float(value), 4)
