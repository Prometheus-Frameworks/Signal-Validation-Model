"""CLI entrypoint for the signal validation research workflows."""

from __future__ import annotations

import argparse

from src.backtest.pipeline import run_scaffold_pipeline
from src.enrichment import write_wr_cohort_outputs, write_wr_role_outputs
from src.exports import export_wr_results
from src.ingestion import build_wr_tables_from_csv
from src.labels.wr_breakouts import write_wr_label_outputs
from src.public import build_wr_public_findings, build_wr_public_report
from src.reporting import build_wr_case_study
from src.scoring import compare_wr_recipes, score_wr_candidates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="signal-validation",
        description="Historical signal-validation workflows for fantasy football breakout research.",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    run_parser = subparsers.add_parser(
        "run-scaffold",
        help="Run the deterministic scaffold-only backtest flow on mock data.",
    )
    run_parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory for scaffold candidate rankings and validation reports.",
    )

    ingest_parser = subparsers.add_parser(
        "build-wr-tables",
        help="Build canonical historical WR weekly, season, feature, and outcome CSV tables.",
    )
    ingest_parser.add_argument(
        "--input",
        required=True,
        help="Path to the raw historical WR weekly CSV input.",
    )
    ingest_parser.add_argument(
        "--output-dir",
        default="data/processed",
        help="Directory for canonical WR processed tables.",
    )

    label_parser = subparsers.add_parser(
        "build-wr-labels",
        help="Build deterministic WR breakout labels and validation reports from processed tables.",
    )
    label_parser.add_argument(
        "--processed-dir",
        default="data/processed",
        help="Directory containing wr_feature_seasons.csv and wr_outcome_seasons.csv.",
    )
    label_parser.add_argument(
        "--output-dir",
        default="outputs/validation_reports",
        help="Directory for WR validation datasets, labels, summaries, and examples.",
    )

    score_parser = subparsers.add_parser(
        "score-wr-candidates",
        help="Score WR breakout candidates from the PR3 validation dataset and write PR4 artifacts.",
    )
    score_parser.add_argument(
        "--validation-dataset",
        default="outputs/validation_reports/wr_validation_dataset.csv",
        help="Path to the PR3 WR validation dataset CSV.",
    )
    score_parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Base output directory for candidate rankings and validation reports.",
    )


    enrich_parser = subparsers.add_parser(
        "enrich-wr-cohorts",
        help="Enrich the WR validation dataset with deterministic cohort-baseline context and write PR6 artifacts.",
    )
    enrich_parser.add_argument(
        "--processed-dir",
        default="data/processed",
        help="Directory containing wr_feature_seasons.csv for deterministic cohort assignment.",
    )
    enrich_parser.add_argument(
        "--validation-dataset",
        default="outputs/validation_reports/wr_validation_dataset.csv",
        help="Path to the canonical WR validation dataset CSV to enrich.",
    )
    enrich_parser.add_argument(
        "--output-dir",
        default="outputs/validation_reports",
        help="Directory for enriched WR cohort-baseline artifacts.",
    )

    compare_parser = subparsers.add_parser(
        "compare-wr-recipes",
        help="Compare multiple deterministic WR score recipes against the same labeled validation dataset.",
    )
    compare_parser.add_argument(
        "--validation-dataset",
        default="outputs/validation_reports/wr_validation_dataset_role_enriched.csv",
        help="Path to the WR validation dataset CSV, typically the PR8 role-enriched dataset.",
    )
    compare_parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Base output directory for per-recipe rankings and comparison reports.",
    )

    case_study_parser = subparsers.add_parser(
        "build-wr-case-study",
        help="Build a deterministic season-pair WR case study from validation and recipe outputs.",
    )
    case_study_parser.add_argument(
        "--validation-dataset",
        default="outputs/validation_reports/wr_validation_dataset_role_enriched.csv",
        help="Path to the enriched WR validation dataset CSV.",
    )
    case_study_parser.add_argument(
        "--comparison-summary",
        default="outputs/validation_reports/wr_recipe_comparison_summary.json",
        help="Path to the WR recipe comparison summary JSON.",
    )
    case_study_parser.add_argument(
        "--candidate-dir",
        default="outputs/candidate_rankings",
        help="Directory containing per-recipe WR candidate ranking CSV files.",
    )
    case_study_parser.add_argument(
        "--output-dir",
        default="outputs/case_studies",
        help="Directory for season-pair WR case-study artifacts.",
    )
    case_study_parser.add_argument(
        "--feature-season",
        required=True,
        type=int,
        help="Feature season to analyze, such as 2024.",
    )
    case_study_parser.add_argument(
        "--outcome-season",
        required=True,
        type=int,
        help="Outcome season paired with the feature season, such as 2025.",
    )

    export_parser = subparsers.add_parser(
        "export-wr-results",
        help="Export deterministic downstream WR breakout artifacts from existing validated outputs.",
    )
    export_parser.add_argument(
        "--validation-dataset",
        default="outputs/validation_reports/wr_validation_dataset_role_enriched.csv",
        help="Path to the validated WR dataset CSV used by downstream exports.",
    )
    export_parser.add_argument(
        "--comparison-summary",
        default="outputs/validation_reports/wr_recipe_comparison_summary.json",
        help="Path to the WR recipe comparison summary JSON.",
    )
    export_parser.add_argument(
        "--candidate-dir",
        default="outputs/candidate_rankings",
        help="Directory containing best-recipe ranking and component CSV artifacts.",
    )
    export_parser.add_argument(
        "--case-study-dir",
        default="outputs/case_studies",
        help="Directory containing season-pair case-study artifacts.",
    )
    export_parser.add_argument(
        "--output-dir",
        default="outputs/exports",
        help="Directory for canonical downstream export artifacts.",
    )
    export_parser.add_argument(
        "--feature-season",
        required=True,
        type=int,
        help="Feature season to export, such as 2024.",
    )
    export_parser.add_argument(
        "--outcome-season",
        required=True,
        type=int,
        help="Outcome season paired with the feature season, such as 2025.",
    )

    public_report_parser = subparsers.add_parser(
        "build-wr-public-report",
        help="Build a public-facing WR report pack from deterministic export and case-study artifacts.",
    )
    public_report_parser.add_argument(
        "--exports-dir",
        default="outputs/exports",
        help="Directory containing deterministic WR export artifacts.",
    )
    public_report_parser.add_argument(
        "--case-study-dir",
        default="outputs/case_studies",
        help="Directory containing deterministic WR case-study artifacts.",
    )
    public_report_parser.add_argument(
        "--comparison-summary",
        default="outputs/validation_reports/wr_recipe_comparison_summary.json",
        help="Path to the WR recipe comparison summary JSON.",
    )
    public_report_parser.add_argument(
        "--output-dir",
        default="outputs/public",
        help="Directory for public-facing WR report artifacts.",
    )
    public_report_parser.add_argument(
        "--feature-season",
        required=True,
        type=int,
        help="Feature season to report, such as 2024.",
    )
    public_report_parser.add_argument(
        "--outcome-season",
        required=True,
        type=int,
        help="Outcome season paired with the feature season, such as 2025.",
    )

    public_findings_parser = subparsers.add_parser(
        "build-wr-public-findings",
        help="Build a public-facing WR findings/narrative pack from deterministic validated outputs.",
    )
    public_findings_parser.add_argument(
        "--comparison-summary",
        default="outputs/validation_reports/wr_recipe_comparison_summary.json",
        help="Path to the WR recipe comparison summary JSON.",
    )
    public_findings_parser.add_argument(
        "--case-study-dir",
        default="outputs/case_studies",
        help="Directory containing deterministic WR case-study artifacts.",
    )
    public_findings_parser.add_argument(
        "--exports-dir",
        default="outputs/exports",
        help="Directory containing deterministic WR export artifacts.",
    )
    public_findings_parser.add_argument(
        "--public-dir",
        default="outputs/public",
        help="Alias for the public output directory used by earlier public-report workflows.",
    )
    public_findings_parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for public-facing WR findings artifacts. Defaults to --public-dir when omitted.",
    )
    public_findings_parser.add_argument(
        "--feature-season",
        required=True,
        type=int,
        help="Feature season to report, such as 2024.",
    )
    public_findings_parser.add_argument(
        "--outcome-season",
        required=True,
        type=int,
        help="Outcome season paired with the feature season, such as 2025.",
    )

    role_enrich_parser = subparsers.add_parser(
        "enrich-wr-role",
        help="Enrich the WR validation dataset with deterministic role-and-opportunity signals and write PR8 artifacts.",
    )
    role_enrich_parser.add_argument(
        "--processed-dir",
        default="data/processed",
        help="Directory containing canonical wr_player_weeks.csv and wr_player_seasons.csv tables.",
    )
    role_enrich_parser.add_argument(
        "--validation-dataset",
        default="outputs/validation_reports/wr_validation_dataset_enriched.csv",
        help="Path to the WR validation dataset CSV to role-enrich, typically the PR6 cohort-enriched dataset.",
    )
    role_enrich_parser.add_argument(
        "--output-dir",
        default="outputs/validation_reports",
        help="Directory for role-enriched WR validation artifacts.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run-scaffold":
        result = run_scaffold_pipeline(output_dir=args.output_dir)
        print(
            "Scaffold only: executed deterministic mock backtest flow. "
            f"Wrote rankings to {result.candidate_ranking_path} and summary to {result.validation_report_path}."
        )
        return

    if args.command == "build-wr-tables":
        output_paths = build_wr_tables_from_csv(
            input_path=args.input,
            output_dir=args.output_dir,
        )
        print("Built canonical WR historical tables:")
        for table_name, path in sorted(output_paths.items()):
            print(f"- {table_name}: {path}")
        return

    if args.command == "build-wr-labels":
        output_paths = write_wr_label_outputs(
            processed_dir=args.processed_dir,
            output_dir=args.output_dir,
        )
        print("Built WR breakout labeling artifacts:")
        for table_name, path in sorted(output_paths.items()):
            print(f"- {table_name}: {path}")
        return

    if args.command == "enrich-wr-cohorts":
        artifacts = write_wr_cohort_outputs(
            processed_dir=args.processed_dir,
            validation_dataset_path=args.validation_dataset,
            output_dir=args.output_dir,
        )
        print("Built WR cohort enrichment artifacts:")
        for label, path in sorted(artifacts.__dict__.items()):
            print(f"- {label}: {path}")
        return

    if args.command == "enrich-wr-role":
        artifacts = write_wr_role_outputs(
            processed_dir=args.processed_dir,
            validation_dataset_path=args.validation_dataset,
            output_dir=args.output_dir,
        )
        print("Built WR role enrichment artifacts:")
        for label, path in sorted(artifacts.__dict__.items()):
            print(f"- {label}: {path}")
        return

    if args.command == "score-wr-candidates":
        artifacts = score_wr_candidates(
            validation_dataset_path=args.validation_dataset,
            output_dir=args.output_dir,
        )
        print("Built WR candidate scoring artifacts:")
        for label, path in sorted(artifacts.__dict__.items()):
            print(f"- {label}: {path}")
        return

    if args.command == "compare-wr-recipes":
        artifacts = compare_wr_recipes(
            validation_dataset_path=args.validation_dataset,
            output_dir=args.output_dir,
        )
        print("Built WR recipe comparison artifacts:")
        for label, path in sorted(artifacts.__dict__.items()):
            print(f"- {label}: {path}")
        return

    if args.command == "build-wr-case-study":
        artifacts = build_wr_case_study(
            validation_dataset_path=args.validation_dataset,
            comparison_summary_path=args.comparison_summary,
            candidate_dir=args.candidate_dir,
            output_dir=args.output_dir,
            feature_season=args.feature_season,
            outcome_season=args.outcome_season,
        )
        print("Built WR case-study artifacts:")
        for label, path in sorted(artifacts.__dict__.items()):
            print(f"- {label}: {path}")
        return

    if args.command == "export-wr-results":
        artifacts = export_wr_results(
            validation_dataset_path=args.validation_dataset,
            comparison_summary_path=args.comparison_summary,
            candidate_dir=args.candidate_dir,
            case_study_dir=args.case_study_dir,
            output_dir=args.output_dir,
            feature_season=args.feature_season,
            outcome_season=args.outcome_season,
        )
        print("Built WR export artifacts:")
        for label, path in sorted(artifacts.__dict__.items()):
            print(f"- {label}: {path}")
        return

    if args.command == "build-wr-public-report":
        artifacts = build_wr_public_report(
            exports_dir=args.exports_dir,
            case_study_dir=args.case_study_dir,
            comparison_summary_path=args.comparison_summary,
            output_dir=args.output_dir,
            feature_season=args.feature_season,
            outcome_season=args.outcome_season,
        )
        print("Built WR public-report artifacts:")
        for label, path in sorted(artifacts.__dict__.items()):
            print(f"- {label}: {path}")
        return

    if args.command == "build-wr-public-findings":
        artifacts = build_wr_public_findings(
            comparison_summary_path=args.comparison_summary,
            case_study_dir=args.case_study_dir,
            exports_dir=args.exports_dir,
            output_dir=args.output_dir or args.public_dir,
            feature_season=args.feature_season,
            outcome_season=args.outcome_season,
        )
        print("Built WR public-findings artifacts:")
        for label, path in sorted(artifacts.__dict__.items()):
            print(f"- {label}: {path}")
        return

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
