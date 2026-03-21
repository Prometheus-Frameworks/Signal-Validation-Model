"""Writers for scaffold candidate rankings and validation summaries."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from src.schemas import CandidateRankingRow, ValidationSummaryRow


def write_candidate_rankings(path: Path, rankings: list[CandidateRankingRow]) -> Path:
    """Write scaffold candidate rankings to CSV."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "player_id",
                "player_name",
                "feature_season",
                "target_outcome_season",
                "position",
                "breakout_signal_score",
                "rank",
                "score_components",
                "scoring_version",
                "notes",
            ],
        )
        writer.writeheader()
        for row in rankings:
            payload = row.model_dump()
            payload["score_components"] = json.dumps(payload["score_components"], sort_keys=True)
            writer.writerow(payload)
    return path


def write_validation_summary(path: Path, summary: ValidationSummaryRow) -> Path:
    """Write scaffold validation summary to JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(summary.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path
