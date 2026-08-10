#!/usr/bin/env python3
"""Thin CLI wrapper for the packaged deprecated local WR builder."""

from __future__ import annotations

import sys

from src.ingestion.legacy_local_builder import (
    DEFAULT_SEASONS,
    OUTPUT_COLUMNS,
    REQUIRED_COLUMNS,
    SEASONS,
    LegacyLocalBuilderUnavailable,
    _import_dependencies,
    build_parser,
    build_real_wr_history,
    main,
)

__all__ = [
    "DEFAULT_SEASONS",
    "OUTPUT_COLUMNS",
    "REQUIRED_COLUMNS",
    "SEASONS",
    "LegacyLocalBuilderUnavailable",
    "_import_dependencies",
    "build_parser",
    "build_real_wr_history",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
