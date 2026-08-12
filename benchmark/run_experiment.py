"""Run the LexOrchestra mock experiment (reproducible, no API keys required)."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from benchmark.experiment import (
    DEFAULT_CONDITIONS,
    DEFAULT_DOCUMENTS,
    DEFAULT_PROFILES,
    DEFAULT_STRATEGIES,
    run_mock_matrix,
    save_results,
)
from benchmark.answers_validate import assert_all_answers_valid
from benchmark.report import write_report

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS_DIR = REPO_ROOT / "experiments"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run LexOrchestra mock experiment (reproducible baseline)",
    )
    parser.add_argument(
        "--documents",
        nargs="*",
        default=DEFAULT_DOCUMENTS,
        help="Document IDs (default: edgemode + nuscale)",
    )
    parser.add_argument(
        "--conditions",
        nargs="*",
        default=DEFAULT_CONDITIONS,
    )
    parser.add_argument(
        "--strategies",
        nargs="*",
        default=DEFAULT_STRATEGIES,
    )
    parser.add_argument(
        "--profiles",
        nargs="*",
        default=DEFAULT_PROFILES,
        choices=["canonical", "decoy_anchored"],
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=1,
        help="Repeat full matrix N times (non-deterministic seeds after first pass)",
    )
    parser.add_argument(
        "--non-deterministic",
        action="store_true",
        help="Use random seeds instead of fixed DETERMINISTIC_SEEDS",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="JSON output (default: experiments/mock_baseline/results.json)",
    )
    parser.add_argument(
        "--skip-answers-check",
        action="store_true",
        help="Skip answer-key validation before run",
    )
    args = parser.parse_args(argv)

    output_path = args.output or (EXPERIMENTS_DIR / "mock_baseline" / "results.json")
    report_path = output_path.with_name("REPORT.md")
    manifest_path = output_path.with_name("manifest.json")

    print("LexOrchestra mock experiment")
    print(f"  documents: {', '.join(args.documents)}")
    print(f"  conditions: {', '.join(args.conditions)}")
    print(f"  strategies: {', '.join(args.strategies)}")
    print(f"  profiles: {', '.join(args.profiles)}")
    print(f"  deterministic: {not args.non_deterministic}")
    print(f"  output: {output_path}")
    print()

    if not args.skip_answers_check:
        print("Validating benchmark answers against canonical parses...")
        assert_all_answers_valid(args.documents)
        print("  answers OK")
        print()

    results = run_mock_matrix(
        documents=args.documents,
        conditions=args.conditions,
        strategies=args.strategies,
        profiles=args.profiles,
        deterministic=not args.non_deterministic,
        repetitions=args.repetitions,
    )

    save_results(results, output_path)

    meta = {
        "mode": "mock",
        "documents": args.documents,
        "conditions": args.conditions,
        "strategies": args.strategies,
        "profiles": args.profiles,
        "deterministic": not args.non_deterministic,
        "generated": datetime.now(timezone.utc).isoformat(),
    }
    import json

    manifest_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    write_report(output_path, report_path, title="LexOrchestra Mock Baseline", meta=meta)

    print(f"\nResults: {output_path}")
    print(f"Report:  {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
