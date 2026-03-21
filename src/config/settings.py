"""Configuration models for scaffold runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BacktestConfig:
    """Minimal configuration for the scaffold-only backtest flow."""

    feature_season: int = 2024
    outcome_season: int = 2025
    position: str = "WR"
    output_dir: Path = Path("outputs")

    def candidate_rankings_dir(self) -> Path:
        return self.output_dir / "candidate_rankings"

    def validation_reports_dir(self) -> Path:
        return self.output_dir / "validation_reports"
