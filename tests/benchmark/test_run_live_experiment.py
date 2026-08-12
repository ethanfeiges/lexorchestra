"""Tests for live LLM experiment CLI."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from benchmark.live_providers import get_provider
from benchmark.run_live_experiment import DEFAULT_LIVE_STRATEGY, LIVE_DOCUMENTS, main
from models.gemini_client import (
    DEFAULT_GEMINI_MODEL,
    GeminiClient,
    build_gemini_client_factory,
    resolve_gemini_api_key,
)
from orchestrator.tasks import parse_claims_response


def test_gemini_provider_exits_when_missing_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    provider = get_provider("gemini")
    with pytest.raises(SystemExit) as exc:
        provider.require_api_key()
    assert exc.value.code == 2


def test_main_exits_2_without_gemini_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with patch("benchmark.run_live_experiment.load_dotenv_if_present"):
        with pytest.raises(SystemExit) as exc:
            main([])
    assert exc.value.code == 2


def test_main_parses_gemini_args_and_runs_matrix(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    output = tmp_path / "results.json"
    provider = get_provider("gemini")

    fake_results = [
        {
            "run_id": "r1",
            "document_id": LIVE_DOCUMENTS[0],
            "condition": "clean",
            "strategy": DEFAULT_LIVE_STRATEGY,
            "provider": "gemini",
            "model": "gemini-2.5-flash",
            "seed": 11001,
            "decoys_in_prompt": [],
            "metrics": {
                "grounding_rate": 1.0,
                "decoy_citation_rate": 0.0,
                "task_accuracy": 1.0,
            },
            "task_scores": {},
        }
    ]

    with patch("benchmark.run_live_experiment.run_live_matrix", return_value=fake_results) as mock_run:
        with patch("benchmark.run_live_experiment.assert_all_answers_valid"):
            code = main(
                [
                    "--documents",
                    LIVE_DOCUMENTS[0],
                    "--conditions",
                    "clean",
                    "--model",
                    "gemini-2.5-flash",
                    "--output",
                    str(output),
                    "--skip-answers-check",
                ]
            )

    assert code == 0
    mock_run.assert_called_once()
    assert mock_run.call_args.kwargs["provider"].name == "gemini"
    assert mock_run.call_args.kwargs["model"] == "gemini-2.5-flash"
    manifest = json.loads(output.with_name("manifest.json").read_text(encoding="utf-8"))
    assert manifest["mode"] == "live_gemini"
    assert manifest["provider"] == "gemini"
    assert manifest["model"] == "gemini-2.5-flash"


def test_build_gemini_client_factory_returns_gemini_client():
    factory = build_gemini_client_factory(default_model=DEFAULT_GEMINI_MODEL)
    client = factory("gemini-2.5-pro")
    assert isinstance(client, GeminiClient)
    assert client.model == "gemini-2.5-pro"


def test_resolve_gemini_api_key_prefers_gemini_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    assert resolve_gemini_api_key() == "gemini-key"


def test_resolve_gemini_api_key_falls_back_to_google_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    assert resolve_gemini_api_key() == "google-key"


def test_parse_claims_response_handles_json_object_shape():
    raw = json.dumps(
        {
            "claims": [
                {
                    "statement": "Cap is $10M",
                    "clause_id": "c-007",
                    "quote": "aggregate liability shall not exceed $10,000,000",
                    "sot_label": "signed_contract",
                    "rule_id": "liability_cap_10m",
                    "verdict": "pass",
                }
            ]
        }
    )
    claims = parse_claims_response(raw, "playbook", "gemini-2.5-flash")
    assert len(claims) == 1
    assert claims[0]["clause_id"] == "c-007"


def test_live_documents_includes_new_msas():
    assert "edgar_aspira_women_s_health_inc_ex10.1" in LIVE_DOCUMENTS
    assert "edgar_pulmatrix_inc_ex10.6" in LIVE_DOCUMENTS
    assert "edgar_chime_financial_inc_ex10.1" not in LIVE_DOCUMENTS
    assert len(LIVE_DOCUMENTS) == 4
