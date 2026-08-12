#!/usr/bin/env python3
"""Validate experiment docs against committed manifests.

Usage:
    python scripts/sync_experiment_docs.py          # print current state
    python scripts/sync_experiment_docs.py --check  # exit 1 if docs drift
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from benchmark.run_live_experiment import LIVE_DOCUMENTS

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = REPO_ROOT / "experiments"
LIVE_CATALOG = REPO_ROOT / "experimentDocs" / "EXPERIMENTS.md"
MOCK_CATALOG = REPO_ROOT / "experimentDocs" / "MOCK_EXPERIMENTS.md"

LIVE_EXPECTED_RUNS = len(LIVE_DOCUMENTS) * 2

EXPECTED = {
    "mock_baseline": {
        "runs": 24,
        "doc": MOCK_CATALOG,
        "keywords": ["11001", "11024", "decoy_anchored", "edgar_chime_financial_inc_ex10.1"],
    },
    "ablations": {
        "runs": 6,
        "doc": MOCK_CATALOG,
        "keywords": ["full_pipeline", "no_verifier", "unlabeled", "unlabeled_noisy"],
    },
    "live_gemini": {
        "runs": LIVE_EXPECTED_RUNS,
        "doc": LIVE_CATALOG,
        "keywords": [
            "gemini-2.5-flash",
            "parallel_grounded",
            "edgar_aspira_women_s_health_inc_ex10.1",
            "edgar_pulmatrix_inc_ex10.6",
            "subtasks",
        ],
    },
}


def _load_manifest(suite: str) -> dict:
    path = EXPERIMENTS / suite / "manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _count_results(suite: str) -> int:
    path = EXPERIMENTS / suite / "results.json"
    if not path.is_file():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    return len(data) if isinstance(data, list) else 0


def collect_state() -> dict[str, dict]:
    state: dict[str, dict] = {}
    for suite in EXPECTED:
        manifest = _load_manifest(suite)
        state[suite] = {
            "manifest": manifest,
            "result_count": _count_results(suite),
            "expected_runs": EXPECTED[suite]["runs"],
        }
    return state


def print_state(state: dict[str, dict]) -> None:
    print("LexOrchestra experiment state\n")
    for suite, info in state.items():
        m = info["manifest"]
        print(f"  {suite}:")
        print(f"    results.json rows: {info['result_count']} (expected {info['expected_runs']})")
        print(f"    mode: {m.get('mode', '?')}")
        if "generated" in m:
            print(f"    generated: {m['generated']}")
        if m.get("status"):
            print(f"    status: {m['status']}")
    print(f"\n  Live catalog: {LIVE_CATALOG.relative_to(REPO_ROOT)}")
    print(f"  Mock catalog: {MOCK_CATALOG.relative_to(REPO_ROOT)}")


def check_docs(state: dict[str, dict]) -> list[str]:
    errors: list[str] = []

    if not LIVE_CATALOG.is_file():
        errors.append("experimentDocs/EXPERIMENTS.md is missing")
    if not MOCK_CATALOG.is_file():
        errors.append("experimentDocs/MOCK_EXPERIMENTS.md is missing")

    live_text = LIVE_CATALOG.read_text(encoding="utf-8") if LIVE_CATALOG.is_file() else ""
    mock_text = MOCK_CATALOG.read_text(encoding="utf-8") if MOCK_CATALOG.is_file() else ""

    for suite, info in state.items():
        expected = info["expected_runs"]
        actual = info["result_count"]
        if actual != expected:
            if suite == "live_gemini" and actual >= 4 and actual < expected:
                pass  # partial live run until quota allows full matrix
            else:
                errors.append(
                    f"{suite}: results.json has {actual} rows, expected {expected}"
                )

        cfg = EXPECTED[suite]
        doc_text = live_text if cfg["doc"] == LIVE_CATALOG else mock_text
        doc_name = cfg["doc"].relative_to(REPO_ROOT)
        for keyword in cfg["keywords"]:
            if keyword not in doc_text:
                errors.append(f"{doc_name} missing expected keyword: {keyword!r}")

    if f"{LIVE_EXPECTED_RUNS} runs" not in live_text and "8-run" not in live_text and "8 runs" not in live_text:
        if "4 runs" not in live_text and "4-run" not in live_text:
            errors.append(
                f"experimentDocs/EXPERIMENTS.md should describe live Gemini run count (~{LIVE_EXPECTED_RUNS})"
            )
    if "24 runs" not in mock_text:
        errors.append("experimentDocs/MOCK_EXPERIMENTS.md should mention '24 runs' for mock baseline")
    if "6 runs" not in mock_text and "6 run" not in mock_text:
        errors.append("experimentDocs/MOCK_EXPERIMENTS.md should mention ablation run count")

    if not re.search(r"Last synced", live_text):
        errors.append("experimentDocs/EXPERIMENTS.md missing 'Last synced' line")
    if not re.search(r"Last synced", mock_text):
        errors.append("experimentDocs/MOCK_EXPERIMENTS.md missing 'Last synced' line")

    if "MOCK_EXPERIMENTS.md" not in live_text:
        errors.append("experimentDocs/EXPERIMENTS.md should link to MOCK_EXPERIMENTS.md")
    if "EXPERIMENTS.md" not in mock_text:
        errors.append("experimentDocs/MOCK_EXPERIMENTS.md should link to EXPERIMENTS.md")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync/check experiment documentation")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if manifests or experiment docs are inconsistent",
    )
    args = parser.parse_args()

    try:
        state = collect_state()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    print_state(state)

    if args.check:
        errors = check_docs(state)
        if errors:
            print("\nDoc sync check FAILED:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            print(
                "\nFix: update experimentDocs/EXPERIMENTS.md, experimentDocs/MOCK_EXPERIMENTS.md, "
                "FINDINGS.md, README.md, context/STORE.md",
                file=sys.stderr,
            )
            return 1
        print("\nDoc sync check OK")
    else:
        print("\nRun with --check to validate experiment docs")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
