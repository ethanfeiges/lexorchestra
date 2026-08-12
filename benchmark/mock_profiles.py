"""Mock agent profiles for reproducible experiments without live LLMs."""

from __future__ import annotations

import json
from pathlib import Path

from benchmark.answers import DocumentAnswers, load_answers
from models.mock_client import MockModelClient
from docProcessing.io import build_bundle_from_file
from docProcessing.models import SoTBundle, SoTCandidate
from docProcessing.prompt import get_candidate_by_label

from orchestrator.tasks import claims_for_answers_extract, claims_for_answers_playbook

MOCK_PROFILES = ("canonical", "decoy_anchored")

DECOY_PRIORITY = [
    "outdated_wrong_terms",
    "draft_missing_section",
    "bad_parse_extra_clause",
    "bad_parse_wrong_ids",
]


def _pick_decoy_candidate(
    bundle: SoTBundle, decoy_labels: list[str]
) -> SoTCandidate | None:
    for label in DECOY_PRIORITY:
        if label in decoy_labels:
            candidate = get_candidate_by_label(bundle, label)
            if candidate is not None:
                return candidate
    return None


def _clause_map(candidate: SoTCandidate) -> dict[str, str]:
    return {c.id: c.text for c in candidate.clauses}


def claims_for_decoy_playbook(
    bundle: SoTBundle,
    answers: DocumentAnswers,
    decoy_labels: list[str],
) -> str:
    """Build playbook claims anchored on a decoy version (simulates model failure)."""
    decoy = _pick_decoy_candidate(bundle, decoy_labels)
    if decoy is None:
        return claims_for_answers_playbook(answers, {c.id: c.text for c in bundle.canonical})

    decoy_clauses = _clause_map(decoy)
    claims = []
    for rule in answers.rules:
        clause_id = rule.canonical_clause_ids[0]
        if clause_id not in decoy_clauses:
            clause_id = next(iter(decoy_clauses), clause_id)
        text = decoy_clauses.get(clause_id, "")
        quote = text[:160] if text else "not found in document"
        if rule.required_substrings:
            for needle in rule.required_substrings:
                if needle.lower() in text.lower():
                    idx = text.lower().find(needle.lower())
                    quote = text[idx : idx + len(needle) + 40]
                    break
        claims.append(
            {
                "statement": rule.question,
                "clause_id": clause_id,
                "quote": quote,
                "sot_label": decoy.label,
                "rule_id": rule.id,
                "verdict": rule.expected,
            }
        )
    return json.dumps({"claims": claims})


def claims_for_decoy_extract(
    bundle: SoTBundle,
    answers: DocumentAnswers,
    decoy_labels: list[str],
) -> str:
    """Build extract claims anchored on a decoy version."""
    decoy = _pick_decoy_candidate(bundle, decoy_labels)
    if decoy is None:
        return claims_for_answers_extract(answers, {c.id: c.text for c in bundle.canonical})

    decoy_clauses = _clause_map(decoy)
    claims = []
    for question in answers.extract_questions:
        clause_id = question.acceptable_clause_ids[0]
        if clause_id not in decoy_clauses:
            clause_id = next(iter(decoy_clauses), clause_id)
        text = decoy_clauses.get(clause_id, "")
        quote = text[:160] if text else ""
        claims.append(
            {
                "statement": question.question,
                "clause_id": clause_id,
                "quote": quote,
                "sot_label": decoy.label,
            }
        )
    return json.dumps({"claims": claims})


def build_mock_client(
    *,
    profile: str,
    contract_path: str | Path,
    document_id: str,
    seed: int,
    decoys_in_prompt: list[str],
) -> MockModelClient:
    """Build a mock client for one run using the given profile and run seed."""
    path = Path(contract_path)
    bundle = build_bundle_from_file(path, seed=seed)
    answers = load_answers(document_id)
    canonical = {c.id: c.text for c in bundle.canonical}

    if profile == "canonical":
        extract = claims_for_answers_extract(answers, canonical)
        playbook = claims_for_answers_playbook(answers, canonical)
    elif profile == "decoy_anchored":
        extract = claims_for_decoy_extract(bundle, answers, decoys_in_prompt)
        playbook = claims_for_decoy_playbook(bundle, answers, decoys_in_prompt)
    else:
        raise ValueError(f"Unknown mock profile: {profile}")

    return MockModelClient(extract_response=extract, playbook_response=playbook)
