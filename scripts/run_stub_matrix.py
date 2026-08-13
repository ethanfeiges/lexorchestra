"""Run full benchmark matrix with canonical stub clients (no API key)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from benchmark.experiment import (
    DEFAULT_CONDITIONS,
    DEFAULT_DOCUMENTS,
    DEFAULT_STRATEGIES,
    count_expected_runs,
)
from benchmark.report import write_report
from benchmark.stub_runner import STUB_PROVIDER, run_stub_matrix

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    conditions = DEFAULT_CONDITIONS + ["portfolio_clean", "cross_type_mislabeled"]
    output_dir = REPO_ROOT / "experiments" / "stub_matrix"
    output_path = output_dir / "results.json"
    report_path = output_dir / "REPORT.md"
    manifest_path = output_dir / "manifest.json"

    run_count = count_expected_runs(DEFAULT_DOCUMENTS, conditions, DEFAULT_STRATEGIES)
    print("LexOrchestra stub matrix (canonical clients, no LLM calls)")
    print(f"  run count: {run_count}")
    print(f"  output: {output_path}")
    print()

    results = run_stub_matrix(
        documents=DEFAULT_DOCUMENTS,
        conditions=conditions,
        strategies=DEFAULT_STRATEGIES,
        output_path=output_path,
    )

    meta = {
        "mode": STUB_PROVIDER.mode,
        "status": "completed" if len(results) >= run_count else "partial",
        "provider": STUB_PROVIDER.name,
        "documents": DEFAULT_DOCUMENTS,
        "conditions": conditions,
        "strategies": DEFAULT_STRATEGIES,
        "model": STUB_PROVIDER.default_model,
        "deterministic": True,
        "seeds": "DETERMINISTIC_SEEDS",
        "generated": datetime.now(timezone.utc).isoformat(),
        "completed_runs": len(results),
        "expected_runs": run_count,
        "notes": "Canonical stub clients; validates pipeline per strategy without Gemini API.",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    write_report(
        output_path,
        report_path,
        title="LexOrchestra Stub Matrix Report",
        meta=meta,
    )

    print(f"\nResults: {output_path}")
    print(f"Report:  {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
