"""Reproducible experiment matrix runner (mock-first)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from benchmark.conditions import build_prompt_context, fresh_seed
from benchmark.mock_profiles import MOCK_PROFILES, build_mock_client
from orchestrator.run import run_benchmark_case

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "legalDocs" / "contracts" / "public"

DEFAULT_DOCUMENTS = [
    "edgar_edgemode_inc_ex10.1",
    "edgar_nuscale_power_corp_ex10.15",
    "edgar_chime_financial_inc_ex10.1",
]

DEFAULT_CONDITIONS = ["clean", "noisy_prompt"]
DEFAULT_STRATEGIES = ["single", "parallel_grounded"]
DEFAULT_PROFILES = ["canonical", "decoy_anchored"]

# Fixed seeds for --deterministic runs (reproducible on any machine).
# 3 docs × 2 profiles × 2 conditions × 2 strategies = 24 runs.
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


def _model_lists(strategy: str) -> tuple[list[str], list[str]]:
    if strategy == "single":
        return ["mock-a"], ["mock-a"]
    return ["mock-a", "mock-b"], ["mock-a", "mock-b"]


def _pick_seed(deterministic: bool, run_index: int) -> int:
    if deterministic:
        return DETERMINISTIC_SEEDS[run_index % len(DETERMINISTIC_SEEDS)]
    return fresh_seed()


def run_mock_matrix(
    *,
    documents: list[str] | None = None,
    conditions: list[str] | None = None,
    strategies: list[str] | None = None,
    profiles: list[str] | None = None,
    deterministic: bool = True,
    repetitions: int = 1,
) -> list[dict[str, Any]]:
    """Run full mock experiment matrix; returns serializable result rows."""
    docs = documents or DEFAULT_DOCUMENTS
    conds = conditions or DEFAULT_CONDITIONS
    strats = strategies or DEFAULT_STRATEGIES
    profs = profiles or DEFAULT_PROFILES

    results: list[dict[str, Any]] = []
    run_index = 0

    for doc_id in docs:
        contract_path = FIXTURES / f"{doc_id}.txt"
        if not contract_path.exists():
            print(f"Skip missing fixture: {doc_id}", file=sys.stderr)
            continue

        for profile in profs:
            if profile not in MOCK_PROFILES:
                raise ValueError(f"Unknown mock profile: {profile}")

            for condition in conds:
                for strategy in strats:
                    for _rep in range(repetitions):
                        seed = _pick_seed(deterministic, run_index)
                        run_index += 1

                        # Build decoys list for decoy_anchored client before run
                        from docProcessing.io import build_bundle_from_file

                        bundle = build_bundle_from_file(contract_path, seed=seed)
                        ctx = build_prompt_context(bundle, condition, seed)

                        client = build_mock_client(
                            profile=profile,
                            contract_path=contract_path,
                            document_id=doc_id,
                            seed=seed,
                            decoys_in_prompt=ctx.decoys_in_prompt,
                        )
                        ext, pb = _model_lists(strategy)

                        print(
                            f"  {doc_id} | {condition} | {strategy} | "
                            f"{profile} | seed={seed}",
                            flush=True,
                        )

                        run = run_benchmark_case(
                            contract_path,
                            condition=condition,
                            strategy=strategy,
                            seed=seed,
                            client=client,
                            extract_models=ext,
                            playbook_models=pb,
                        )
                        row = {
                            "run_id": run.run_id,
                            "document_id": run.document_id,
                            "condition": run.condition,
                            "strategy": run.strategy,
                            "mock_profile": profile,
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


def save_results(results: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
