"""End-to-end portfolio (cross-type) orchestration tests."""

import json
import re

from benchmark.answers import load_answers
from benchmark.portfolio import build_portfolio_context
from docProcessing.io import build_bundle_from_file
from models.mock_client import CallableModelClient
from orchestrator.portfolio_run import run_portfolio_benchmark_case
from orchestrator.tasks import claims_for_answers_extract, claims_for_answers_playbook

TWO_DOC_IDS = [
    "edgar_edgemode_inc_ex10.1",
    "edgar_amd_ex10.79",
]
FIXTURES = (
    __import__("pathlib").Path(__file__).resolve().parents[2]
    / "legalDocs"
    / "contracts"
    / "public"
)


def _portfolio_stub_client(seed: int = 42) -> CallableModelClient:
    """Route portfolio prompts to canonical claims for the assigned document."""
    bundles = {
        doc_id: build_bundle_from_file(FIXTURES / f"{doc_id}.txt", seed=seed)
        for doc_id in TWO_DOC_IDS
    }
    answers = {doc_id: load_answers(doc_id) for doc_id in TWO_DOC_IDS}

    def _complete(_system: str, user: str) -> str:
        match = re.search(r"document_id='([^']+)'", user)
        if not match:
            match = re.search(r'document_id="([^"]+)"', user)
        assert match is not None, f"Could not parse document_id from prompt: {user[:200]}"
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


def test_portfolio_clean_high_accuracy():
    client = _portfolio_stub_client()
    result = run_portfolio_benchmark_case(
        condition="portfolio_clean",
        seed=42,
        client=client,
        model="stub",
        document_ids=TWO_DOC_IDS,
    )
    assert result.document_id == "portfolio:primary_five"
    assert result.metrics.grounding_rate == 1.0
    assert result.metrics.task_accuracy == 1.0
    assert result.metrics.cross_document_citation_rate == 0.0
    assert result.metrics.source_fidelity == 1.0
    tasks = {v.task for v in result.verified_claims}
    assert any(t.startswith("playbook:") for t in tasks)
    assert any(t.startswith("extract_discriminate:") for t in tasks)


def test_portfolio_cross_document_citation_detected():
    ctx = build_portfolio_context(
        document_ids=TWO_DOC_IDS,
        condition="portfolio_clean",
        seed=42,
    )
    target = ctx.documents[0]
    other = ctx.documents[1]
    other_clause = other.bundle.canonical[0]

    def _cross_doc(_system: str, user: str) -> str:
        match = re.search(r"document_id='([^']+)'", user)
        doc_id = match.group(1) if match else target.document_id
        if doc_id == target.document_id and "Task (extract)" in user:
            payload = {
                "claims": [
                    {
                        "statement": "Cited other document",
                        "document_id": other.document_id,
                        "clause_id": other_clause.id,
                        "quote": other_clause.text[:80],
                        "sot_label": f"signed_contract:{other.document_id}",
                    }
                ]
            }
            return json.dumps(payload)
        clauses = {c.id: c.text for c in target.bundle.canonical}
        return claims_for_answers_extract(
            target.answers,
            clauses,
            document_id=target.document_id,
        )

    result = run_portfolio_benchmark_case(
        condition="portfolio_clean",
        seed=42,
        client=CallableModelClient(_cross_doc),
        model="stub",
        document_ids=TWO_DOC_IDS,
    )
    cross = [v for v in result.verified_claims if v.cross_document_match is not None]
    assert cross
    assert any(v.cross_document_match == other.document_id for v in cross)
