"""Run focused ablation experiments (mock-only, no API keys)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmark.conditions import build_prompt_context
from benchmark.experiment import DETERMINISTIC_SEEDS, save_results
from benchmark.answers_validate import assert_all_answers_valid
from benchmark.mock_profiles import build_mock_client
from benchmark.report import write_report
from orchestrator.run import run_benchmark_case
from docProcessing.io import build_bundle_from_file

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "legalDocs" / "contracts" / "public"
EXPERIMENTS_DIR = REPO_ROOT / "experiments"

ABLATION_DOCUMENTS = [
    "edgar_edgemode_inc_ex10.1",
    "edgar_nuscale_power_corp_ex10.15",
]

ABLATION_MATRIX = [
    {
        "ablation": "full_pipeline",
        "profile": "decoy_anchored",
        "condition": "noisy_prompt",
        "verify": True,
    },
    {
        "ablation": "no_verifier",
        "profile": "decoy_anchored",
        "condition": "noisy_prompt",
        "verify": False,
    },
    {
        "ablation": "unlabeled",
        "profile": "decoy_anchored",
        "condition": "unlabeled_noisy",
        "verify": True,
    },
]


def run_ablation_matrix(
    *,
    documents: list[str] | None = None,
    strategy: str = "single",
    deterministic: bool = True,
) -> list[dict[str, Any]]:
    """Run the focused ablation matrix; returns serializable result rows."""
    docs = documents or ABLATION_DOCUMENTS
    results: list[dict[str, Any]] = []
    run_index = 0

    for cfg in ABLATION_MATRIX:
        for doc_id in docs:
            contract_path = FIXTURES / f"{doc_id}.txt"
            if not contract_path.exists():
                print(f"Skip missing fixture: {doc_id}", file=sys.stderr)
                continue

            seed = (
                DETERMINISTIC_SEEDS[run_index % len(DETERMINISTIC_SEEDS)]
                if deterministic
                else run_index + 42_000
            )
            run_index += 1

            bundle = build_bundle_from_file(contract_path, seed=seed)
            ctx = build_prompt_context(bundle, cfg["condition"], seed)
            client = build_mock_client(
                profile=cfg["profile"],
                contract_path=contract_path,
                document_id=doc_id,
                seed=seed,
                decoys_in_prompt=ctx.decoys_in_prompt,
            )

            print(
                f"  {cfg['ablation']} | {doc_id} | seed={seed}",
                flush=True,
            )

            run = run_benchmark_case(
                contract_path,
                condition=cfg["condition"],
                strategy=strategy,
                seed=seed,
                client=client,
                verify=cfg["verify"],
            )
            row = {
                "run_id": run.run_id,
                "document_id": run.document_id,
                "condition": run.condition,
                "strategy": run.strategy,
                "mock_profile": cfg["profile"],
                "ablation": cfg["ablation"],
                "verify": cfg["verify"],
                "seed": run.seed,
                "decoys_in_prompt": run.decoys_in_prompt,
                "metrics": run.metrics.model_dump(),
                "task_scores": run.task_scores,
            }
            results.append(row)
            m = run.metrics
            print(
                f"    grounding={m.grounding_rate:.0%} "
                f"decoy={m.decoy_citation_rate:.0%} "
                f"accuracy={m.task_accuracy:.0%}",
                flush=True,
            )

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run LexOrchestra ablation experiments (mock-only)",
    )
    parser.add_argument(
        "--documents",
        nargs="*",
        default=ABLATION_DOCUMENTS,
    )
    parser.add_argument(
        "--strategy",
        default="single",
    )
    parser.add_argument(
        "--non-deterministic",
        action="store_true",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="JSON output (default: experiments/ablations/results.json)",
    )
    parser.add_argument(
        "--skip-answers-check",
        action="store_true",
    )
    args = parser.parse_args(argv)

    output_path = args.output or (EXPERIMENTS_DIR / "ablations" / "results.json")
    report_path = output_path.with_name("REPORT.md")
    manifest_path = output_path.with_name("manifest.json")

    print("LexOrchestra ablation experiment")
    print(f"  documents: {', '.join(args.documents)}")
    print(f"  strategy: {args.strategy}")
    print(f"  ablations: {', '.join(a['ablation'] for a in ABLATION_MATRIX)}")
    print(f"  output: {output_path}")
    print()

    if not args.skip_answers_check:
        print("Validating benchmark answers against canonical parses...")
        assert_all_answers_valid(args.documents)
        print("  answers OK")
        print()

    results = run_ablation_matrix(
        documents=args.documents,
        strategy=args.strategy,
        deterministic=not args.non_deterministic,
    )

    save_results(results, output_path)

    meta = {
        "mode": "mock_ablation",
        "documents": args.documents,
        "strategy": args.strategy,
        "ablations": [a["ablation"] for a in ABLATION_MATRIX],
        "deterministic": not args.non_deterministic,
        "generated": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    write_report(
        output_path,
        report_path,
        title="LexOrchestra Ablation Report",
        meta=meta,
    )

    print(f"\nResults: {output_path}")
    print(f"Report:  {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
