"""Tests for mock agent profiles."""

from pathlib import Path

from benchmark.conditions import build_prompt_context
from benchmark.mock_profiles import build_mock_client, claims_for_decoy_playbook
from benchmark.answers import load_answers
from docProcessing.io import build_bundle_from_file

PRIMARY = (
    Path(__file__).resolve().parents[2]
    / "legalDocs" / "contracts"
    / "public"
    / "edgar_nuscale_power_corp_ex10.15.txt"
)


def test_decoy_playbook_differs_from_canonical():
    bundle = build_bundle_from_file(PRIMARY, seed=42)
    answers = load_answers(bundle.document_id)
    ctx = build_prompt_context(bundle, "noisy_prompt", 42)
    decoy_json = claims_for_decoy_playbook(bundle, answers, ctx.decoys_in_prompt)
    assert "outdated_wrong_terms" in decoy_json or "draft_missing_section" in decoy_json


def test_decoy_anchored_client_under_noisy():
    bundle = build_bundle_from_file(PRIMARY, seed=42)
    ctx = build_prompt_context(bundle, "noisy_prompt", 42)
    client = build_mock_client(
        profile="decoy_anchored",
        contract_path=PRIMARY,
        document_id=bundle.document_id,
        seed=42,
        decoys_in_prompt=ctx.decoys_in_prompt,
    )
    import asyncio

    raw = asyncio.run(client.complete("sys", "Task (playbook): x"))
    assert "signed_contract" not in raw or "outdated_wrong_terms" in raw
