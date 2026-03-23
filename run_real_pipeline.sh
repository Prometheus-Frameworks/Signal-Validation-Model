#!/usr/bin/env bash
set -e

signal-validation build-real-wr-history --source preferred

signal-validation build-wr-tables --input data/raw/player_weekly_history.csv
signal-validation build-wr-labels --processed-dir data/processed --output-dir outputs/validation_reports
signal-validation enrich-wr-cohorts --processed-dir data/processed --validation-dataset outputs/validation_reports/wr_validation_dataset.csv --output-dir outputs/validation_reports
signal-validation enrich-wr-role --processed-dir data/processed --validation-dataset outputs/validation_reports/wr_validation_dataset_enriched.csv --output-dir outputs/validation_reports
signal-validation compare-wr-recipes --validation-dataset outputs/validation_reports/wr_validation_dataset_role_enriched.csv --output-dir outputs

signal-validation build-wr-case-study --validation-dataset outputs/validation_reports/wr_validation_dataset_role_enriched.csv --comparison-summary outputs/validation_reports/wr_recipe_comparison_summary.json --candidate-dir outputs/candidate_rankings --output-dir outputs/case_studies --feature-season 2024 --outcome-season 2025

signal-validation export-wr-results --validation-dataset outputs/validation_reports/wr_validation_dataset_role_enriched.csv --comparison-summary outputs/validation_reports/wr_recipe_comparison_summary.json --candidate-dir outputs/candidate_rankings --case-study-dir outputs/case_studies --output-dir outputs/exports --feature-season 2024 --outcome-season 2025

signal-validation build-wr-public-report --exports-dir outputs/exports --case-study-dir outputs/case_studies --comparison-summary outputs/validation_reports/wr_recipe_comparison_summary.json --output-dir outputs/public --feature-season 2024 --outcome-season 2025

signal-validation build-wr-public-findings --public-dir outputs/public --comparison-summary outputs/validation_reports/wr_recipe_comparison_summary.json --case-study-dir outputs/case_studies --exports-dir outputs/exports --feature-season 2024 --outcome-season 2025

echo "Done. Start reading outputs/public/wr_public_findings_2024_to_2025.md"
