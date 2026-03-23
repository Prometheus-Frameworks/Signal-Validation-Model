"""TIBER-Data ingestion adapter for normalized WR historical weekly data."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse
from urllib.error import URLError
from urllib.request import urlopen

from src.validation import ValidationError, read_raw_wr_week_rows
from src.validation.wr_tables import WR_RAW_OPTIONAL_COLUMNS, WR_RAW_REQUIRED_COLUMNS

PREFERRED_SORT_KEYS = ("season", "week", "player_name", "player_id")
DEFAULT_TIBER_EXPORT_ENV_VARS = (
    "TIBER_DATA_WR_EXPORT_PATH",
    "TIBER_DATA_WR_EXPORT_URL",
)
DEFAULT_TIBER_API_ENV_VARS = ("TIBER_DATA_WR_API_URL",)
TIBER_DATA_EXPORT_SOURCE_TYPE = "tiber-data-export"
TIBER_DATA_API_SOURCE_TYPE = "tiber-data-api"

_FIELD_ALIASES = {
    "player_id": ("player_id", "gsis_id", "nflverse_player_id"),
    "player_name": ("player_name", "player_display_name", "full_name", "name"),
    "team": ("team", "recent_team", "team_abbr"),
    "season": ("season",),
    "week": ("week",),
    "position": ("position",),
    "fantasy_points_ppr": ("fantasy_points_ppr", "ppr_points"),
    "targets": ("targets",),
    "receptions": ("receptions",),
    "receiving_yards": ("receiving_yards", "rec_yards"),
    "receiving_tds": ("receiving_tds", "rec_tds"),
    "games": ("games",),
    "active": ("active", "is_active"),
    "snap_share": ("snap_share",),
    "route_participation": ("route_participation",),
    "target_share": ("target_share",),
    "air_yard_share": ("air_yard_share",),
}

_REQUIRED_OUTPUT_COLUMNS = WR_RAW_REQUIRED_COLUMNS + [
    column for column in WR_RAW_OPTIONAL_COLUMNS if column != "active"
]


class TiberDataSourceUnavailable(RuntimeError):
    """Raised when TIBER-Data is not configured or reachable for this run."""


@dataclass(frozen=True)
class TiberDataIngestionResult:
    raw_csv_path: Path
    provenance_path: Path
    source_type: str
    source_location: str
    row_count: int
    seasons: tuple[int, ...]
    used_fallback: bool = False
    fallback_reason: str | None = None



def build_wr_history_from_tiber_data(
    *,
    output_path: str | Path,
    provenance_path: str | Path | None = None,
    export_path_or_url: str | None = None,
    api_url: str | None = None,
) -> TiberDataIngestionResult:
    """Fetch WR history from TIBER-Data, normalize it, and write the raw CSV contract."""

    output_path = Path(output_path)
    provenance_path = Path(provenance_path) if provenance_path is not None else output_path.with_suffix(
        ".provenance.json"
    )

    if export_path_or_url:
        source_rows = _load_export_rows(export_path_or_url)
        source_type = TIBER_DATA_EXPORT_SOURCE_TYPE
        source_location = export_path_or_url
    elif api_url:
        source_rows = _load_api_rows(api_url)
        source_type = TIBER_DATA_API_SOURCE_TYPE
        source_location = api_url
    else:
        raise TiberDataSourceUnavailable(
            "TIBER-Data ingestion requires either an export path/URL or an API URL."
        )

    normalized_rows = _normalize_rows(source_rows)
    _write_rows(output_path, normalized_rows)
    validated_rows = read_raw_wr_week_rows(output_path)
    seasons = tuple(sorted({int(row["season"]) for row in validated_rows}))

    provenance = {
        "source_type": source_type,
        "source_location": source_location,
        "row_count": len(validated_rows),
        "seasons": list(seasons),
        "column_order": _REQUIRED_OUTPUT_COLUMNS,
        "sorting": list(PREFERRED_SORT_KEYS),
        "duplicate_key": ["player_id", "season", "week"],
        "used_fallback": False,
        "fallback_reason": None,
    }
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return TiberDataIngestionResult(
        raw_csv_path=output_path,
        provenance_path=provenance_path,
        source_type=source_type,
        source_location=source_location,
        row_count=len(validated_rows),
        seasons=seasons,
    )



def _load_export_rows(path_or_url: str) -> list[dict[str, Any]]:
    if _is_url(path_or_url):
        payload = _read_url_text(path_or_url)
        return _parse_rows_from_payload(payload=payload, source_name=path_or_url)

    path = Path(path_or_url)
    if not path.exists():
        raise TiberDataSourceUnavailable(f"TIBER-Data export does not exist: {path}")
    return _parse_rows_from_payload(payload=path.read_text(encoding="utf-8"), source_name=str(path))



def _load_api_rows(api_url: str) -> list[dict[str, Any]]:
    payload = _read_url_text(api_url)
    parsed = json.loads(payload)
    if isinstance(parsed, list):
        rows = parsed
    elif isinstance(parsed, dict) and isinstance(parsed.get("data"), list):
        rows = parsed["data"]
    else:
        raise ValidationError("TIBER-Data API response must be a list or contain a top-level 'data' list")
    if not all(isinstance(row, dict) for row in rows):
        raise ValidationError("TIBER-Data API rows must be JSON objects")
    return [dict(row) for row in rows]



def _parse_rows_from_payload(*, payload: str, source_name: str) -> list[dict[str, Any]]:
    suffix = Path(urlparse(source_name).path).suffix.lower()
    if suffix == ".json":
        parsed = json.loads(payload)
        if not isinstance(parsed, list):
            raise ValidationError("TIBER-Data JSON export must contain a top-level list of rows")
        if not all(isinstance(row, dict) for row in parsed):
            raise ValidationError("TIBER-Data JSON export rows must be objects")
        return [dict(row) for row in parsed]

    reader = csv.DictReader(io.StringIO(payload))
    if reader.fieldnames is None:
        raise ValidationError(f"TIBER-Data export is missing a header row: {source_name}")
    return [dict(row) for row in reader]



def _normalize_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_rows = [_normalize_row(row) for row in rows]
    normalized_rows.sort(
        key=lambda row: (
            int(row["season"]),
            int(row["week"]),
            str(row["player_name"]),
            str(row["player_id"]),
        )
    )
    _validate_normalized_rows(normalized_rows)
    return normalized_rows



def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for target_column in WR_RAW_REQUIRED_COLUMNS + WR_RAW_OPTIONAL_COLUMNS:
        source_value = None
        for alias in _FIELD_ALIASES[target_column]:
            if alias in row:
                source_value = row[alias]
                break
        normalized[target_column] = source_value

    missing_required = [
        column
        for column in WR_RAW_REQUIRED_COLUMNS
        if _is_blank(normalized[column])
    ]
    if missing_required:
        raise ValidationError(f"TIBER-Data row is missing required values for columns: {missing_required}")

    normalized["player_id"] = str(normalized["player_id"]).strip()
    normalized["player_name"] = str(normalized["player_name"]).strip()
    normalized["team"] = str(normalized["team"] or "").strip()
    normalized["position"] = str(normalized["position"]).strip().upper()
    normalized["season"] = int(normalized["season"])
    normalized["week"] = int(normalized["week"])
    normalized["fantasy_points_ppr"] = round(float(normalized["fantasy_points_ppr"]), 4)
    normalized["targets"] = int(float(normalized["targets"]))
    normalized["receptions"] = int(float(normalized["receptions"]))
    normalized["receiving_yards"] = round(float(normalized["receiving_yards"]), 4)
    normalized["receiving_tds"] = int(float(normalized["receiving_tds"]))

    for optional_int_column in ("games",):
        if _is_blank(normalized[optional_int_column]):
            normalized[optional_int_column] = ""
        else:
            normalized[optional_int_column] = int(float(normalized[optional_int_column]))

    if _is_blank(normalized["active"]):
        normalized["active"] = ""
    else:
        normalized["active"] = _normalize_bool_text(normalized["active"])

    for optional_float_column in ("snap_share", "route_participation", "target_share", "air_yard_share"):
        if _is_blank(normalized[optional_float_column]):
            normalized[optional_float_column] = ""
        else:
            normalized[optional_float_column] = round(float(normalized[optional_float_column]), 4)

    return normalized



def _validate_normalized_rows(rows: list[dict[str, Any]]) -> None:
    seen_keys: set[tuple[str, int, int]] = set()
    for row in rows:
        if row["position"] != "WR":
            raise ValidationError("TIBER-Data normalization only supports WR rows")
        key = (str(row["player_id"]), int(row["season"]), int(row["week"]))
        if key in seen_keys:
            raise ValidationError(
                "duplicate WR weekly primary key encountered for "
                f"player_id={key[0]}, season={key[1]}, week={key[2]}"
            )
        seen_keys.add(key)

    sorted_rows = sorted(
        rows,
        key=lambda row: (
            int(row["season"]),
            int(row["week"]),
            str(row["player_name"]),
            str(row["player_id"]),
        ),
    )
    if rows != sorted_rows:
        raise ValidationError("TIBER-Data rows are not deterministically ordered")



def _write_rows(output_path: Path, rows: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_REQUIRED_OUTPUT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _serialize_csv_value(row.get(column)) for column in _REQUIRED_OUTPUT_COLUMNS})



def _serialize_csv_value(value: Any) -> str | int | float:
    if value is None or value == "":
        return ""
    return value



def _normalize_bool_text(value: Any) -> str:
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "t", "yes", "y"}:
        return "true"
    if lowered in {"0", "false", "f", "no", "n"}:
        return "false"
    raise ValidationError(f"unable to coerce active flag to boolean text: {value!r}")



def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""



def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"}



def _read_url_text(url: str) -> str:
    try:
        with urlopen(url) as response:  # noqa: S310 - controlled by explicit user/config input
            return response.read().decode("utf-8")
    except (OSError, URLError) as exc:
        raise TiberDataSourceUnavailable(f"unable to read TIBER-Data URL: {url}") from exc
