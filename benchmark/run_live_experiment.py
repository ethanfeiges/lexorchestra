"""Backward-compatible alias for benchmark.run_experiment."""

from __future__ import annotations

import sys

from benchmark.experiment import DEFAULT_DOCUMENTS, DEFAULT_STRATEGY, run_gemini_matrix
from benchmark.run_experiment import load_dotenv_if_present, main

# Re-export names used by tests and scripts.
LIVE_DOCUMENTS = DEFAULT_DOCUMENTS
DEFAULT_LIVE_STRATEGY = DEFAULT_STRATEGY
run_live_matrix = run_gemini_matrix

__all__ = [
    "DEFAULT_LIVE_STRATEGY",
    "LIVE_DOCUMENTS",
    "load_dotenv_if_present",
    "main",
    "run_live_matrix",
]

if __name__ == "__main__":
    raise SystemExit(main())
