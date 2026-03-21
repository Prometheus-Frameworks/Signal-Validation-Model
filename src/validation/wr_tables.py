"""Validation and I/O helpers for WR historical canonical tables."""

from __future__ import annotations

import csv
from pathlib import Path


class ValidationError(ValueError):
    """Raised when raw historical data or canonical tables are invalid."""


WR_RAW_REQUIRED_COLUMNS = [
    "player_id",
    "player_name",
    "team",
    "season",
    "week",
    "position",
    "fantasy_points_ppr",
    "targets",
    "receptions",
    "receiving_yards",
    "receiving_tds",
]

WR_RAW_OPTIONAL_COLUMNS = [
    "games",
    "active",
    "snap_share",
    "route_participation",
    "target_share",
    "air_yard_share",
]

WR_CANONICAL_COLUMN_ORDER = {
    "wr_player_weeks": [
        "player_id",
        "player_name",
        "team",
        "season",
        "week",
        "position",
        "week_is_active",
        "raw_games_value",
        "ppr_points",
        "targets",
        "receptions",
        "receiving_yards",
        "receiving_tds",
        "snap_share",
        "route_participation",
        "target_share",
        "air_yard_share",
    ],
    "wr_player_seasons": [
        "player_id",
        "player_name",
        "team",
        "season",
        "position",
        "weeks_recorded",
        "games_played",
        "total_ppr",
        "ppg",
        "spike_week_threshold",
        "spike_week_count",
        "spike_week_rate",
        "dud_week_threshold",
        "dud_week_count",
        "dud_week_rate",
        "total_targets",
        "targets_per_game",
        "total_receptions",
        "receptions_per_game",
        "total_receiving_yards",
        "receiving_yards_per_game",
        "total_receiving_tds",
        "receiving_tds_per_game",
        "avg_snap_share",
        "avg_route_participation",
        "avg_target_share",
        "avg_air_yard_share",
    ],
    "wr_feature_seasons": [
        "player_id",
        "player_name",
        "season",
        "target_outcome_season",
        "data_through_season",
        "position",
        "team",
        "games_played",
        "weeks_recorded",
        "total_ppr",
        "ppg",
        "spike_week_rate",
        "dud_week_rate",
        "total_targets",
        "targets_per_game",
        "total_receptions",
        "receptions_per_game",
        "total_receiving_yards",
        "receiving_yards_per_game",
        "total_receiving_tds",
        "receiving_tds_per_game",
        "avg_snap_share",
        "avg_route_participation",
        "avg_target_share",
        "avg_air_yard_share",
    ],
    "wr_outcome_seasons": [
        "player_id",
        "player_name",
        "feature_season",
        "outcome_season",
        "position",
        "team",
        "outcome_games_played",
        "outcome_total_ppr",
        "outcome_ppg",
        "outcome_spike_week_rate",
        "outcome_dud_week_rate",
        "outcome_total_targets",
        "outcome_targets_per_game",
        "outcome_total_receptions",
        "outcome_receptions_per_game",
        "outcome_total_receiving_yards",
        "outcome_receiving_yards_per_game",
        "outcome_total_receiving_tds",
        "outcome_receiving_tds_per_game",
    ],
}


def read_raw_wr_week_rows(input_path: Path) -> list[dict[str, object]]:
    """Read and validate a raw CSV of historical player-week rows for WR processing."""

    if not input_path.exists():
        raise ValidationError(f"input file does not exist: {input_path}")

    with input_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValidationError("raw CSV must contain a header row")

        missing_columns = [column for column in WR_RAW_REQUIRED_COLUMNS if column not in reader.fieldnames]
        if missing_columns:
            raise ValidationError(f"raw CSV is missing required columns: {missing_columns}")

        rows: list[dict[str, object]] = []
        seen_keys: set[tuple[str, int, int]] = set()
        for line_number, row in enumerate(reader, start=2):
            normalized = _normalize_raw_row(row=row, line_number=line_number)
            key = (
                str(normalized["player_id"]),
                int(normalized["season"]),
                int(normalized["week"]),
            )
            if key in seen_keys:
                raise ValidationError(
                    "duplicate WR weekly primary key encountered for "
                    f"player_id={key[0]}, season={key[1]}, week={key[2]}"
                )
            seen_keys.add(key)
            rows.append(normalized)

    rows.sort(key=lambda row: (row["player_id"], row["season"], row["week"]))
    return rows


def write_canonical_csv_tables(
    tables: dict[str, list[dict[str, object]]],
    output_dir: Path,
) -> dict[str, Path]:
    """Write canonical tables to deterministic CSV files with stable column ordering."""

    validate_canonical_tables(tables)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths: dict[str, Path] = {}

    for table_name, rows in tables.items():
        path = output_dir / f"{table_name}.csv"
        fieldnames = WR_CANONICAL_COLUMN_ORDER[table_name]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: _serialize_value(row.get(field)) for field in fieldnames})
        output_paths[table_name] = path

    return output_paths


def validate_canonical_tables(tables: dict[str, list[dict[str, object]]]) -> None:
    """Validate primary keys, position restrictions, leakage guardrails, and column ordering."""

    expected_tables = set(WR_CANONICAL_COLUMN_ORDER)
    if set(tables) != expected_tables:
        raise ValidationError(
            f"canonical table set must equal {sorted(expected_tables)}, got {sorted(tables)}"
        )

    _validate_table_rows(
        rows=tables["wr_player_weeks"],
        table_name="wr_player_weeks",
        key_columns=("player_id", "season", "week"),
    )
    _validate_table_rows(
        rows=tables["wr_player_seasons"],
        table_name="wr_player_seasons",
        key_columns=("player_id", "season"),
    )
    _validate_table_rows(
        rows=tables["wr_feature_seasons"],
        table_name="wr_feature_seasons",
        key_columns=("player_id", "season"),
    )
    _validate_table_rows(
        rows=tables["wr_outcome_seasons"],
        table_name="wr_outcome_seasons",
        key_columns=("player_id", "feature_season", "outcome_season"),
    )

    feature_columns = (
        list(tables["wr_feature_seasons"][0].keys())
        if tables["wr_feature_seasons"]
        else WR_CANONICAL_COLUMN_ORDER["wr_feature_seasons"]
    )
    for column in feature_columns:
        lowered = column.lower()
        if lowered.startswith("outcome_") or lowered.startswith("label_") or lowered.startswith("future_"):
            raise ValidationError(f"feature table contains forbidden future-looking column: {column}")

    for row in tables["wr_feature_seasons"]:
        if int(row["target_outcome_season"]) != int(row["season"]) + 1:
            raise ValidationError("feature rows must target exactly the next season")
        if int(row["data_through_season"]) > int(row["season"]):
            raise ValidationError("feature rows cannot contain data beyond their own season")

    for row in tables["wr_outcome_seasons"]:
        if int(row["outcome_season"]) != int(row["feature_season"]) + 1:
            raise ValidationError("outcome rows must align to the immediately preceding feature season")


def _validate_table_rows(
    rows: list[dict[str, object]],
    table_name: str,
    key_columns: tuple[str, ...],
) -> None:
    expected_columns = WR_CANONICAL_COLUMN_ORDER[table_name]
    seen_keys: set[tuple[object, ...]] = set()

    for row in rows:
        if list(row.keys()) != expected_columns:
            raise ValidationError(
                f"{table_name} columns must match canonical order {expected_columns}, got {list(row.keys())}"
            )
        if row["position"] != "WR":
            raise ValidationError(f"{table_name} may only contain WR rows")

        key = tuple(row[column] for column in key_columns)
        if key in seen_keys:
            raise ValidationError(f"duplicate primary key found in {table_name}: {key}")
        seen_keys.add(key)

        if "season" in row:
            _validate_season(int(row["season"]), field_name=f"{table_name}.season")
        if "feature_season" in row:
            _validate_season(int(row["feature_season"]), field_name=f"{table_name}.feature_season")
        if "outcome_season" in row:
            _validate_season(int(row["outcome_season"]), field_name=f"{table_name}.outcome_season")
        if "week" in row:
            _validate_week(int(row["week"]), field_name=f"{table_name}.week")


def _normalize_raw_row(row: dict[str, str], line_number: int) -> dict[str, object]:
    position = _require_text(row, "position", line_number).upper()
    if position != "WR":
        raise ValidationError(f"line {line_number}: only WR rows are supported, got {position}")

    season = _parse_int(row, "season", line_number)
    week = _parse_int(row, "week", line_number)
    _validate_season(season, field_name=f"line {line_number} season")
    _validate_week(week, field_name=f"line {line_number} week")

    games_value = _parse_optional_int(row.get("games"), "games", line_number)
    active_value = _parse_optional_bool(row.get("active"), "active", line_number)
    week_is_active = _resolve_week_is_active(games_value=games_value, active_value=active_value)

    normalized = {
        "player_id": _require_text(row, "player_id", line_number),
        "player_name": _require_text(row, "player_name", line_number),
        "team": _require_text(row, "team", line_number),
        "season": season,
        "week": week,
        "position": position,
        "week_is_active": week_is_active,
        "raw_games_value": games_value,
        "ppr_points": _parse_float(row, "fantasy_points_ppr", line_number),
        "targets": _parse_int(row, "targets", line_number),
        "receptions": _parse_int(row, "receptions", line_number),
        "receiving_yards": _parse_float(row, "receiving_yards", line_number),
        "receiving_tds": _parse_int(row, "receiving_tds", line_number),
        "snap_share": _parse_optional_share(row.get("snap_share"), "snap_share", line_number),
        "route_participation": _parse_optional_share(
            row.get("route_participation"),
            "route_participation",
            line_number,
        ),
        "target_share": _parse_optional_share(row.get("target_share"), "target_share", line_number),
        "air_yard_share": _parse_optional_share(
            row.get("air_yard_share"),
            "air_yard_share",
            line_number,
        ),
    }

    if normalized["receptions"] > normalized["targets"]:
        raise ValidationError(f"line {line_number}: receptions cannot exceed targets")
    return normalized


def _require_text(row: dict[str, str], field_name: str, line_number: int) -> str:
    value = (row.get(field_name) or "").strip()
    if not value:
        raise ValidationError(f"line {line_number}: missing required field {field_name}")
    return value


def _parse_int(row: dict[str, str], field_name: str, line_number: int) -> int:
    raw_value = (row.get(field_name) or "").strip()
    if raw_value == "":
        raise ValidationError(f"line {line_number}: missing required integer field {field_name}")
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValidationError(f"line {line_number}: invalid integer for {field_name}: {raw_value}") from exc
    if value < 0:
        raise ValidationError(f"line {line_number}: {field_name} cannot be negative")
    return value


def _parse_optional_int(
    raw_value: str | None,
    field_name: str,
    line_number: int,
) -> int | None:
    if raw_value is None or raw_value.strip() == "":
        return None
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValidationError(f"line {line_number}: invalid integer for {field_name}: {raw_value}") from exc
    if value < 0:
        raise ValidationError(f"line {line_number}: {field_name} cannot be negative")
    return value


def _parse_float(row: dict[str, str], field_name: str, line_number: int) -> float:
    raw_value = (row.get(field_name) or "").strip()
    if raw_value == "":
        raise ValidationError(f"line {line_number}: missing required numeric field {field_name}")
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ValidationError(f"line {line_number}: invalid float for {field_name}: {raw_value}") from exc
    return value


def _parse_optional_share(raw_value: str | None, field_name: str, line_number: int) -> float | None:
    if raw_value is None or raw_value.strip() == "":
        return None
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ValidationError(f"line {line_number}: invalid float for {field_name}: {raw_value}") from exc
    if not 0.0 <= value <= 1.0:
        raise ValidationError(f"line {line_number}: {field_name} must be between 0 and 1")
    return round(value, 4)


def _parse_optional_bool(raw_value: str | None, field_name: str, line_number: int) -> bool | None:
    if raw_value is None or raw_value.strip() == "":
        return None
    normalized = raw_value.strip().lower()
    truthy = {"1", "true", "t", "yes", "y"}
    falsy = {"0", "false", "f", "no", "n"}
    if normalized in truthy:
        return True
    if normalized in falsy:
        return False
    raise ValidationError(f"line {line_number}: invalid boolean for {field_name}: {raw_value}")


def _resolve_week_is_active(games_value: int | None, active_value: bool | None) -> bool:
    if active_value is not None:
        return active_value
    if games_value is not None:
        return games_value > 0
    return True


def _validate_season(value: int, field_name: str) -> None:
    if value < 1990 or value > 2100:
        raise ValidationError(f"{field_name} must be between 1990 and 2100")


def _validate_week(value: int, field_name: str) -> None:
    if value < 1 or value > 18:
        raise ValidationError(f"{field_name} must be between 1 and 18")


def _serialize_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, float):
        return _format_float(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def _format_float(value: float) -> str:
    text = f"{value:.4f}"
    text = text.rstrip("0").rstrip(".")
    return text if text else "0"
