"""Pinned TIBER-Data player-season coverage ingestion for bounded WR research."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from src.validation import ValidationError

TIBER_DATA_REPOSITORY = "https://github.com/Prometheus-Frameworks/TIBER-Data"
PINNED_TIBER_DATA_COMMIT_SHA = "3606b6a0af5add2ebea1f7de141a299cebe70a34"
PINNED_ARTIFACT_LAST_CHANGED_COMMIT_SHA = (
    "711d6ee158d4e3bd116d1df4d76dea282200454d"
)
PINNED_PLAYER_SEASON_COVERAGE_PATH = "exports/promoted/nfl/player_season_coverage_v0.json"
PINNED_PLAYER_SEASON_COVERAGE_BLOB_SHA = "f7b2918b978d842cd8753a7f3dedd3836934859b"
PINNED_PLAYER_SEASON_COVERAGE_SHA256 = (
    "d45f612b207085df00b4b080e4f55ce1abbd060dcbf30b0bee777ff833ddd8ac"
)

EXPECTED_ARTIFACT_ID = "player_season_coverage_v0"
EXPECTED_SPEC_VERSION = "player_season_coverage_v0_promoted_v1"
EXPECTED_STATUS = "promoted_governed_artifact"
EXPECTED_PROMOTION_REVIEW = "TIBER-Data#202"
EXPECTED_PROMOTION_DECISION = "promote_player_season_coverage_v0_2021_2025"
EXPECTED_ROW_GRAIN = "player_id + season + season_type"
EXPECTED_SEASON_TYPE = "REG"
EXPECTED_SEASONS = (2021, 2022, 2023, 2024, 2025)
SUPPORTED_POSITIONS = frozenset({"QB", "RB", "TE", "WR"})
SOURCE_VERIFIED_IDENTITY = "source_verified"


@dataclass(frozen=True)
class PlayerSeasonRecord:
    """Normalized source-backed player-season evidence from the promoted artifact."""

    player_id: str
    player_name: str
    position: str
    espn_id: str | None
    sleeper_id: str | None
    identity_confidence: str
    teams: tuple[str, ...]
    primary_team: str
    season: int
    season_type: str
    rookie_year: int
    career_year: int
    games_played: int
    season_ppr: float
    season_ppg: float
    targets: int
    receptions: int
    receiving_yards: float
    receiving_tds: int
    target_share: float
    air_yards_share: float
    wopr: float
    routes_run: int | None
    route_participation: float | None
    snap_share: float | None
    missing_fields: tuple[str, ...]


@dataclass(frozen=True)
class PlayerSeasonCoverageReceipt:
    """Immutable provenance binding for the accepted promoted input bytes."""

    source_repository: str
    source_commit_sha: str
    artifact_last_changed_commit_sha: str
    source_path: str
    source_blob_sha: str
    content_sha256: str
    artifact_id: str
    spec_version: str
    status: str
    generated_at: str
    promoted_at: str
    promotion_review: str
    promotion_decision: str
    row_grain: str
    seasons: tuple[int, ...]
    season_type_scope: tuple[str, ...]
    included_positions: tuple[str, ...]
    total_record_count: int
    counts_by_season: tuple[tuple[int, int], ...]
    counts_by_position: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class PlayerSeasonCoverageArtifact:
    """Validated player-season rows plus the exact upstream provenance receipt."""

    records: tuple[PlayerSeasonRecord, ...]
    receipt: PlayerSeasonCoverageReceipt

    def records_for_position(self, position: str) -> tuple[PlayerSeasonRecord, ...]:
        normalized_position = position.strip().upper()
        return tuple(record for record in self.records if record.position == normalized_position)


def load_player_season_coverage(
    input_path: str | Path,
) -> PlayerSeasonCoverageArtifact:
    """Read the promoted artifact after verifying its exact byte digest.

    The digest is checked before UTF-8 decoding or JSON parsing. This public
    production boundary accepts only the issue-16 TIBER-Data bytes whose commit,
    blob, path, and content digest are recorded in the returned receipt.
    """

    return _load_player_season_coverage_with_expected_digest(
        input_path,
        expected_sha256=PINNED_PLAYER_SEASON_COVERAGE_SHA256,
    )


def _load_player_season_coverage_with_expected_digest(
    input_path: str | Path,
    *,
    expected_sha256: str,
) -> PlayerSeasonCoverageArtifact:
    """Private parser seam for offline contract tests with synthetic bytes."""

    path = Path(input_path)
    if not path.exists():
        raise ValidationError(f"player-season coverage input does not exist: {path}")
    if not path.is_file():
        raise ValidationError(f"player-season coverage input is not a file: {path}")

    raw_bytes = path.read_bytes()
    actual_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValidationError(
            "player-season coverage digest mismatch: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )

    try:
        payload = json.loads(
            raw_bytes.decode("utf-8"),
            parse_constant=_reject_non_finite_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValidationError("player-season coverage input is not valid finite-value JSON") from exc

    root = _require_mapping(payload, "artifact")
    metadata = _validate_metadata(root)
    raw_records = _require_list(root.get("records"), "artifact.records")
    records = tuple(_normalize_record(row, index=index) for index, row in enumerate(raw_records))
    _validate_records(records, metadata)

    ordered_records = tuple(
        sorted(
            records,
            key=lambda record: (
                record.season,
                record.position,
                record.player_id,
                record.season_type,
            ),
        )
    )
    receipt = PlayerSeasonCoverageReceipt(
        source_repository=TIBER_DATA_REPOSITORY,
        source_commit_sha=PINNED_TIBER_DATA_COMMIT_SHA,
        artifact_last_changed_commit_sha=PINNED_ARTIFACT_LAST_CHANGED_COMMIT_SHA,
        source_path=PINNED_PLAYER_SEASON_COVERAGE_PATH,
        source_blob_sha=PINNED_PLAYER_SEASON_COVERAGE_BLOB_SHA,
        content_sha256=actual_sha256,
        artifact_id=metadata["artifact_id"],
        spec_version=metadata["spec_version"],
        status=metadata["status"],
        generated_at=metadata["generated_at"],
        promoted_at=metadata["promoted_at"],
        promotion_review=metadata["promotion_review"],
        promotion_decision=metadata["promotion_decision"],
        row_grain=metadata["row_grain"],
        seasons=metadata["seasons"],
        season_type_scope=metadata["season_type_scope"],
        included_positions=metadata["included_positions"],
        total_record_count=metadata["total_record_count"],
        counts_by_season=metadata["counts_by_season"],
        counts_by_position=metadata["counts_by_position"],
    )
    return PlayerSeasonCoverageArtifact(records=ordered_records, receipt=receipt)


def _validate_metadata(root: Mapping[str, Any]) -> dict[str, Any]:
    artifact_id = _require_exact_text(root, "artifact_id", EXPECTED_ARTIFACT_ID, "artifact")
    spec_version = _require_exact_text(
        root,
        "spec_version",
        EXPECTED_SPEC_VERSION,
        "artifact",
    )
    status = _require_exact_text(root, "status", EXPECTED_STATUS, "artifact")
    row_grain = _require_exact_text(root, "row_grain", EXPECTED_ROW_GRAIN, "artifact")
    generated_at = _require_text(root.get("generated_at"), "artifact.generated_at")
    promoted_at = _require_text(root.get("promoted_at"), "artifact.promoted_at")
    promotion_review = _require_exact_text(
        root,
        "promotion_review",
        EXPECTED_PROMOTION_REVIEW,
        "artifact",
    )
    promotion_decision = _require_exact_text(
        root,
        "promotion_decision",
        EXPECTED_PROMOTION_DECISION,
        "artifact",
    )

    if root.get("no_fixture_or_scaffold_markers_confirmed") is not True:
        raise ValidationError(
            "artifact.no_fixture_or_scaffold_markers_confirmed must be true"
        )

    seasons = tuple(_require_int(value, "artifact.seasons[]", minimum=1990) for value in _require_list(root.get("seasons"), "artifact.seasons"))
    if seasons != EXPECTED_SEASONS:
        raise ValidationError(f"artifact.seasons must equal {list(EXPECTED_SEASONS)!r}")

    season_type_scope = tuple(
        _require_text(value, "artifact.season_type_scope[]")
        for value in _require_list(root.get("season_type_scope"), "artifact.season_type_scope")
    )
    if season_type_scope != (EXPECTED_SEASON_TYPE,):
        raise ValidationError(
            f"artifact.season_type_scope must equal [{EXPECTED_SEASON_TYPE!r}]"
        )

    included_positions = tuple(
        _require_text(value, "artifact.included_positions[]").upper()
        for value in _require_list(root.get("included_positions"), "artifact.included_positions")
    )
    if not included_positions or len(set(included_positions)) != len(included_positions):
        raise ValidationError("artifact.included_positions must be non-empty and unique")
    unsupported_positions = sorted(set(included_positions) - SUPPORTED_POSITIONS)
    if unsupported_positions:
        raise ValidationError(
            f"artifact.included_positions contains unsupported positions: {unsupported_positions}"
        )

    counts = _require_mapping(root.get("counts"), "artifact.counts")
    total_record_count = _require_int(
        counts.get("records"),
        "artifact.counts.records",
        minimum=0,
    )
    counts_by_season = _normalize_count_map(
        counts.get("by_season"),
        "artifact.counts.by_season",
        key_parser=_parse_season_count_key,
    )
    counts_by_position = _normalize_count_map(
        counts.get("by_position"),
        "artifact.counts.by_position",
        key_parser=_parse_position_count_key,
    )

    return {
        "artifact_id": artifact_id,
        "spec_version": spec_version,
        "status": status,
        "generated_at": generated_at,
        "promoted_at": promoted_at,
        "promotion_review": promotion_review,
        "promotion_decision": promotion_decision,
        "row_grain": row_grain,
        "seasons": seasons,
        "season_type_scope": season_type_scope,
        "included_positions": included_positions,
        "total_record_count": total_record_count,
        "counts_by_season": counts_by_season,
        "counts_by_position": counts_by_position,
    }


def _normalize_record(value: Any, *, index: int) -> PlayerSeasonRecord:
    label = f"artifact.records[{index}]"
    row = _require_mapping(value, label)
    player_id = _require_text(row.get("player_id"), f"{label}.player_id")
    player_name = _require_text(row.get("player_name"), f"{label}.player_name")
    position = _require_text(row.get("position"), f"{label}.position").upper()
    if position not in SUPPORTED_POSITIONS:
        raise ValidationError(f"{label}.position is unsupported: {position}")

    identity_confidence = _require_text(
        row.get("identity_confidence"),
        f"{label}.identity_confidence",
    )
    if identity_confidence != SOURCE_VERIFIED_IDENTITY:
        raise ValidationError(
            f"{label}.identity_confidence must equal {SOURCE_VERIFIED_IDENTITY!r}"
        )

    raw_provider_ids = row.get("provider_ids")
    provider_ids = (
        {}
        if raw_provider_ids is None
        else _require_mapping(raw_provider_ids, f"{label}.provider_ids")
    )
    espn_id = _optional_text(provider_ids.get("espn_id"), f"{label}.provider_ids.espn_id")
    sleeper_id = _optional_text(
        provider_ids.get("sleeper_id"),
        f"{label}.provider_ids.sleeper_id",
    )

    teams = tuple(
        _require_text(team, f"{label}.teams[]")
        for team in _require_list(row.get("teams"), f"{label}.teams")
    )
    if not teams or len(set(teams)) != len(teams):
        raise ValidationError(f"{label}.teams must be non-empty and unique")
    primary_team = _require_text(row.get("primary_team"), f"{label}.primary_team")
    if primary_team not in teams:
        raise ValidationError(f"{label}.primary_team must appear in teams")

    season = _require_int(row.get("season"), f"{label}.season", minimum=1990)
    season_type = _require_text(row.get("season_type"), f"{label}.season_type")
    if season_type != EXPECTED_SEASON_TYPE:
        raise ValidationError(f"{label}.season_type must equal {EXPECTED_SEASON_TYPE!r}")
    rookie_year = _require_int(row.get("rookie_year"), f"{label}.rookie_year", minimum=1900)
    career_year = _require_int(row.get("career_year"), f"{label}.career_year", minimum=1)
    expected_career_year = season - rookie_year + 1
    if career_year != expected_career_year:
        raise ValidationError(
            f"{label}.career_year must equal season - rookie_year + 1 "
            f"({expected_career_year}), got {career_year}"
        )
    games_played = _require_int(row.get("games_played"), f"{label}.games_played", minimum=0)

    production = _require_mapping(row.get("production_summary"), f"{label}.production_summary")
    season_ppr = _require_number(
        production.get("season_ppr"),
        f"{label}.production_summary.season_ppr",
    )
    games_for_ppg = _require_int(
        production.get("games_for_ppg"),
        f"{label}.production_summary.games_for_ppg",
        minimum=0,
    )
    if games_for_ppg != games_played:
        raise ValidationError(
            f"{label}.production_summary.games_for_ppg must equal games_played"
        )
    season_ppg = _require_number(
        production.get("season_ppg"),
        f"{label}.production_summary.season_ppg",
    )
    receiving = _require_mapping(
        production.get("receiving"),
        f"{label}.production_summary.receiving",
    )
    receiving_yards = _require_number(
        receiving.get("receiving_yards"),
        f"{label}.production_summary.receiving.receiving_yards",
    )
    receiving_tds = _require_int(
        receiving.get("receiving_tds"),
        f"{label}.production_summary.receiving.receiving_tds",
        minimum=0,
    )

    usage = _require_mapping(row.get("usage_summary"), f"{label}.usage_summary")
    targets = _require_int(usage.get("targets"), f"{label}.usage_summary.targets", minimum=0)
    receptions = _require_int(
        usage.get("receptions"),
        f"{label}.usage_summary.receptions",
        minimum=0,
    )
    if receptions > targets:
        raise ValidationError(f"{label}.usage_summary.receptions cannot exceed targets")
    target_share = _require_share(
        usage.get("target_share"),
        f"{label}.usage_summary.target_share",
    )
    # Receiving air-yard share can be slightly negative when a player records
    # negative receiving air yards.  It is retained as context only and is not
    # a bounded probability/share input to the v0 definition.
    air_yards_share = _require_number(
        usage.get("air_yards_share"),
        f"{label}.usage_summary.air_yards_share",
    )
    wopr = _require_number(usage.get("wopr"), f"{label}.usage_summary.wopr")
    if wopr < 0.0:
        raise ValidationError(f"{label}.usage_summary.wopr cannot be negative")
    routes_run = _optional_int(
        usage.get("routes_run"),
        f"{label}.usage_summary.routes_run",
        minimum=0,
    )
    route_participation = _optional_share(
        usage.get("route_participation"),
        f"{label}.usage_summary.route_participation",
    )
    snap_share = _optional_share(
        usage.get("snap_share"),
        f"{label}.usage_summary.snap_share",
    )

    missing_fields = tuple(
        _require_text(field, f"{label}.missing_fields[]")
        for field in _require_list(row.get("missing_fields"), f"{label}.missing_fields")
    )
    if len(set(missing_fields)) != len(missing_fields):
        raise ValidationError(f"{label}.missing_fields must not contain duplicates")
    for field_name, field_value in (
        ("routes_run", routes_run),
        ("route_participation", route_participation),
        ("snap_share", snap_share),
    ):
        if field_value is None and field_name not in missing_fields:
            raise ValidationError(
                f"{label}.{field_name} is null but missing_fields does not declare it"
            )
        if field_value is not None and field_name in missing_fields:
            raise ValidationError(
                f"{label}.{field_name} is present but missing_fields declares it missing"
            )

    return PlayerSeasonRecord(
        player_id=player_id,
        player_name=player_name,
        position=position,
        espn_id=espn_id,
        sleeper_id=sleeper_id,
        identity_confidence=identity_confidence,
        teams=teams,
        primary_team=primary_team,
        season=season,
        season_type=season_type,
        rookie_year=rookie_year,
        career_year=career_year,
        games_played=games_played,
        season_ppr=season_ppr,
        season_ppg=season_ppg,
        targets=targets,
        receptions=receptions,
        receiving_yards=receiving_yards,
        receiving_tds=receiving_tds,
        target_share=target_share,
        air_yards_share=air_yards_share,
        wopr=wopr,
        routes_run=routes_run,
        route_participation=route_participation,
        snap_share=snap_share,
        missing_fields=missing_fields,
    )


def _validate_records(
    records: tuple[PlayerSeasonRecord, ...],
    metadata: Mapping[str, Any],
) -> None:
    if len(records) != metadata["total_record_count"]:
        raise ValidationError(
            "artifact.counts.records does not match the number of records: "
            f"declared {metadata['total_record_count']}, observed {len(records)}"
        )

    seen_keys: set[tuple[str, int, str]] = set()
    identity_by_player_id: dict[str, tuple[str, str, int]] = {}
    for record in records:
        key = (record.player_id, record.season, record.season_type)
        if key in seen_keys:
            raise ValidationError(f"duplicate player-season coverage key: {key}")
        seen_keys.add(key)
        identity = (record.player_name, record.position, record.rookie_year)
        prior_identity = identity_by_player_id.setdefault(record.player_id, identity)
        if prior_identity != identity:
            raise ValidationError(
                "conflicting identity fields for player_id "
                f"{record.player_id!r}: {prior_identity!r} versus {identity!r}"
            )

    actual_by_season = tuple(sorted(Counter(record.season for record in records).items()))
    actual_by_position = tuple(sorted(Counter(record.position for record in records).items()))
    if actual_by_season != metadata["counts_by_season"]:
        raise ValidationError(
            "artifact.counts.by_season does not match records: "
            f"declared {metadata['counts_by_season']}, observed {actual_by_season}"
        )
    if actual_by_position != metadata["counts_by_position"]:
        raise ValidationError(
            "artifact.counts.by_position does not match records: "
            f"declared {metadata['counts_by_position']}, observed {actual_by_position}"
        )

    actual_seasons = tuple(season for season, _ in actual_by_season)
    actual_positions = tuple(position for position, _ in actual_by_position)
    if actual_seasons != metadata["seasons"]:
        raise ValidationError(
            f"artifact.seasons does not match record coverage: {actual_seasons}"
        )
    if set(actual_positions) != set(metadata["included_positions"]):
        raise ValidationError(
            f"artifact.included_positions does not match records: {actual_positions}"
        )


def _normalize_count_map(
    value: Any,
    label: str,
    *,
    key_parser: Any,
) -> tuple[tuple[Any, int], ...]:
    mapping = _require_mapping(value, label)
    normalized: list[tuple[Any, int]] = []
    seen_keys: set[Any] = set()
    for raw_key, raw_count in mapping.items():
        parsed_key = key_parser(raw_key, label)
        if parsed_key in seen_keys:
            raise ValidationError(f"{label} contains duplicate normalized key {parsed_key!r}")
        seen_keys.add(parsed_key)
        normalized.append(
            (parsed_key, _require_int(raw_count, f"{label}.{raw_key}", minimum=0))
        )
    return tuple(sorted(normalized))


def _parse_season_count_key(value: Any, label: str) -> int:
    try:
        season = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} contains invalid season key {value!r}") from exc
    if str(season) != str(value) or season < 1990:
        raise ValidationError(f"{label} contains invalid season key {value!r}")
    return season


def _parse_position_count_key(value: Any, label: str) -> str:
    position = _require_text(value, f"{label} key").upper()
    if position not in SUPPORTED_POSITIONS:
        raise ValidationError(f"{label} contains unsupported position key {position!r}")
    return position


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be a list")
    return value


def _require_exact_text(
    mapping: Mapping[str, Any],
    field_name: str,
    expected: str,
    parent_label: str,
) -> str:
    value = _require_text(mapping.get(field_name), f"{parent_label}.{field_name}")
    if value != expected:
        raise ValidationError(
            f"{parent_label}.{field_name} must equal {expected!r}, got {value!r}"
        )
    return value


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, label)


def _require_int(value: Any, label: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise ValidationError(f"{label} must be at least {minimum}")
    return value


def _optional_int(
    value: Any,
    label: str,
    *,
    minimum: int | None = None,
) -> int | None:
    if value is None:
        return None
    return _require_int(value, label, minimum=minimum)


def _require_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{label} must be numeric")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValidationError(f"{label} must be finite")
    return normalized


def _require_share(value: Any, label: str) -> float:
    share = _require_number(value, label)
    if not 0.0 <= share <= 1.0:
        raise ValidationError(f"{label} must be between 0 and 1")
    return share


def _optional_share(value: Any, label: str) -> float | None:
    if value is None:
        return None
    return _require_share(value, label)


def _reject_non_finite_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is not allowed: {value}")
