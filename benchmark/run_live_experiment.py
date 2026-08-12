"""Run LexOrchestra live LLM baseline (small matrix, requires API key)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmark.experiment import DETERMINISTIC_SEEDS, save_results
from benchmark.answers import list_answer_documents
from benchmark.answers_validate import assert_all_answers_valid
from benchmark.live_providers import PROVIDERS, REPO_ROOT, LiveProvider, get_provider
from benchmark.report import write_report
from orchestrator.run import run_benchmark_case

FIXTURES = REPO_ROOT / "legalDocs" / "contracts" / "public"

from models.gemini_client import LIVE_DOCUMENTS_EXCLUDE

# MSAs with answer keys, excluding oversized fixtures for default live runs.
LIVE_DOCUMENTS = [
    doc_id for doc_id in list_answer_documents() if doc_id not in LIVE_DOCUMENTS_EXCLUDE
]
LIVE_CONDITIONS = ["clean", "noisy_prompt"]
DEFAULT_LIVE_STRATEGY = "parallel_grounded"


def load_dotenv_if_present() -> None:
    """Load .env into os.environ without overriding existing variables."""
    env_path = REPO_ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def run_live_matrix(
    *,
    provider: LiveProvider,
    documents: list[str] | None = None,
    conditions: list[str] | None = None,
    model: str | None = None,
    strategy: str = DEFAULT_LIVE_STRATEGY,
) -> list[dict[str, Any]]:
    """Run a small live LLM matrix; returns serializable result rows."""
    docs = documents or LIVE_DOCUMENTS
    conds = conditions or LIVE_CONDITIONS
    resolved_model = model or provider.default_model
    client_factory = provider.build_factory(resolved_model)

    results: list[dict[str, Any]] = []
    run_index = 0

    for doc_id in docs:
        contract_path = FIXTURES / f"{doc_id}.txt"
        if not contract_path.exists():
            print(f"Skip missing fixture: {doc_id}", file=sys.stderr)
            continue

        for condition in conds:
            seed = DETERMINISTIC_SEEDS[run_index % len(DETERMINISTIC_SEEDS)]
            run_index += 1

            print(
                f"  {doc_id} | {condition} | {strategy} | "
                f"{resolved_model} | seed={seed}",
                flush=True,
            )

            run_kwargs: dict[str, Any] = {}
            if strategy == "parallel_grounded":
                # Use the live model for both subtasks (not mock-a/mock-b placeholders).
                run_kwargs["extract_models"] = [resolved_model]
                run_kwargs["playbook_models"] = [resolved_model]

            run = run_benchmark_case(
                contract_path,
                condition=condition,
                strategy=strategy,
                seed=seed,
                client_factory=client_factory,
                model=resolved_model,
                **run_kwargs,
            )
            row = {
                "run_id": run.run_id,
                "document_id": run.document_id,
                "condition": run.condition,
                "strategy": run.strategy,
                "provider": provider.name,
                "model": resolved_model,
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
        description="Run LexOrchestra live LLM baseline (small matrix)",
    )
    parser.add_argument(
        "--provider",
        choices=sorted(PROVIDERS),
        default="gemini",
        help="LLM provider (default: gemini)",
    )
    parser.add_argument(
        "--documents",
        nargs="*",
        default=LIVE_DOCUMENTS,
        help="Document IDs (default: edgemode + nuscale)",
    )
    parser.add_argument(
        "--conditions",
        nargs="*",
        default=LIVE_CONDITIONS,
        help="Prompt conditions (default: clean noisy_prompt)",
    )
    parser.add_argument(
        "--include-chime",
        action="store_true",
        help="Include Chime MSA (184 clauses; may hit Gemini token quotas)",
    )
    parser.add_argument(
        "--strategy",
        choices=["single", "parallel_grounded"],
        default=DEFAULT_LIVE_STRATEGY,
        help=(
            "single = one model runs extract then playbook; "
            "parallel_grounded = separate subtasks in parallel (default)"
        ),
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model id (default: provider-specific, e.g. gemini-2.5-pro)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="JSON output (default: experiments/live_<provider>/results.json)",
    )
    parser.add_argument(
        "--skip-answers-check",
        action="store_true",
        help="Skip answer-key validation before run",
    )
    args = parser.parse_args(argv)

    load_dotenv_if_present()
    provider = get_provider(args.provider)
    provider.require_api_key()

    documents = list(args.documents)
    if args.include_chime and "edgar_chime_financial_inc_ex10.1" not in documents:
        documents.append("edgar_chime_financial_inc_ex10.1")
    documents = sorted(set(documents))

    resolved_model = args.model or provider.default_model
    output_path = args.output or (provider.output_dir() / "results.json")
    report_path = output_path.with_name("REPORT.md")
    manifest_path = output_path.with_name("manifest.json")

    print(f"LexOrchestra live {provider.name} baseline")
    print(f"  documents: {', '.join(documents)}")
    print(f"  conditions: {', '.join(args.conditions)}")
    print(f"  strategy: {args.strategy}")
    print(f"  provider: {provider.name}")
    print(f"  model: {resolved_model}")
    print(f"  run count: {len(documents) * len(args.conditions)}")
    print(f"  output: {output_path}")
    print()

    if not args.skip_answers_check:
        print("Validating benchmark answers against canonical parses...")
        assert_all_answers_valid(documents)
        print("  answers OK")
        print()

    results = run_live_matrix(
        provider=provider,
        documents=documents,
        conditions=args.conditions,
        model=resolved_model,
        strategy=args.strategy,
    )

    save_results(results, output_path)

    meta = {
        "mode": provider.mode,
        "status": "completed",
        "provider": provider.name,
        "documents": documents,
        "conditions": args.conditions,
        "strategy": args.strategy,
        "model": resolved_model,
        "deterministic": True,
        "seeds": "DETERMINISTIC_SEEDS",
        "generated": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    write_report(
        output_path,
        report_path,
        title=f"LexOrchestra Live {provider.name.title()} Baseline",
        meta=meta,
    )

    print(f"\nResults: {output_path}")
    print(f"Report:  {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
