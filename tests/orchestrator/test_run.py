"""End-to-end orchestrator tests with stub LLM clients."""

import json
from pathlib import Path

from benchmark.answers import load_answers
from models.mock_client import MockModelClient, StaticModelClient
from orchestrator.run import run_benchmark_case
from orchestrator.tasks import claims_for_answers_extract, claims_for_answers_playbook
from docProcessing.io import build_bundle_from_file

PRIMARY = (
    Path(__file__).resolve().parents[2]
    / "legalDocs" / "contracts"
    / "public"
    / "edgar_nuscale_power_corp_ex10.15.txt"
)


def _stub_client_for_document(path: Path) -> MockModelClient:
    bundle = build_bundle_from_file(path, seed=42)
    answers = load_answers(bundle.document_id)
    clauses = {c.id: c.text for c in bundle.canonical}
    return MockModelClient(
        extract_response=claims_for_answers_extract(answers, clauses),
        playbook_response=claims_for_answers_playbook(answers, clauses),
    )


def test_e2e_clean_high_accuracy():
    client = _stub_client_for_document(PRIMARY)
    result = run_benchmark_case(
        PRIMARY,
        condition="clean",
        strategy="single",
        seed=42,
        client=client,
        model="stub",
    )
    assert result.metrics.grounding_rate == 1.0
    assert result.metrics.task_accuracy == 1.0
    assert result.metrics.decoy_citation_rate == 0.0


def test_e2e_noisy_still_correct_with_canonical_stub():
    client = _stub_client_for_document(PRIMARY)
    result = run_benchmark_case(
        PRIMARY,
        condition="noisy_prompt",
        strategy="parallel_grounded",
        seed=42,
        client_factory=lambda _m: client,
        model="stub",
    )
    assert result.metrics.grounding_rate == 1.0
    assert result.metrics.task_accuracy == 1.0
    assert len(result.decoys_in_prompt) >= 1


def test_e2e_decoy_response_fails():
    bundle = build_bundle_from_file(PRIMARY, seed=42)

    bad_playbook = json.dumps(
        {
            "claims": [
                {
                    "statement": "Wrong cap from decoy",
                    "clause_id": "c-007",
                    "quote": "in no event shall be in excess of $5,000,000 in the aggregate",
                    "sot_label": "outdated_wrong_terms",
                    "rule_id": "liability_cap_10m",
                    "verdict": "pass",
                },
                {
                    "statement": "Not mutual",
                    "clause_id": "c-007",
                    "quote": "Indemnity. Fluor shall hold NuScale harmless",
                    "rule_id": "mutual_indemnity",
                    "verdict": "fail",
                },
            ]
        }
    )
    answers = load_answers(bundle.document_id)
    clauses = {c.id: c.text for c in bundle.canonical}
    client = MockModelClient(
        extract_response=claims_for_answers_extract(answers, clauses),
        playbook_response=bad_playbook,
    )
    result = run_benchmark_case(
        PRIMARY,
        condition="noisy_prompt",
        seed=42,
        client=client,
        strategy="single",
        model="stub",
    )
    assert result.metrics.grounding_rate < 1.0
    assert result.metrics.decoy_citation_rate > 0
    assert result.task_scores.get("playbook:liability_cap_10m") is False


def test_fresh_seed_changes_bundle():
    r1 = run_benchmark_case(
        PRIMARY,
        seed=100,
        client=StaticModelClient('{"claims":[]}'),
        strategy="single",
        model="stub",
    )
    r2 = run_benchmark_case(
        PRIMARY,
        seed=200,
        client=StaticModelClient('{"claims":[]}'),
        strategy="single",
        model="stub",
    )
    assert r1.seed != r2.seed


def _decoy_citing_client(path: Path, seed: int) -> MockModelClient:
    """Build a client that cites decoy text (simulates a distracted model)."""
    from benchmark.conditions import build_prompt_context
    from docProcessing.prompt import get_candidate_by_label

    bundle = build_bundle_from_file(path, seed=seed)
    answers = load_answers(bundle.document_id)
    ctx = build_prompt_context(bundle, "noisy_prompt", seed)
    decoy_label = ctx.decoys_in_prompt[0] if ctx.decoys_in_prompt else "outdated_wrong_terms"
    decoy = get_candidate_by_label(bundle, decoy_label)
    assert decoy is not None
    decoy_clauses = {c.id: c.text for c in decoy.clauses}

    extract = claims_for_answers_extract(answers, decoy_clauses)
    raw_extract = json.loads(extract)
    for claim in raw_extract["claims"]:
        claim["sot_label"] = decoy.label
    extract = json.dumps(raw_extract)

    playbook = claims_for_answers_playbook(answers, decoy_clauses)
    raw_playbook = json.loads(playbook)
    for claim in raw_playbook["claims"]:
        claim["sot_label"] = decoy.label
    playbook = json.dumps(raw_playbook)

    return MockModelClient(extract_response=extract, playbook_response=playbook)


def test_verify_false_trusts_decoy_labels():
    client = _decoy_citing_client(PRIMARY, seed=42)
    result = run_benchmark_case(
        PRIMARY,
        condition="noisy_prompt",
        strategy="single",
        seed=42,
        client=client,
        verify=False,
        model="stub",
    )
    assert result.metrics.grounding_rate == 1.0
    assert result.metrics.decoy_citation_rate == 0.0
    assert result.metrics.task_accuracy == 1.0


def test_verify_true_rejects_decoy_labels():
    client = _decoy_citing_client(PRIMARY, seed=42)
    result = run_benchmark_case(
        PRIMARY,
        condition="noisy_prompt",
        strategy="single",
        seed=42,
        client=client,
        verify=True,
        model="stub",
    )
    assert result.metrics.grounding_rate < 1.0
    assert result.metrics.task_accuracy < 1.0
