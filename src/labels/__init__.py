"""Breakout labeling logic for scaffold runs and WR validation datasets."""

from src.labels.late_veteran_wr_breakout import (
    DECLARED_OBSERVED_ROW_UNIVERSE,
    LATE_VETERAN_WR_BREAKOUT_V0,
    FeatureEligibility,
    HistoricalPair,
    LateVeteranWrBreakoutDefinition,
    OutcomeLabels,
    PrimaryCohortEvaluation,
    SensitivityDiagnostic,
    build_diagnostic_sensitivity_grid,
    build_historical_pairs,
    build_outcome_labels,
    evaluate_feature_eligibility,
    evaluate_primary_cohort,
)
from src.labels.wr_breakouts import build_wr_validation_dataset, write_wr_label_outputs

__all__ = [
    "DECLARED_OBSERVED_ROW_UNIVERSE",
    "LATE_VETERAN_WR_BREAKOUT_V0",
    "FeatureEligibility",
    "HistoricalPair",
    "LateVeteranWrBreakoutDefinition",
    "OutcomeLabels",
    "PrimaryCohortEvaluation",
    "SensitivityDiagnostic",
    "build_diagnostic_sensitivity_grid",
    "build_historical_pairs",
    "build_outcome_labels",
    "build_wr_validation_dataset",
    "evaluate_feature_eligibility",
    "evaluate_primary_cohort",
    "write_wr_label_outputs",
]
