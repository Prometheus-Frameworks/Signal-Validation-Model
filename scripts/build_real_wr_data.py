#!/usr/bin/env python3
"""Build a real historical WR weekly CSV from nfl_data_py weekly data."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

SEASONS = [2020, 2021, 2022, 2023, 2024]
OUTPUT_PATH = Path("data/raw/player_weekly_history.csv")
REQUIRED_COLUMNS = [
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
OPTIONAL_COLUMNS = [
    "games",
    "snap_share",
    "route_participation",
    "target_share",
    "air_yard_share",
]
OUTPUT_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

SOURCE_COLUMN_MAP = {
    "player_id": "player_id",
    "player_name": "player_name",
    "recent_team": "team",
    "season": "season",
    "week": "week",
    "position": "position",
    "fantasy_points_ppr": "fantasy_points_ppr",
    "targets": "targets",
    "receptions": "receptions",
    "receiving_yards": "receiving_yards",
    "receiving_tds": "receiving_tds",
}
OPTIONAL_SOURCE_COLUMNS = {
    "games": "games",
    "snap_share": "snap_share",
    "route_participation": "route_participation",
    "target_share": "target_share",
    "air_yard_share": "air_yard_share",
}


def build_real_wr_history(output_path: Path = OUTPUT_PATH) -> Path:
    pandas, nfl = _import_dependencies()

    source_columns = list(SOURCE_COLUMN_MAP) + ["season_type"]
    weekly = nfl.import_weekly_data(SEASONS, columns=source_columns, downcast=False)
    wr_history = _transform_weekly_data(weekly, pandas)
    _validate_output_frame(wr_history)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wr_history.to_csv(output_path, index=False)
    _print_summary(wr_history, output_path)
    return output_path


def _import_dependencies() -> tuple[Any, Any]:
    try:
        import pandas  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise SystemExit(
            "pandas is required to build real WR history. Install project dependencies first."
        ) from exc

    try:
        import nfl_data_py as nfl  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise SystemExit(
            "nfl_data_py is required to build real WR history. Install project dependencies first."
        ) from exc

    return pandas, nfl


def _transform_weekly_data(weekly: Any, pandas: Any) -> Any:
    frame = weekly.copy()
    if "season_type" in frame.columns:
        frame = frame.loc[frame["season_type"].fillna("REG") == "REG"].copy()

    frame = frame.rename(columns=SOURCE_COLUMN_MAP)
    frame = frame.loc[frame["position"].fillna("").astype(str).str.upper() == "WR"].copy()
    frame["position"] = "WR"
    frame = frame.loc[frame["season"].isin(SEASONS)].copy()

    for output_column, source_column in OPTIONAL_SOURCE_COLUMNS.items():
        if source_column in weekly.columns:
            frame[output_column] = weekly[source_column]
        else:
            frame[output_column] = pandas.NA

    frame = frame[OUTPUT_COLUMNS].copy()
    frame["team"] = frame["team"].fillna("").astype(str).str.strip()

    frame["season"] = frame["season"].astype(int)
    frame["week"] = frame["week"].astype(int)
    for column in ["targets", "receptions", "receiving_tds"]:
        frame[column] = frame[column].fillna(0).astype(int)
    for column in ["fantasy_points_ppr", "receiving_yards"]:
        frame[column] = frame[column].fillna(0.0).astype(float)

    frame = frame.sort_values(
        by=["season", "week", "player_name", "player_id"],
        kind="mergesort",
    ).reset_index(drop=True)
    return frame


def _validate_output_frame(frame: Any) -> None:
    if list(frame.columns) != OUTPUT_COLUMNS:
        raise ValueError(f"unexpected output columns: {list(frame.columns)}")
    if frame.empty:
        raise ValueError("weekly WR output is empty")
    if set(frame["position"].dropna().unique()) != {"WR"}:
        raise ValueError("output contains non-WR rows")
    if not frame["season"].isin(SEASONS).all():
        raise ValueError("output contains seasons outside 2020-2024")

    duplicate_count = int(frame.duplicated(subset=["player_id", "season", "week"]).sum())
    if duplicate_count:
        raise ValueError(f"output contains {duplicate_count} duplicate player-week keys")

    if not (frame["targets"] >= frame["receptions"]).all():
        raise ValueError("output contains rows with receptions greater than targets")

    for column in ["targets", "receptions", "receiving_tds"]:
        if (frame[column] < 0).any():
            raise ValueError(f"output contains negative values in {column}")

    sorted_frame = frame.sort_values(
        by=["season", "week", "player_name", "player_id"],
        kind="mergesort",
    ).reset_index(drop=True)
    if not frame.equals(sorted_frame):
        raise ValueError("output is not deterministically sorted")

    blank_optional = frame[OPTIONAL_COLUMNS].isna() | (frame[OPTIONAL_COLUMNS] == "")
    for column in OPTIONAL_COLUMNS:
        non_blank_mask = ~blank_optional[column]
        if not non_blank_mask.any():
            continue
        if column == "games":
            if (frame.loc[non_blank_mask, column].astype(int) < 0).any():
                raise ValueError("games cannot be negative when present")
            continue

        values = frame.loc[non_blank_mask, column].astype(float)
        if ((values < 0.0) | (values > 1.0)).any():
            raise ValueError(f"{column} must be between 0 and 1 when present")



def _print_summary(frame: Any, output_path: Path) -> None:
    duplicate_count = int(frame.duplicated(subset=["player_id", "season", "week"]).sum())
    seasons = sorted(int(season) for season in frame["season"].drop_duplicates().tolist())
    optional_null_counts = {
        column: int((frame[column].isna() | (frame[column] == "")).sum())
        for column in OPTIONAL_COLUMNS
    }

    print(f"row count: {len(frame)}")
    print(f"distinct WR count: {frame['player_id'].nunique()}")
    print(f"seasons covered: {seasons}")
    print("optional null counts:")
    for column in OPTIONAL_COLUMNS:
        print(f"  - {column}: {optional_null_counts[column]}")
    print(f"duplicate count check: {duplicate_count}")
    print(f"output path written: {output_path}")



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a real WR weekly history CSV from nfl_data_py weekly data.",
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_PATH),
        help="Output CSV path. Defaults to data/raw/player_weekly_history.csv.",
    )
    return parser



def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    build_real_wr_history(Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
