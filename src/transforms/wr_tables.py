"""Transforms for canonical WR historical research tables."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from src.validation.wr_tables import (
    WR_CANONICAL_COLUMN_ORDER,
    ValidationError,
    validate_canonical_tables,
)

SPIKE_WEEK_PPR_THRESHOLD = 20.0
DUD_WEEK_PPR_THRESHOLD = 5.0


@dataclass(frozen=True)
class WeeklyRow:
    player_id: str
    player_name: str
    team: str
    season: int
    week: int
    position: str
    week_is_active: bool
    raw_games_value: int | None
    ppr_points: float
    targets: int
    receptions: int
    receiving_yards: float
    receiving_tds: int
    snap_share: float | None
    route_participation: float | None
    target_share: float | None
    air_yard_share: float | None

    def as_dict(self) -> dict[str, object]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "team": self.team,
            "season": self.season,
            "week": self.week,
            "position": self.position,
            "week_is_active": self.week_is_active,
            "raw_games_value": self.raw_games_value,
            "ppr_points": round(self.ppr_points, 4),
            "targets": self.targets,
            "receptions": self.receptions,
            "receiving_yards": round(self.receiving_yards, 4),
            "receiving_tds": self.receiving_tds,
            "snap_share": _round_optional(self.snap_share),
            "route_participation": _round_optional(self.route_participation),
            "target_share": _round_optional(self.target_share),
            "air_yard_share": _round_optional(self.air_yard_share),
        }


@dataclass(frozen=True)
class SeasonAccumulator:
    player_id: str
    player_name: str
    team: str
    season: int
    position: str
    weeks_recorded: int = 0
    games_played: int = 0
    total_ppr: float = 0.0
    spike_week_count: int = 0
    dud_week_count: int = 0
    total_targets: int = 0
    total_receptions: int = 0
    total_receiving_yards: float = 0.0
    total_receiving_tds: int = 0
    sum_snap_share: float = 0.0
    snap_share_weeks: int = 0
    sum_route_participation: float = 0.0
    route_participation_weeks: int = 0
    sum_target_share: float = 0.0
    target_share_weeks: int = 0
    sum_air_yard_share: float = 0.0
    air_yard_share_weeks: int = 0

    def add_week(self, week: WeeklyRow) -> "SeasonAccumulator":
        games_played = self.games_played + (1 if week.week_is_active else 0)
        spike_week_count = self.spike_week_count + (
            1 if week.week_is_active and week.ppr_points >= SPIKE_WEEK_PPR_THRESHOLD else 0
        )
        dud_week_count = self.dud_week_count + (
            1 if week.week_is_active and week.ppr_points < DUD_WEEK_PPR_THRESHOLD else 0
        )

        sum_snap_share, snap_share_weeks = _accumulate_optional(
            self.sum_snap_share,
            self.snap_share_weeks,
            week.snap_share,
        )
        sum_route_participation, route_participation_weeks = _accumulate_optional(
            self.sum_route_participation,
            self.route_participation_weeks,
            week.route_participation,
        )
        sum_target_share, target_share_weeks = _accumulate_optional(
            self.sum_target_share,
            self.target_share_weeks,
            week.target_share,
        )
        sum_air_yard_share, air_yard_share_weeks = _accumulate_optional(
            self.sum_air_yard_share,
            self.air_yard_share_weeks,
            week.air_yard_share,
        )

        return SeasonAccumulator(
            player_id=self.player_id,
            player_name=self.player_name,
            team=self.team,
            season=self.season,
            position=self.position,
            weeks_recorded=self.weeks_recorded + 1,
            games_played=games_played,
            total_ppr=self.total_ppr + week.ppr_points,
            spike_week_count=spike_week_count,
            dud_week_count=dud_week_count,
            total_targets=self.total_targets + week.targets,
            total_receptions=self.total_receptions + week.receptions,
            total_receiving_yards=self.total_receiving_yards + week.receiving_yards,
            total_receiving_tds=self.total_receiving_tds + week.receiving_tds,
            sum_snap_share=sum_snap_share,
            snap_share_weeks=snap_share_weeks,
            sum_route_participation=sum_route_participation,
            route_participation_weeks=route_participation_weeks,
            sum_target_share=sum_target_share,
            target_share_weeks=target_share_weeks,
            sum_air_yard_share=sum_air_yard_share,
            air_yard_share_weeks=air_yard_share_weeks,
        )

    def as_player_season_row(self) -> dict[str, object]:
        games_played = self.games_played
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "team": self.team,
            "season": self.season,
            "position": self.position,
            "weeks_recorded": self.weeks_recorded,
            "games_played": games_played,
            "total_ppr": round(self.total_ppr, 4),
            "ppg": _safe_rate(self.total_ppr, games_played),
            "spike_week_threshold": SPIKE_WEEK_PPR_THRESHOLD,
            "spike_week_count": self.spike_week_count,
            "spike_week_rate": _safe_rate(self.spike_week_count, games_played),
            "dud_week_threshold": DUD_WEEK_PPR_THRESHOLD,
            "dud_week_count": self.dud_week_count,
            "dud_week_rate": _safe_rate(self.dud_week_count, games_played),
            "total_targets": self.total_targets,
            "targets_per_game": _safe_rate(self.total_targets, games_played),
            "total_receptions": self.total_receptions,
            "receptions_per_game": _safe_rate(self.total_receptions, games_played),
            "total_receiving_yards": round(self.total_receiving_yards, 4),
            "receiving_yards_per_game": _safe_rate(self.total_receiving_yards, games_played),
            "total_receiving_tds": self.total_receiving_tds,
            "receiving_tds_per_game": _safe_rate(self.total_receiving_tds, games_played),
            "avg_snap_share": _safe_optional_average(self.sum_snap_share, self.snap_share_weeks),
            "avg_route_participation": _safe_optional_average(
                self.sum_route_participation,
                self.route_participation_weeks,
            ),
            "avg_target_share": _safe_optional_average(self.sum_target_share, self.target_share_weeks),
            "avg_air_yard_share": _safe_optional_average(
                self.sum_air_yard_share,
                self.air_yard_share_weeks,
            ),
        }


def build_canonical_wr_tables(
    raw_rows: Iterable[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    """Transform validated raw rows into canonical weekly, season, feature, and outcome tables."""

    weekly_rows = [_normalize_weekly_row(row).as_dict() for row in raw_rows]
    weekly_rows.sort(key=lambda row: (row["player_id"], row["season"], row["week"]))

    accumulators: dict[tuple[str, int], SeasonAccumulator] = {}
    names_by_player: dict[str, str] = {}

    for row in weekly_rows:
        key = (str(row["player_id"]), int(row["season"]))
        if key not in accumulators:
            accumulators[key] = SeasonAccumulator(
                player_id=str(row["player_id"]),
                player_name=str(row["player_name"]),
                team=str(row["team"]),
                season=int(row["season"]),
                position=str(row["position"]),
            )
        names_by_player[str(row["player_id"])] = str(row["player_name"])
        accumulators[key] = accumulators[key].add_week(_weekly_row_from_dict(row))

    player_seasons = [
        accumulator.as_player_season_row()
        for _, accumulator in sorted(accumulators.items())
    ]

    feature_seasons = [_build_feature_row(row) for row in player_seasons]
    feature_seasons.sort(key=lambda row: (row["player_id"], row["season"]))

    outcome_seasons = _build_outcome_rows(player_seasons, names_by_player)

    tables = {
        "wr_player_weeks": _order_rows(weekly_rows, WR_CANONICAL_COLUMN_ORDER["wr_player_weeks"]),
        "wr_player_seasons": _order_rows(
            player_seasons, WR_CANONICAL_COLUMN_ORDER["wr_player_seasons"]
        ),
        "wr_feature_seasons": _order_rows(
            feature_seasons, WR_CANONICAL_COLUMN_ORDER["wr_feature_seasons"]
        ),
        "wr_outcome_seasons": _order_rows(
            outcome_seasons, WR_CANONICAL_COLUMN_ORDER["wr_outcome_seasons"]
        ),
    }
    validate_canonical_tables(tables)
    return tables


def _normalize_weekly_row(raw_row: dict[str, object]) -> WeeklyRow:
    return WeeklyRow(
        player_id=str(raw_row["player_id"]),
        player_name=str(raw_row["player_name"]),
        team=str(raw_row["team"]),
        season=int(raw_row["season"]),
        week=int(raw_row["week"]),
        position="WR",
        week_is_active=bool(raw_row["week_is_active"]),
        raw_games_value=(None if raw_row["raw_games_value"] is None else int(raw_row["raw_games_value"])),
        ppr_points=float(raw_row["ppr_points"]),
        targets=int(raw_row["targets"]),
        receptions=int(raw_row["receptions"]),
        receiving_yards=float(raw_row["receiving_yards"]),
        receiving_tds=int(raw_row["receiving_tds"]),
        snap_share=_optional_float(raw_row.get("snap_share")),
        route_participation=_optional_float(raw_row.get("route_participation")),
        target_share=_optional_float(raw_row.get("target_share")),
        air_yard_share=_optional_float(raw_row.get("air_yard_share")),
    )


def _weekly_row_from_dict(row: dict[str, object]) -> WeeklyRow:
    return WeeklyRow(
        player_id=str(row["player_id"]),
        player_name=str(row["player_name"]),
        team=str(row["team"]),
        season=int(row["season"]),
        week=int(row["week"]),
        position=str(row["position"]),
        week_is_active=bool(row["week_is_active"]),
        raw_games_value=(None if row["raw_games_value"] is None else int(row["raw_games_value"])),
        ppr_points=float(row["ppr_points"]),
        targets=int(row["targets"]),
        receptions=int(row["receptions"]),
        receiving_yards=float(row["receiving_yards"]),
        receiving_tds=int(row["receiving_tds"]),
        snap_share=_optional_float(row.get("snap_share")),
        route_participation=_optional_float(row.get("route_participation")),
        target_share=_optional_float(row.get("target_share")),
        air_yard_share=_optional_float(row.get("air_yard_share")),
    )


def _build_feature_row(player_season_row: dict[str, object]) -> dict[str, object]:
    return {
        "player_id": player_season_row["player_id"],
        "player_name": player_season_row["player_name"],
        "season": player_season_row["season"],
        "target_outcome_season": int(player_season_row["season"]) + 1,
        "data_through_season": player_season_row["season"],
        "position": player_season_row["position"],
        "team": player_season_row["team"],
        "games_played": player_season_row["games_played"],
        "weeks_recorded": player_season_row["weeks_recorded"],
        "total_ppr": player_season_row["total_ppr"],
        "ppg": player_season_row["ppg"],
        "spike_week_rate": player_season_row["spike_week_rate"],
        "dud_week_rate": player_season_row["dud_week_rate"],
        "total_targets": player_season_row["total_targets"],
        "targets_per_game": player_season_row["targets_per_game"],
        "total_receptions": player_season_row["total_receptions"],
        "receptions_per_game": player_season_row["receptions_per_game"],
        "total_receiving_yards": player_season_row["total_receiving_yards"],
        "receiving_yards_per_game": player_season_row["receiving_yards_per_game"],
        "total_receiving_tds": player_season_row["total_receiving_tds"],
        "receiving_tds_per_game": player_season_row["receiving_tds_per_game"],
        "avg_snap_share": player_season_row["avg_snap_share"],
        "avg_route_participation": player_season_row["avg_route_participation"],
        "avg_target_share": player_season_row["avg_target_share"],
        "avg_air_yard_share": player_season_row["avg_air_yard_share"],
    }


def _build_outcome_rows(
    player_seasons: list[dict[str, object]],
    names_by_player: dict[str, str],
) -> list[dict[str, object]]:
    seasons_by_player: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in player_seasons:
        seasons_by_player[str(row["player_id"])].append(row)

    outcome_rows: list[dict[str, object]] = []
    for player_id, seasons in seasons_by_player.items():
        ordered = sorted(seasons, key=lambda row: int(row["season"]))
        for row in ordered:
            outcome_rows.append(
                {
                    "player_id": player_id,
                    "player_name": names_by_player[player_id],
                    "feature_season": int(row["season"]) - 1,
                    "outcome_season": row["season"],
                    "position": row["position"],
                    "team": row["team"],
                    "outcome_games_played": row["games_played"],
                    "outcome_total_ppr": row["total_ppr"],
                    "outcome_ppg": row["ppg"],
                    "outcome_spike_week_rate": row["spike_week_rate"],
                    "outcome_dud_week_rate": row["dud_week_rate"],
                    "outcome_total_targets": row["total_targets"],
                    "outcome_targets_per_game": row["targets_per_game"],
                    "outcome_total_receptions": row["total_receptions"],
                    "outcome_receptions_per_game": row["receptions_per_game"],
                    "outcome_total_receiving_yards": row["total_receiving_yards"],
                    "outcome_receiving_yards_per_game": row["receiving_yards_per_game"],
                    "outcome_total_receiving_tds": row["total_receiving_tds"],
                    "outcome_receiving_tds_per_game": row["receiving_tds_per_game"],
                }
            )
    outcome_rows.sort(
        key=lambda row: (row["player_id"], row["feature_season"], row["outcome_season"])
    )
    return outcome_rows


def _order_rows(rows: list[dict[str, object]], columns: list[str]) -> list[dict[str, object]]:
    ordered: list[dict[str, object]] = []
    for row in rows:
        missing = [column for column in columns if column not in row]
        if missing:
            raise ValidationError(f"row is missing canonical columns: {missing}")
        ordered.append({column: row[column] for column in columns})
    return ordered


def _safe_rate(numerator: float | int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _safe_optional_average(total: float, count: int) -> float | None:
    if count <= 0:
        return None
    return round(total / count, 4)


def _accumulate_optional(total: float, count: int, value: float | None) -> tuple[float, int]:
    if value is None:
        return total, count
    return total + value, count + 1


def _round_optional(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
