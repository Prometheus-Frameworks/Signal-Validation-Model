"""Scaffold-only backtest pipeline using deterministic mock data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.backtest.scoring import SCORING_VERSION, build_candidate_ranking_rows
from src.config import BacktestConfig
from src.features.mock_data import MOCK_OUTCOMES_2025, load_mock_feature_rows
from src.labels.rules import assign_breakout_label
from src.reporting.writer import write_candidate_rankings, write_validation_summary
from src.schemas import ValidationSummaryRow


@dataclass(frozen=True)
class ScaffoldRunResult:
    candidate_ranking_path: Path
    validation_report_path: Path


def run_scaffold_pipeline(output_dir: str | Path = "outputs") -> ScaffoldRunResult:
    """Run the deterministic scaffold-only research flow on mock WR data."""

    config = BacktestConfig(output_dir=Path(output_dir))
    feature_rows = load_mock_feature_rows()
    outcome_rows = {row["player_id"]: row for row in MOCK_OUTCOMES_2025}

    labels = [assign_breakout_label(row, outcome_rows[row.player_id]) for row in feature_rows]
    rankings = build_candidate_ranking_rows(feature_rows)

    summary = ValidationSummaryRow(
        feature_season=config.feature_season,
        outcome_season=config.outcome_season,
        position=config.position,
        candidate_count=len(rankings),
        breakout_count=sum(1 for row in labels if row.is_breakout),
        top_ranked_player_id=rankings[0].player_id,
        top_ranked_player_name=rankings[0].player_name,
        scoring_version=SCORING_VERSION,
        summary_note=(
            "Scaffold-only validation summary built from mock data. "
            "No predictive-power claim is implied."
        ),
    )

    candidate_path = config.candidate_rankings_dir() / "wr_2024_features_for_2025_outcomes_scaffold.csv"
    summary_path = config.validation_reports_dir() / "wr_2024_to_2025_scaffold_summary.json"

    write_candidate_rankings(candidate_path, rankings)
    write_validation_summary(summary_path, summary)

    return ScaffoldRunResult(
        candidate_ranking_path=candidate_path,
        validation_report_path=summary_path,
    )
