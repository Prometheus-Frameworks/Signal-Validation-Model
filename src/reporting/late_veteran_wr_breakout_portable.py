"""Portable entrypoint for byte-stable late-veteran WR research artifacts.

The underlying research implementation is intentionally unchanged. This adapter
only canonicalizes transport-level line endings for digest-pinned JSON inputs,
normalizes generated text artifacts to UTF-8/LF, and records POSIX-style receipt
paths so the same bounded run is reproducible on Windows and POSIX systems.
"""

from __future__ import annotations

from contextlib import ExitStack
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
from typing import Any

from src.ingestion.tiber_player_season_coverage import (
    PINNED_PLAYER_SEASON_COVERAGE_SHA256,
)
from src.reporting.late_veteran_wr_breakout import (
    LateVeteranWrBreakoutArtifacts,
    PINNED_PILOT_RECEIPTS_SHA256,
    build_late_veteran_wr_breakout_v0 as _build_late_veteran_wr_breakout_v0,
)
from src.validation import ValidationError


def build_late_veteran_wr_breakout_v0(
    player_season_input: str | Path,
    pilot_receipts_input: str | Path,
    output_dir: str | Path = "outputs",
) -> LateVeteranWrBreakoutArtifacts:
    """Run the bounded v0 build with cross-platform byte canonicalization."""

    with ExitStack() as stack:
        player_input = _prepare_digest_pinned_json(
            Path(player_season_input),
            expected_sha256=PINNED_PLAYER_SEASON_COVERAGE_SHA256,
            label="player-season coverage",
            stack=stack,
        )
        pilot_input = _prepare_digest_pinned_json(
            Path(pilot_receipts_input),
            expected_sha256=PINNED_PILOT_RECEIPTS_SHA256,
            label="pilot receipt",
            stack=stack,
        )
        result = _build_late_veteran_wr_breakout_v0(
            player_season_input=player_input,
            pilot_receipts_input=pilot_input,
            output_dir=output_dir,
        )

    _finalize_portable_outputs(result, Path(output_dir))
    return result


def _prepare_digest_pinned_json(
    path: Path,
    *,
    expected_sha256: str,
    label: str,
    stack: ExitStack,
) -> Path:
    """Accept exact bytes or their transport-equivalent CRLF-to-LF form only."""

    if not path.exists() or not path.is_file():
        raise ValidationError(f"{label} input does not exist or is not a file: {path}")

    raw = path.read_bytes()
    if _sha256_bytes(raw) == expected_sha256:
        return path

    canonical = _to_lf(raw)
    if canonical == raw or _sha256_bytes(canonical) != expected_sha256:
        return path

    temp_root = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="tiber-lf-")))
    canonical_path = temp_root / path.name
    canonical_path.write_bytes(canonical)
    return canonical_path


def _finalize_portable_outputs(
    result: LateVeteranWrBreakoutArtifacts,
    output_root: Path,
) -> None:
    output_paths = (
        result.definition_path,
        result.summary_path,
        result.historical_pairs_path,
        result.examples_path,
        result.pilot_path,
    )
    for path in output_paths:
        path.write_bytes(_to_lf(path.read_bytes()))

    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    if not isinstance(receipt, dict):
        raise ValidationError("late-veteran WR receipt must be a JSON object")

    implementation_bindings = _require_binding_list(
        receipt,
        "implementation_bindings",
    )
    wrapper_path = Path(__file__).resolve()
    repository_root = wrapper_path.parents[2]
    wrapper_binding = {
        "relative_path": wrapper_path.relative_to(repository_root).as_posix(),
        "content_sha256": _sha256_path(wrapper_path),
    }
    implementation_by_path = {
        _as_posix_relative(binding["relative_path"]): {
            **binding,
            "relative_path": _as_posix_relative(binding["relative_path"]),
        }
        for binding in implementation_bindings
    }
    implementation_by_path[wrapper_binding["relative_path"]] = wrapper_binding
    receipt["implementation_bindings"] = [
        implementation_by_path[key] for key in sorted(implementation_by_path)
    ]

    output_bindings = _require_binding_list(receipt, "output_bindings")
    normalized_output_bindings: list[dict[str, Any]] = []
    for binding in output_bindings:
        relative_path = _as_posix_relative(binding["relative_path"])
        local_path = output_root.joinpath(*PurePosixPath(relative_path).parts)
        if not local_path.exists() or not local_path.is_file():
            raise ValidationError(
                f"receipt output binding does not resolve under output root: {relative_path}"
            )
        normalized_output_bindings.append(
            {
                **binding,
                "relative_path": relative_path,
                "content_sha256": _sha256_path(local_path),
            }
        )
    receipt["output_bindings"] = sorted(
        normalized_output_bindings,
        key=lambda binding: binding["relative_path"],
    )

    _write_json_lf(result.receipt_path, receipt)


def _require_binding_list(
    receipt: dict[str, Any],
    key: str,
) -> list[dict[str, Any]]:
    value = receipt.get(key)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValidationError(f"late-veteran WR receipt {key} must be a list of objects")
    for binding in value:
        if not isinstance(binding.get("relative_path"), str):
            raise ValidationError(
                f"late-veteran WR receipt {key} binding lacks relative_path"
            )
    return value


def _as_posix_relative(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    has_drive_prefix = bool(path.parts and ":" in path.parts[0])
    if path.is_absolute() or ".." in path.parts or has_drive_prefix:
        raise ValidationError(f"receipt path must remain relative and bounded: {value}")
    return path.as_posix()


def _write_json_lf(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_bytes(text.encode("utf-8"))


def _to_lf(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


__all__ = [
    "LateVeteranWrBreakoutArtifacts",
    "build_late_veteran_wr_breakout_v0",
]
