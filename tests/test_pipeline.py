import json
from pathlib import Path

from src.backtest.pipeline import run_scaffold_pipeline


def test_pipeline_emits_placeholder_outputs(tmp_path: Path) -> None:
    result = run_scaffold_pipeline(output_dir=tmp_path)

    assert result.candidate_ranking_path.exists()
    assert result.validation_report_path.exists()

    summary = json.loads(result.validation_report_path.read_text(encoding="utf-8"))
    assert summary["candidate_count"] == 3
    assert summary["breakout_count"] == 2
    assert "Scaffold-only" in summary["summary_note"]
