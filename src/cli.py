"""CLI entrypoint for the scaffolded signal validation pipeline."""

from __future__ import annotations

import argparse

from src.backtest.pipeline import run_scaffold_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="signal-validation",
        description="Historical signal-validation scaffold for fantasy football breakout research.",
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


if __name__ == "__main__":
    main()
