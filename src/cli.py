"""CLI entrypoint for the signal validation research workflows."""

from __future__ import annotations

import argparse

from src.backtest.pipeline import run_scaffold_pipeline
from src.ingestion import build_wr_tables_from_csv
from src.labels.wr_breakouts import write_wr_label_outputs
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

    compare_parser = subparsers.add_parser(
        "compare-wr-recipes",
        help="Compare multiple deterministic WR score recipes against the same labeled validation dataset.",
    )
    compare_parser.add_argument(
        "--validation-dataset",
        default="outputs/validation_reports/wr_validation_dataset.csv",
        help="Path to the PR3 WR validation dataset CSV.",
    )
    compare_parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Base output directory for per-recipe rankings and comparison reports.",
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

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
