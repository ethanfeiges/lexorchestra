#!/usr/bin/env python3
"""Run pytest after code changes. Used by Cursor hooks."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEBOUNCE_SEC = 3
LAST_RUN_FILE = Path(__file__).resolve().parent / ".last_test_run"
RELEVANT_PATH = re.compile(r"(^|[\\/])(docProcessing|tests|benchmark)[\\/]|pyproject\.toml$|\.py$")


def _read_hook_input() -> dict:
    if sys.stdin.isatty():
        return {}
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError:
        return {}


def _should_run_for_edit(hook_input: dict) -> bool:
    file_path = hook_input.get("file_path") or hook_input.get("path") or ""
    if not file_path:
        return True
    normalized = file_path.replace("\\", "/")
    if normalized.startswith("context/") or normalized.startswith("legalDocs/contracts/public/"):
        return False
    return bool(RELEVANT_PATH.search(normalized))


def _debounced() -> bool:
    now = time.time()
    if LAST_RUN_FILE.exists():
        try:
            last = float(LAST_RUN_FILE.read_text(encoding="utf-8").strip())
        except ValueError:
            last = 0.0
        if now - last < DEBOUNCE_SEC:
            return True
    LAST_RUN_FILE.write_text(str(now), encoding="utf-8")
    return False


def run_pytest() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def _format_failure(result: subprocess.CompletedProcess[str]) -> str:
    parts = [result.stdout.strip(), result.stderr.strip()]
    body = "\n".join(part for part in parts if part)
    return body or "pytest failed with no output"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("after-edit", "stop"), default="after-edit")
    args = parser.parse_args()
    hook_input = _read_hook_input()

    if args.mode == "after-edit" and not _should_run_for_edit(hook_input):
        print(json.dumps({}))
        return 0

    if args.mode == "after-edit" and _debounced():
        print(json.dumps({}))
        return 0

    result = run_pytest()
    passed = result.returncode == 0
    summary = result.stdout.strip() or ("passed" if passed else "failed")

    if args.mode == "after-edit":
        payload: dict[str, str] = {}
        if passed:
            payload["additional_context"] = f"[auto-test] {summary}"
        else:
            payload["additional_context"] = (
                "[auto-test] Tests failed after your edit. Fix before continuing:\n"
                + _format_failure(result)
            )
        print(json.dumps(payload))
        return 0

    # stop hook: ask agent to fix failures before ending the turn
    if passed:
        print(json.dumps({}))
        return 0

    print(
        json.dumps(
            {
                "followup_message": (
                    "Automated test run failed. Fix all failing tests, then re-run "
                    "`python -m pytest tests/ -q` and summarize what you fixed.\n\n"
                    + _format_failure(result)
                )
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
