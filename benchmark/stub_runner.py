"""Run the full benchmark matrix with canonical stub clients (no LLM calls)."""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from benchmark.answers import load_answers
from benchmark.document_types import primary_fixtures
from benchmark.experiment import (
    DEFAULT_CONDITIONS,
    DEFAULT_STRATEGIES,
    DETERMINISTIC_SEEDS,
    PORTFOLIO_CONDITIONS,
    PORTFOLIO_STRATEGIES,
    _print_metrics,
    _result_row,
    save_results,
)
from benchmark.live_providers import LiveProvider
from docProcessing.io import build_bundle_from_file
from models.base import ModelClient
from models.mock_client import CallableModelClient, MockModelClient
from orchestrator.portfolio_run import run_portfolio_benchmark_case
from orchestrator.run import run_benchmark_case
from orchestrator.tasks import claims_for_answers_extract, claims_for_answers_playbook

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "legalDocs" / "contracts" / "public"

def _unused_factory(_model: str) -> Callable[[str], ModelClient]:
    raise NotImplementedError("stub matrix builds clients per document")


STUB_PROVIDER = LiveProvider(
    name="stub",
    default_model="canonical-stub",
    experiments_dir="stub_matrix",
    mode="stub_matrix",
    env_keys=(),
    factory_builder=_unused_factory,
)


def _doc_stub_client(doc_id: str, seed: int) -> MockModelClient:
    bundle = build_bundle_from_file(FIXTURES / f"{doc_id}.txt", seed=seed)
    answers = load_answers(doc_id)
    clauses = {c.id: c.text for c in bundle.canonical}
    return MockModelClient(
        extract_response=claims_for_answers_extract(answers, clauses),
        playbook_response=claims_for_answers_playbook(answers, clauses),
    )


def _portfolio_stub_client(seed: int) -> CallableModelClient:
    doc_ids = primary_fixtures()
    bundles = {
        doc_id: build_bundle_from_file(FIXTURES / f"{doc_id}.txt", seed=seed)
        for doc_id in doc_ids
    }
    answers = {doc_id: load_answers(doc_id) for doc_id in doc_ids}

    def _complete(_system: str, user: str) -> str:
        match = re.search(r"document_id='([^']+)'", user)
        if not match:
            match = re.search(r'document_id="([^"]+)"', user)
        if not match:
            raise ValueError(f"Could not parse document_id from prompt: {user[:200]}")
        doc_id = match.group(1)
        clauses = {c.id: c.text for c in bundles[doc_id].canonical}
        if "Task (playbook)" in user:
            return claims_for_answers_playbook(
                answers[doc_id],
                clauses,
                document_id=doc_id,
            )
        return claims_for_answers_extract(
            answers[doc_id],
            clauses,
            document_id=doc_id,
        )

    return CallableModelClient(_complete)


def run_stub_matrix(
    *,
    documents: list[str] | None = None,
    conditions: list[str] | None = None,
    strategies: list[str] | None = None,
    output_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Execute the full matrix with canonical stub clients."""
    docs = documents or primary_fixtures()
    conds = conditions or DEFAULT_CONDITIONS + PORTFOLIO_CONDITIONS
    strats = strategies or list(DEFAULT_STRATEGIES)
    results_path = output_path or REPO_ROOT / "experiments" / "stub_matrix" / "results.json"
    provider = STUB_PROVIDER
    model = provider.default_model

    results: list[dict[str, Any]] = []
    run_index = 0
    portfolio_strats = [s for s in strats if s in PORTFOLIO_STRATEGIES]
    doc_strats = [s for s in strats if s not in PORTFOLIO_STRATEGIES]
    portfolio_client = _portfolio_stub_client(seed=42)

    for condition in conds:
        for strategy in portfolio_strats:
            if condition not in PORTFOLIO_CONDITIONS:
                continue
            seed = DETERMINISTIC_SEEDS[run_index % len(DETERMINISTIC_SEEDS)]
            run_index += 1
            print(
                f"  portfolio:primary_five | {condition} | {strategy} | "
                f"{model} | seed={seed}",
                flush=True,
            )
            run = run_portfolio_benchmark_case(
                condition=condition,
                strategy=strategy,
                seed=seed,
                client=portfolio_client,
                model=model,
            )
            row = _result_row(run, provider, model)
            results.append(row)
            save_results(results, results_path)
            _print_metrics(run.metrics)

    for doc_id in docs:
        contract_path = FIXTURES / f"{doc_id}.txt"
        if not contract_path.exists():
            print(f"Skip missing fixture: {doc_id}", file=sys.stderr)
            continue

        for condition in conds:
            if condition in PORTFOLIO_CONDITIONS:
                continue
            for strategy in doc_strats:
                seed = DETERMINISTIC_SEEDS[run_index % len(DETERMINISTIC_SEEDS)]
                run_index += 1
                client = _doc_stub_client(doc_id, seed)
                client_factory: Callable[[str], ModelClient] = lambda _m, c=client: c

                print(
                    f"  {doc_id} | {condition} | {strategy} | "
                    f"{model} | seed={seed}",
                    flush=True,
                )

                run_kwargs: dict[str, Any] = {}
                if strategy in ("parallel_grounded", "parallel_source_probe"):
                    run_kwargs["extract_models"] = [model]
                    run_kwargs["playbook_models"] = [model]

                run = run_benchmark_case(
                    contract_path,
                    condition=condition,
                    strategy=strategy,
                    seed=seed,
                    client_factory=client_factory,
                    model=model,
                    **run_kwargs,
                )
                row = _result_row(run, provider, model)
                results.append(row)
                save_results(results, results_path)
                _print_metrics(run.metrics)

    return results
