"""Portfolio (cross-type) benchmark runner."""

from __future__ import annotations

import secrets
from collections.abc import Callable

from benchmark.conditions import fresh_seed
from benchmark.metrics import build_portfolio_task_scores, compute_portfolio_metrics
from benchmark.portfolio import PortfolioContext, build_portfolio_context
from grounding.verifier import verify_portfolio_claims
from models.base import ModelClient
from orchestrator.models import RunManifest, RunResult, VerifiedClaim
from orchestrator.runner import run_parallel_cross_type_discrimination


async def run_portfolio_benchmark_case_async(
    *,
    case_id: str = "primary_five",
    condition: str = "portfolio_clean",
    strategy: str = "parallel_cross_type_discrimination",
    seed: int | None = None,
    client_factory: Callable[[str], ModelClient] | None = None,
    client: ModelClient | None = None,
    model: str = "mock",
    verify: bool = True,
    models: list[str] | None = None,
    document_ids: list[str] | None = None,
) -> RunResult:
    """Run a multi-document cross-type portfolio benchmark case."""
    run_seed = seed if seed is not None else fresh_seed()
    portfolio = build_portfolio_context(
        case_id=case_id,
        condition=condition,
        seed=run_seed,
        document_ids=document_ids,
    )
    document_block = portfolio.document_block
    assigned_models = models or [model]

    manifest = RunManifest(
        document_id=f"portfolio:{portfolio.portfolio_id}",
        seed=run_seed,
        decoys_in_prompt=[f"{a}->{b}" for a, b in portfolio.mislabeled],
        condition=condition,
        strategy=strategy,
        models={"portfolio": assigned_models},
    )

    if client_factory is None:
        if client is None:
            raise ValueError("Provide client_factory or client")
        client_factory = lambda _m: client  # noqa: E731

    if strategy != "parallel_cross_type_discrimination":
        raise ValueError(f"Unsupported portfolio strategy: {strategy}")

    task_responses = await run_parallel_cross_type_discrimination(
        client_factory=client_factory,
        document_block=document_block,
        documents=list(portfolio.documents),
        models=assigned_models,
    )

    stores = {entry.document_id: entry.store for entry in portfolio.documents}
    bundles = {entry.document_id: entry.bundle for entry in portfolio.documents}
    answers_by_doc = {entry.document_id: entry.answers for entry in portfolio.documents}

    verified: list[VerifiedClaim] = []
    if verify:
        for response in task_responses:
            parts = response.task.split(":", 1)
            if len(parts) != 2:
                continue
            kind, doc_id = parts[0], parts[1]
            if doc_id not in stores:
                continue
            verified.extend(
                verify_portfolio_claims(
                    response.claims,
                    stores[doc_id],
                    expected_document_id=doc_id,
                    model=response.model,
                    task=response.task,
                    bundle=bundles[doc_id],
                    all_stores=stores,
                )
            )
        task_scores = build_portfolio_task_scores(verified, answers_by_doc)
        metrics = compute_portfolio_metrics(verified, task_scores)
    else:
        for response in task_responses:
            parts = response.task.split(":", 1)
            doc_id = parts[1] if len(parts) == 2 else portfolio.documents[0].document_id
            for claim in response.claims:
                verified.append(
                    VerifiedClaim(
                        claim=claim,
                        status="grounded",
                        model=response.model,
                        task=response.task,
                        expected_document_id=doc_id,
                    )
                )
        task_scores = build_portfolio_task_scores(
            verified,
            answers_by_doc,
            naive=True,
        )
        metrics = compute_portfolio_metrics(
            verified,
            task_scores,
            trust_model_labels=True,
        )

    return RunResult(
        run_id=manifest.run_id,
        document_id=manifest.document_id,
        document_type="portfolio",
        condition=condition,
        strategy=strategy,
        seed=run_seed,
        decoys_in_prompt=manifest.decoys_in_prompt,
        verified_claims=verified,
        task_scores=task_scores,
        metrics=metrics,
    )


def run_portfolio_benchmark_case(
    *,
    case_id: str = "primary_five",
    condition: str = "portfolio_clean",
    strategy: str = "parallel_cross_type_discrimination",
    seed: int | None = None,
    client_factory: Callable[[str], ModelClient] | None = None,
    client: ModelClient | None = None,
    model: str = "mock",
    verify: bool = True,
    models: list[str] | None = None,
    document_ids: list[str] | None = None,
) -> RunResult:
    """Synchronous portfolio benchmark entry point."""
    import asyncio

    return asyncio.run(
        run_portfolio_benchmark_case_async(
            case_id=case_id,
            condition=condition,
            strategy=strategy,
            seed=seed,
            client_factory=client_factory,
            client=client,
            model=model,
            verify=verify,
            models=models,
            document_ids=document_ids,
        )
    )


def make_portfolio_seed() -> int:
    return secrets.randbelow(2**31)
