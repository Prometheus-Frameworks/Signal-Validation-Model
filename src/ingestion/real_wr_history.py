"""Source selection and provenance for real WR historical ingestion."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Sequence

from src.ingestion.tiber_data_adapter import (
    DEFAULT_TIBER_API_ENV_VARS,
    DEFAULT_TIBER_EXPORT_ENV_VARS,
    TiberDataIngestionResult,
    TiberDataSourceUnavailable,
    build_wr_history_from_tiber_data,
)
from src.validation import read_raw_wr_week_rows

LOCAL_BUILDER_SOURCE_TYPE = "local-builder"



def build_real_wr_history_with_preferred_source(
    *,
    output_path: str | Path,
    provenance_path: str | Path | None = None,
    source: str = "preferred",
    tiber_export_path: str | None = None,
    tiber_api_url: str | None = None,
    local_seasons: Sequence[int] | None = None,
) -> TiberDataIngestionResult:
    """Build the raw WR history contract from TIBER-Data when configured, else local fallback."""

    output_path = Path(output_path)
    provenance_path = Path(provenance_path) if provenance_path is not None else output_path.with_suffix(
        ".provenance.json"
    )

    if source not in {"preferred", "tiber-data", "local-builder"}:
        raise ValueError("source must be one of: preferred, tiber-data, local-builder")

    resolved_tiber_export = tiber_export_path or _read_first_env(DEFAULT_TIBER_EXPORT_ENV_VARS)
    resolved_tiber_api = tiber_api_url or _read_first_env(DEFAULT_TIBER_API_ENV_VARS)

    if source in {"preferred", "tiber-data"}:
        try:
            return build_wr_history_from_tiber_data(
                output_path=output_path,
                provenance_path=provenance_path,
                export_path_or_url=resolved_tiber_export,
                api_url=resolved_tiber_api,
            )
        except TiberDataSourceUnavailable as exc:
            if source == "tiber-data":
                raise
            fallback_reason = str(exc)
            print(
                "TIBER-Data source unavailable; explicitly falling back to local-builder. "
                f"Reason: {fallback_reason}"
            )
            return _build_from_local_builder(
                output_path=output_path,
                provenance_path=provenance_path,
                local_seasons=local_seasons,
                fallback_reason=fallback_reason,
            )

    return _build_from_local_builder(
        output_path=output_path,
        provenance_path=provenance_path,
        local_seasons=local_seasons,
        fallback_reason=None,
    )



def _build_from_local_builder(
    *,
    output_path: Path,
    provenance_path: Path,
    local_seasons: Sequence[int] | None,
    fallback_reason: str | None,
) -> TiberDataIngestionResult:
    from scripts.build_real_wr_data import build_real_wr_history  # local import to avoid circular CLI/script coupling

    build_real_wr_history(output_path=output_path, seasons=list(local_seasons) if local_seasons else None)
    rows = read_raw_wr_week_rows(output_path)
    seasons = tuple(sorted({int(row["season"]) for row in rows}))
    provenance = {
        "source_type": LOCAL_BUILDER_SOURCE_TYPE,
        "source_location": "scripts/build_real_wr_data.py",
        "row_count": len(rows),
        "seasons": list(seasons),
        "used_fallback": fallback_reason is not None,
        "fallback_reason": fallback_reason,
    }
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return TiberDataIngestionResult(
        raw_csv_path=output_path,
        provenance_path=provenance_path,
        source_type=LOCAL_BUILDER_SOURCE_TYPE,
        source_location="scripts/build_real_wr_data.py",
        row_count=len(rows),
        seasons=seasons,
        used_fallback=fallback_reason is not None,
        fallback_reason=fallback_reason,
    )



def _read_first_env(names: Sequence[str]) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None
