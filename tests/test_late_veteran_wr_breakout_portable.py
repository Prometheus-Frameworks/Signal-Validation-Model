from __future__ import annotations

from contextlib import ExitStack
import hashlib
import json
from pathlib import Path

import pytest

from src.reporting.late_veteran_wr_breakout import LateVeteranWrBreakoutArtifacts
from src.reporting import late_veteran_wr_breakout_portable as portable
from src.validation import ValidationError


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_portable_entrypoint_normalizes_inputs_outputs_and_receipt_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical_player = b'{"kind":"player"}\n'
    canonical_pilot = b'{"kind":"pilot"}\n'
    player_input = tmp_path / "player.json"
    pilot_input = tmp_path / "pilot.json"
    player_input.write_bytes(canonical_player.replace(b"\n", b"\r\n"))
    pilot_input.write_bytes(canonical_pilot.replace(b"\n", b"\r\n"))

    monkeypatch.setattr(
        portable,
        "PINNED_PLAYER_SEASON_COVERAGE_SHA256",
        hashlib.sha256(canonical_player).hexdigest(),
    )
    monkeypatch.setattr(
        portable,
        "PINNED_PILOT_RECEIPTS_SHA256",
        hashlib.sha256(canonical_pilot).hexdigest(),
    )

    observed_inputs: list[bytes] = []

    def fake_build(
        *,
        player_season_input: str | Path,
        pilot_receipts_input: str | Path,
        output_dir: str | Path,
    ) -> LateVeteranWrBreakoutArtifacts:
        player_path = Path(player_season_input)
        pilot_path = Path(pilot_receipts_input)
        observed_inputs.extend([player_path.read_bytes(), pilot_path.read_bytes()])

        root = Path(output_dir)
        validation = root / "validation_reports"
        case_studies = root / "case_studies"
        validation.mkdir(parents=True)
        case_studies.mkdir(parents=True)

        definition = validation / "late_veteran_wr_breakout_v0_definition.json"
        summary = validation / "late_veteran_wr_breakout_v0_summary.json"
        pairs = validation / "late_veteran_wr_breakout_v0_historical_pairs.csv"
        examples = case_studies / "late_veteran_wr_breakout_v0_examples.md"
        pilot = case_studies / "late_veteran_wr_breakout_2026_pilot.json"
        receipt = validation / "late_veteran_wr_breakout_v0_receipt.json"

        for path, raw in (
            (definition, b'{"artifact":"definition"}\r\n'),
            (summary, b'{"artifact":"summary"}\r\n'),
            (pairs, b"player_id,value\r\n00-test,1\r\n"),
            (examples, b"# Examples\r\nBare CR\r"),
            (pilot, b'{"artifact":"pilot"}\r\n'),
        ):
            path.write_bytes(raw)

        output_paths = (definition, summary, pairs, examples, pilot)
        receipt_payload = {
            "implementation_bindings": [
                {
                    "relative_path": "src\\reporting\\late_veteran_wr_breakout.py",
                    "content_sha256": "existing-implementation-digest",
                }
            ],
            "output_bindings": [
                {
                    "relative_path": str(path.relative_to(root)).replace("/", "\\"),
                    "content_sha256": "stale-output-digest",
                }
                for path in output_paths
            ],
            "run_guards": {
                "receipt_self_hash_excluded": True,
            },
        }
        receipt.write_bytes(
            (json.dumps(receipt_payload, indent=2, sort_keys=True) + "\r\n").encode()
        )

        return LateVeteranWrBreakoutArtifacts(
            definition_path=definition,
            summary_path=summary,
            historical_pairs_path=pairs,
            examples_path=examples,
            pilot_path=pilot,
            receipt_path=receipt,
            terminal_decision=(
                "late_veteran_wr_breakout_v0_requires_data_or_definition_followup"
            ),
        )

    monkeypatch.setattr(
        portable,
        "_build_late_veteran_wr_breakout_v0",
        fake_build,
    )

    output_root = tmp_path / "outputs"
    result = portable.build_late_veteran_wr_breakout_v0(
        player_input,
        pilot_input,
        output_root,
    )

    assert observed_inputs == [canonical_player, canonical_pilot]
    assert b"\r\n" in player_input.read_bytes()
    assert b"\r\n" in pilot_input.read_bytes()

    generated = (
        result.definition_path,
        result.summary_path,
        result.historical_pairs_path,
        result.examples_path,
        result.pilot_path,
        result.receipt_path,
    )
    assert all(b"\r" not in path.read_bytes() for path in generated)

    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    implementation_paths = {
        binding["relative_path"] for binding in receipt["implementation_bindings"]
    }
    assert "src/reporting/late_veteran_wr_breakout.py" in implementation_paths
    assert "src/reporting/late_veteran_wr_breakout_portable.py" in implementation_paths
    assert all("\\" not in value for value in implementation_paths)

    for binding in receipt["output_bindings"]:
        assert "\\" not in binding["relative_path"]
        output_path = output_root.joinpath(*binding["relative_path"].split("/"))
        assert binding["content_sha256"] == _sha256(output_path)


@pytest.mark.parametrize(
    "transported",
    (
        b'{\r  "kind": "player"\r}\r',
        b'{\r\n  "kind": "player"\r}\r\n',
    ),
)
def test_digest_pinned_input_only_canonicalizes_crlf_pairs(
    tmp_path: Path,
    transported: bytes,
) -> None:
    canonical = b'{\n  "kind": "player"\n}\n'
    expected_sha256 = hashlib.sha256(canonical).hexdigest()
    input_path = tmp_path / "player.json"
    input_path.write_bytes(transported)

    assert portable._to_lf(transported) == canonical
    with ExitStack() as stack:
        prepared = portable._prepare_digest_pinned_json(
            input_path,
            expected_sha256=expected_sha256,
            label="player-season coverage",
            stack=stack,
        )
        assert prepared == input_path
        assert prepared.read_bytes() == transported
        assert hashlib.sha256(prepared.read_bytes()).hexdigest() != expected_sha256


@pytest.mark.parametrize(
    "value",
    (
        "../escape.json",
        "nested/../../escape.json",
        "/absolute/path.json",
        "C:\\absolute\\path.json",
    ),
)
def test_receipt_paths_remain_relative_and_bounded(value: str) -> None:
    with pytest.raises(ValidationError):
        portable._as_posix_relative(value)
