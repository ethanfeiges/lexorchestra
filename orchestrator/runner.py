"""Async parallel task runner."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from orchestrator.models import Claim, TaskResponse
from orchestrator.tasks import (
    build_extract_prompt,
    build_playbook_prompt,
    parse_claims_response,
)
from benchmark.answers import DocumentAnswers
from models.base import ModelClient


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
    coros: list[asyncio.Task[TaskResponse]] = []

    for model in extract_models:
        system, user = build_extract_prompt(document_block, answers.extract_questions[0])
        client = client_factory(model)
        coros.append(asyncio.create_task(_run_one(client, system, user, "extract", model)))

    for model in playbook_models:
        system, user = build_playbook_prompt(
            document_block, answers.rules, condition=condition
        )
        client = client_factory(model)
        coros.append(asyncio.create_task(_run_one(client, system, user, "playbook", model)))

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
    system, user = build_extract_prompt(document_block, answers.extract_questions[0])
    extract = await _run_one(client, system, user, "extract", model)

    system, user = build_playbook_prompt(document_block, answers.rules, condition=condition)
    playbook = await _run_one(client, system, user, "playbook", model)

    return [extract, playbook]
