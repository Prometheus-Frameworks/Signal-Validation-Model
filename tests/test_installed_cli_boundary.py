from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from src.ingestion.real_wr_history import LOCAL_BUILDER_SOURCE_LOCATION


def _installed_cli() -> str:
    command = shutil.which("signal-validation")
    assert command is not None, "tests require the project CLI to be installed"
    return command


def _external_environment(*, python_path: Path | None = None) -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    if python_path is not None:
        environment["PYTHONPATH"] = str(python_path)
    return environment


def test_installed_cli_reaches_packaged_legacy_builder_outside_checkout(
    tmp_path: Path,
) -> None:
    hook_dir = tmp_path / "hook"
    run_dir = tmp_path / "run"
    hook_dir.mkdir()
    run_dir.mkdir()

    hook_dir.joinpath("sitecustomize.py").write_text(
        """from pathlib import Path

import src.ingestion.legacy_local_builder as legacy_local_builder


def _write_fixture(output_path, seasons=None):
    selected_season = (seasons or [2024])[0]
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "player_id,player_name,team,season,week,position,fantasy_points_ppr,targets,receptions,receiving_yards,receiving_tds,games,snap_share,route_participation,target_share,air_yard_share\\n"
        f"wr_installed,Installed Builder,PKG,{selected_season},1,WR,9.0,6,4,50,0,1,0.6,0.75,0.18,0.2\\n",
        encoding="utf-8",
    )
    return output_path


legacy_local_builder.build_real_wr_history = _write_fixture
""",
        encoding="utf-8",
    )

    output_path = run_dir / "player_weekly_history.csv"
    provenance_path = run_dir / "player_weekly_history.provenance.json"
    completed = subprocess.run(
        [
            _installed_cli(),
            "build-real-wr-history",
            "--source",
            "local-builder",
            "--output",
            str(output_path),
            "--provenance-output",
            str(provenance_path),
            "--local-seasons",
            "2024",
        ],
        cwd=run_dir,
        env=_external_environment(python_path=hook_dir),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert output_path.exists()
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert provenance["source_type"] == "local-builder"
    assert provenance["source_location"] == LOCAL_BUILDER_SOURCE_LOCATION
    assert provenance["used_fallback"] is False


@pytest.mark.skipif(
    sys.version_info[:2] < (3, 12),
    reason="unsupported legacy-extra boundary begins at Python 3.12",
)
def test_installed_cli_fails_closed_outside_checkout_on_unsupported_python(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "player_weekly_history.csv"
    provenance_path = tmp_path / "player_weekly_history.provenance.json"
    completed = subprocess.run(
        [
            _installed_cli(),
            "build-real-wr-history",
            "--source",
            "local-builder",
            "--output",
            str(output_path),
            "--provenance-output",
            str(provenance_path),
        ],
        cwd=tmp_path,
        env=_external_environment(),
        capture_output=True,
        text=True,
        check=False,
    )

    message = completed.stdout + completed.stderr
    assert completed.returncode != 0
    assert "Python 3.10 or 3.11" in message
    assert ".[legacy-local-builder]" in message
    assert "--source tiber-data" in message
    assert "No module named 'scripts'" not in message
    assert not output_path.exists()
    assert not provenance_path.exists()
