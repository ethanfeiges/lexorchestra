"""Gemini experiment matrix runner."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from benchmark.answers import list_answer_documents
from benchmark.document_types import primary_fixtures
from benchmark.live_providers import LiveProvider
from orchestrator.run import run_benchmark_case

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "legalDocs" / "contracts" / "public"

DEFAULT_DOCUMENTS = primary_fixtures()
DEFAULT_CONDITIONS = ["clean", "noisy_prompt"]
DEFAULT_STRATEGIES = ["single", "parallel_grounded", "parallel_source_probe"]
DEFAULT_STRATEGY = "parallel_grounded"

# Fixed seeds for reproducible runs (one seed per document × condition pair).
DETERMINISTIC_SEEDS = [
    11_001,
    11_002,
    11_003,
    11_004,
    11_005,
    11_006,
    11_007,
    11_008,
    11_009,
    11_010,
    11_011,
    11_012,
    11_013,
    11_014,
    11_015,
    11_016,
    11_017,
    11_018,
    11_019,
    11_020,
    11_021,
    11_022,
    11_023,
    11_024,
]


def run_gemini_matrix(
    *,
    provider: LiveProvider,
    documents: list[str] | None = None,
    conditions: list[str] | None = None,
    strategies: list[str] | None = None,
    model: str | None = None,
    output_path: Path | None = None,
    continue_on_error: bool = True,
) -> list[dict[str, Any]]:
    """Run the Gemini experiment matrix; returns serializable result rows."""
    docs = documents or DEFAULT_DOCUMENTS
    conds = conditions or DEFAULT_CONDITIONS
    strats = strategies or [DEFAULT_STRATEGY]
    resolved_model = model or provider.default_model
    client_factory = provider.build_factory(resolved_model)
    results_path = output_path or REPO_ROOT / "experiments" / "live_gemini" / "results.json"

    results: list[dict[str, Any]] = []
    run_index = 0

    for doc_id in docs:
        contract_path = FIXTURES / f"{doc_id}.txt"
        if not contract_path.exists():
            print(f"Skip missing fixture: {doc_id}", file=sys.stderr)
            continue

        for condition in conds:
            for strategy in strats:
                seed = DETERMINISTIC_SEEDS[run_index % len(DETERMINISTIC_SEEDS)]
                run_index += 1

                print(
                    f"  {doc_id} | {condition} | {strategy} | "
                    f"{resolved_model} | seed={seed}",
                    flush=True,
                )

                run_kwargs: dict[str, Any] = {}
                if strategy in ("parallel_grounded", "parallel_source_probe"):
                    run_kwargs["extract_models"] = [resolved_model]
                    run_kwargs["playbook_models"] = [resolved_model]

                try:
                    run = run_benchmark_case(
                        contract_path,
                        condition=condition,
                        strategy=strategy,
                        seed=seed,
                        client_factory=client_factory,
                        model=resolved_model,
                        **run_kwargs,
                    )
                except Exception as exc:
                    print(f"    ERROR: {exc}", file=sys.stderr)
                    if not continue_on_error:
                        raise
                    continue

                row = {
                    "run_id": run.run_id,
                    "document_id": run.document_id,
                    "document_type": run.document_type,
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
                save_results(results, results_path)
                m = run.metrics
                print(
                    f"    grounding={m.grounding_rate:.0%} "
                    f"decoy={m.decoy_citation_rate:.0%} "
                    f"accuracy={m.task_accuracy:.0%}",
                    flush=True,
                )

    return results


def save_results(results: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
