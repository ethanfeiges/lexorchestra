"""Async parallel task runner."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from orchestrator.models import Claim, TaskResponse
from orchestrator.tasks import (
    build_extract_discriminate_prompt,
    build_extract_prompt,
    build_playbook_prompt,
    parse_claims_response,
)
from benchmark.answers import DocumentAnswers
from models.base import ModelClient

CANONICAL_TASKS = frozenset({"extract", "playbook"})


async def _run_one(
    client: ModelClient,
    system: str,
    user: str,
    task: str,
    model: str,
) -> TaskResponse:
    raw = await client.complete(system, user)
    claim_dicts = parse_claims_response(raw, task, model)
    claims = [Claim.model_validate(c) for c in claim_dicts]
    return TaskResponse(task=task, model=model, claims=claims)


async def run_parallel(
    *,
    client_factory: Callable[[str], ModelClient],
    document_block: str,
    answers: DocumentAnswers,
    extract_models: list[str],
    playbook_models: list[str],
    condition: str = "clean",
) -> list[TaskResponse]:
    """Run extract and playbook tasks across assigned models in parallel."""
    doc_type = answers.document_type
    coros: list[asyncio.Task[TaskResponse]] = []

    for model in extract_models:
        system, user = build_extract_prompt(
            document_block,
            answers.extract_questions[0],
            document_type=doc_type,
        )
        client = client_factory(model)
        coros.append(asyncio.create_task(_run_one(client, system, user, "extract", model)))

    for model in playbook_models:
        system, user = build_playbook_prompt(
            document_block,
            answers.rules,
            condition=condition,
            document_type=doc_type,
        )
        client = client_factory(model)
        coros.append(asyncio.create_task(_run_one(client, system, user, "playbook", model)))

    return list(await asyncio.gather(*coros))


async def run_parallel_source_probe(
    *,
    client_factory: Callable[[str], ModelClient],
    document_block: str,
    answers: DocumentAnswers,
    extract_models: list[str],
    playbook_models: list[str],
    condition: str = "clean",
    decoy_label: str | None = None,
) -> list[TaskResponse]:
    """Run canonical tasks plus decoy and discrimination probes in parallel."""
    doc_type = answers.document_type
    probe_decoy = decoy_label or "outdated_wrong_terms"
    coros: list[asyncio.Task[TaskResponse]] = []

    for model in extract_models:
        system, user = build_extract_prompt(
            document_block,
            answers.extract_questions[0],
            document_type=doc_type,
        )
        client = client_factory(model)
        coros.append(asyncio.create_task(_run_one(client, system, user, "extract", model)))

    for model in playbook_models:
        system, user = build_playbook_prompt(
            document_block,
            answers.rules,
            condition=condition,
            document_type=doc_type,
        )
        client = client_factory(model)
        coros.append(asyncio.create_task(_run_one(client, system, user, "playbook", model)))

    for model in extract_models:
        system, user = build_extract_prompt(
            document_block,
            answers.extract_questions[0],
            document_type=doc_type,
            source_label=probe_decoy,
        )
        client = client_factory(model)
        coros.append(
            asyncio.create_task(_run_one(client, system, user, "extract_decoy", model))
        )

    for model in extract_models:
        system, user = build_extract_discriminate_prompt(
            document_block,
            answers.extract_questions[0],
            document_type=doc_type,
        )
        client = client_factory(model)
        coros.append(
            asyncio.create_task(
                _run_one(client, system, user, "extract_discriminate", model)
            )
        )

    return list(await asyncio.gather(*coros))


async def run_single(
    *,
    client: ModelClient,
    model: str,
    document_block: str,
    answers: DocumentAnswers,
    condition: str = "clean",
) -> list[TaskResponse]:
    """Run extract then playbook sequentially with one model."""
    doc_type = answers.document_type
    system, user = build_extract_prompt(
        document_block,
        answers.extract_questions[0],
        document_type=doc_type,
    )
    extract = await _run_one(client, system, user, "extract", model)

    system, user = build_playbook_prompt(
        document_block,
        answers.rules,
        condition=condition,
        document_type=doc_type,
    )
    playbook = await _run_one(client, system, user, "playbook", model)

    return [extract, playbook]
