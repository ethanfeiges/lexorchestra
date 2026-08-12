"""Regenerate mock baseline and fail if committed files drift."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_DIR = REPO_ROOT / "experiments" / "mock_baseline"


def main() -> int:
    run = subprocess.run(
        [sys.executable, "-m", "benchmark.run_experiment"],
        cwd=REPO_ROOT,
    )
    if run.returncode != 0:
        return run.returncode

    diff = subprocess.run(
        ["git", "diff", "--exit-code", str(BASELINE_DIR)],
        cwd=REPO_ROOT,
    )
    if diff.returncode != 0:
        print(
            "Baseline drift detected under experiments/mock_baseline/. "
            "Review git diff and commit updated baseline if intentional.",
            file=sys.stderr,
        )
    return diff.returncode


if __name__ == "__main__":
    raise SystemExit(main())
