"""High-level benchmark case runner."""

from __future__ import annotations

import secrets
from collections.abc import Callable
from pathlib import Path

from benchmark.conditions import build_prompt_context, fresh_seed
from benchmark.answers import load_answers
from benchmark.metrics import build_task_scores, compute_metrics
from grounding.verifier import verify_claims
from models.base import ModelClient
from orchestrator.models import Claim, RunManifest, RunResult, VerifiedClaim
from orchestrator.runner import run_parallel, run_single
from docProcessing.io import build_bundle_from_file
from docProcessing.store import SoTStore


def run_benchmark_case(
    contract_path: Path,
    *,
    condition: str = "noisy_prompt",
    strategy: str = "parallel_grounded",
    seed: int | None = None,
    client_factory: Callable[[str], ModelClient] | None = None,
    client: ModelClient | None = None,
    model: str = "mock",
    verify: bool = True,
    extract_models: list[str] | None = None,
    playbook_models: list[str] | None = None,
) -> RunResult:
    """Run one orchestration benchmark case synchronously."""
    import asyncio

    return asyncio.run(
        run_benchmark_case_async(
            contract_path,
            condition=condition,
            strategy=strategy,
            seed=seed,
            client_factory=client_factory,
            client=client,
            model=model,
            verify=verify,
            extract_models=extract_models,
            playbook_models=playbook_models,
        )
    )


async def run_benchmark_case_async(
    contract_path: Path,
    *,
    condition: str = "noisy_prompt",
    strategy: str = "parallel_grounded",
    seed: int | None = None,
    client_factory: Callable[[str], ModelClient] | None = None,
    client: ModelClient | None = None,
    model: str = "mock",
    verify: bool = True,
    extract_models: list[str] | None = None,
    playbook_models: list[str] | None = None,
) -> RunResult:
    """Async entry point for one benchmark case."""
    run_seed = seed if seed is not None else fresh_seed()
    bundle = build_bundle_from_file(contract_path, seed=run_seed)
    answers = load_answers(bundle.document_id)
    store = SoTStore(bundle.canonical, bundle.document_id)

    prompt_ctx = build_prompt_context(bundle, condition, run_seed)
    decoys = prompt_ctx.decoys_in_prompt
    document_block = prompt_ctx.document_block

    ext_models = extract_models or [model]
    pb_models = playbook_models or [model]

    manifest = RunManifest(
        document_id=bundle.document_id,
        seed=run_seed,
        decoys_in_prompt=decoys,
        condition=condition,
        strategy=strategy,
        models={"extract": ext_models, "playbook": pb_models},
    )

    if client_factory is None:
        if client is None:
            raise ValueError("Provide client_factory or client")
        client_factory = lambda _m: client  # noqa: E731

    if strategy == "single":
        single_model = ext_models[0]
        task_responses = await run_single(
            client=client_factory(single_model),
            model=single_model,
            document_block=document_block,
            answers=answers,
            condition=condition,
        )
    else:
        task_responses = await run_parallel(
            client_factory=client_factory,
            document_block=document_block,
            answers=answers,
            extract_models=ext_models,
            playbook_models=pb_models,
            condition=condition,
        )

    verified: list[VerifiedClaim] = []
    if verify:
        for response in task_responses:
            verified.extend(
                verify_claims(
                    response.claims,
                    store,
                    model=response.model,
                    task=response.task,
                    bundle=bundle,
                )
            )
        task_scores = build_task_scores(verified, answers)
        metrics = compute_metrics(verified, task_scores)
    else:
        for response in task_responses:
            for claim in response.claims:
                verified.append(
                    VerifiedClaim(
                        claim=claim,
                        status="grounded",
                        model=response.model,
                        task=response.task,
                        decoy_match=None,
                    )
                )
        task_scores = build_task_scores(verified, answers, naive=True)
        metrics = compute_metrics(verified, task_scores, trust_model_labels=True)

    return RunResult(
        run_id=manifest.run_id,
        document_id=bundle.document_id,
        condition=condition,
        strategy=strategy,
        seed=run_seed,
        decoys_in_prompt=decoys,
        verified_claims=verified,
        task_scores=task_scores,
        metrics=metrics,
    )


def make_run_seed() -> int:
    """Generate a fresh random seed for eval runs."""
    return secrets.randbelow(2**31)
