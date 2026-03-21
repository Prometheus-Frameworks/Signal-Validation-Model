"""CSV ingestion entrypoints for historical WR research tables."""

from __future__ import annotations

from pathlib import Path

from src.transforms.wr_tables import build_canonical_wr_tables
from src.validation.wr_tables import read_raw_wr_week_rows, write_canonical_csv_tables


def build_wr_tables_from_csv(
    input_path: str | Path,
    output_dir: str | Path = "data/processed",
) -> dict[str, Path]:
    """Build canonical WR weekly, season, feature, and outcome tables from a raw CSV."""

    raw_rows = read_raw_wr_week_rows(Path(input_path))
    tables = build_canonical_wr_tables(raw_rows)
    return write_canonical_csv_tables(tables=tables, output_dir=Path(output_dir))
