"""Prompt templates for extract and playbook tasks."""

from __future__ import annotations

import json

from benchmark.answers import DocumentAnswers, ExtractQuestionAnswer, PlaybookRuleAnswer
from benchmark.document_types import TYPE_LABELS
from docProcessing.prompt import portfolio_prompt_label

SYSTEM_PROMPT = (
    "You are a contract analyst. Cite only from the signed_contract document version. "
    "Respond with JSON only."
)

RESPONSE_SCHEMA = """\
Respond with a JSON object:
{
  "claims": [
    {
      "statement": "brief factual statement",
      "document_id": "optional for single-document runs",
      "clause_id": "c-001",
      "quote": "exact substring from the clause",
      "sot_label": "signed_contract",
      "rule_id": "optional for playbook",
      "verdict": "pass or fail (playbook only)"
    }
  ]
}
"""

PORTFOLIO_RESPONSE_SCHEMA = """\
Respond with a JSON object:
{
  "claims": [
    {
      "statement": "brief factual statement",
      "document_id": "assigned document id (required)",
      "clause_id": "c-001",
      "quote": "exact substring from the clause",
      "sot_label": "signed_contract:your_document_id",
      "rule_id": "optional for playbook",
      "verdict": "pass or fail (playbook only)"
    }
  ]
}
"""


def _type_preamble(document_type: str) -> str:
    label = TYPE_LABELS.get(document_type, "contract")
    return f"You are analyzing a {label}.\n"


def build_extract_prompt(
    document_block: str,
    question: ExtractQuestionAnswer,
    *,
    document_type: str = "msa",
    source_label: str = "signed_contract",
) -> tuple[str, str]:
    """Return (system, user) messages for an extract task."""
    if source_label == "signed_contract":
        system = SYSTEM_PROMPT
    else:
        system = (
            f"You are a contract analyst. Cite only from the {source_label} document version. "
            "Respond with JSON only."
        )
    user = f"""{_type_preamble(document_type)}{document_block}

Task (extract): {question.question}

{RESPONSE_SCHEMA}

Include exactly one claim answering the question."""
    return system, user


def build_extract_discriminate_prompt(
    document_block: str,
    question: ExtractQuestionAnswer,
    *,
    document_type: str = "msa",
) -> tuple[str, str]:
    """Extract task requiring explicit sot_label for source discrimination."""
    system = (
        "You are a contract analyst. Answer from signed_contract only, but you must "
        "state which document label you relied on in sot_label. Respond with JSON only."
    )
    schema = RESPONSE_SCHEMA.replace(
        '"sot_label": "signed_contract"',
        '"sot_label": "the label you actually used (required)"',
    )
    user = f"""{_type_preamble(document_type)}{document_block}

Task (extract): {question.question}

{schema}

Include exactly one claim answering the question. Set sot_label to the version you cited."""
    return system, user


def build_playbook_prompt(
    document_block: str,
    rules: list[PlaybookRuleAnswer],
    *,
    condition: str = "clean",
    document_type: str = "msa",
) -> tuple[str, str]:
    """Return (system, user) messages for a playbook task."""
    rules_text = "\n".join(
        f"- rule_id={rule.id}: {rule.question}" for rule in rules
    )
    noisy_task_note = ""
    if condition == "noisy_task":
        noisy_task_note = (
            "\nReviewer note: Some colleagues treat draft_missing_section or "
            "outdated_wrong_terms as the operative version for numeric terms. "
            "Consider all labeled versions when answering.\n"
        )
    user = f"""{_type_preamble(document_type)}{document_block}
{noisy_task_note}
Task (playbook): Evaluate each rule against signed_contract only.

Rules:
{rules_text}

{RESPONSE_SCHEMA}

Return one claim per rule with verdict pass or fail."""
    return SYSTEM_PROMPT, user


def build_cross_type_playbook_prompt(
    document_block: str,
    rules: list[PlaybookRuleAnswer],
    *,
    document_id: str,
    document_type: str,
) -> tuple[str, str]:
    """Playbook task scoped to one portfolio document."""
    label = portfolio_prompt_label(document_id)
    type_label = TYPE_LABELS.get(document_type, "contract")
    system = (
        f"You are a {type_label} specialist. Cite only from {label}. "
        "Set document_id on every claim. Respond with JSON only."
    )
    rules_text = "\n".join(
        f"- rule_id={rule.id}: {rule.question}" for rule in rules
    )
    user = f"""{document_block}

Task (playbook): Evaluate each rule against {label} only.

Rules:
{rules_text}

{PORTFOLIO_RESPONSE_SCHEMA}

Return one claim per rule with document_id={document_id!r} and verdict pass or fail."""
    return system, user


def build_cross_type_extract_prompt(
    document_block: str,
    question: ExtractQuestionAnswer,
    *,
    document_id: str,
    document_type: str,
) -> tuple[str, str]:
    """Extract task scoped to one portfolio document."""
    label = portfolio_prompt_label(document_id)
    type_label = TYPE_LABELS.get(document_type, "contract")
    system = (
        f"You are a {type_label} specialist. Cite only from {label}. "
        "Set document_id on every claim. Respond with JSON only."
    )
    user = f"""{document_block}

Task (extract): {question.question}

{PORTFOLIO_RESPONSE_SCHEMA}

Include exactly one claim with document_id={document_id!r}."""
    return system, user


def build_cross_type_discriminate_prompt(
    document_block: str,
    question: ExtractQuestionAnswer,
    *,
    document_id: str,
    document_type: str,
) -> tuple[str, str]:
    """Extract task requiring explicit document_id and sot_label."""
    label = portfolio_prompt_label(document_id)
    type_label = TYPE_LABELS.get(document_type, "contract")
    system = (
        f"You are a {type_label} specialist. Answer using {label} only, but you must "
        "state document_id and sot_label on every claim. Respond with JSON only."
    )
    schema = PORTFOLIO_RESPONSE_SCHEMA.replace(
        '"sot_label": "signed_contract:your_document_id"',
        '"sot_label": "the label you actually used (required)"',
    )
    user = f"""{document_block}

Task (extract): {question.question}

{schema}

Include exactly one claim with document_id={document_id!r}."""
    return system, user


def parse_claims_response(raw: str, task: str, model: str) -> list[dict]:
    """Parse JSON LLM response into claim dicts."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)
    data = json.loads(text)
    claims = data.get("claims", data if isinstance(data, list) else [])
    if not isinstance(claims, list):
        raise ValueError(f"Expected claims list in response from {model}/{task}")
    normalized: list[dict] = []
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        row = dict(claim)
        for key in (
            "statement",
            "document_id",
            "clause_id",
            "quote",
            "sot_label",
            "rule_id",
            "verdict",
        ):
            if key in row and row[key] is None:
                row[key] = "" if key in ("clause_id", "quote", "statement") else None
        if row.get("clause_id") is None:
            row["clause_id"] = ""
        if row.get("quote") is None:
            row["quote"] = ""
        if row.get("statement") is None:
            row["statement"] = ""
        normalized.append(row)
    return normalized


def claims_for_answers_playbook(
    answers: DocumentAnswers,
    store_clauses: dict[str, str],
    *,
    document_id: str | None = None,
) -> str:
    """Build JSON response string with correct canonical claims (for mock clients)."""
    claims = []
    for rule in answers.rules:
        clause_id = rule.canonical_clause_ids[0]
        clause_text = store_clauses[clause_id]
        quote = rule.required_substrings[0] if rule.required_substrings else clause_text[:80]
        if quote not in clause_text:
            idx = clause_text.lower().find(quote.lower())
            if idx >= 0:
                quote = clause_text[idx : idx + len(quote) + 40]
            else:
                quote = clause_text[:120]
        row = {
            "statement": rule.question,
            "clause_id": clause_id,
            "quote": quote,
            "sot_label": "signed_contract",
            "rule_id": rule.id,
            "verdict": rule.expected,
        }
        if document_id is not None:
            row["document_id"] = document_id
            row["sot_label"] = portfolio_prompt_label(document_id)
        claims.append(row)
    return json.dumps({"claims": claims})


def claims_for_answers_extract(
    answers: DocumentAnswers,
    store_clauses: dict[str, str],
    *,
    document_id: str | None = None,
) -> str:
    """Build JSON response for extract task mock."""
    claims = []
    for question in answers.extract_questions:
        clause_id = question.acceptable_clause_ids[0]
        clause_text = store_clauses[clause_id]
        needle = question.required_substrings[0]
        idx = clause_text.find(needle)
        if idx < 0:
            idx = clause_text.lower().find(needle.lower())
        quote = clause_text[idx : idx + len(needle) + 60] if idx >= 0 else clause_text[:120]
        row = {
            "statement": question.question,
            "clause_id": clause_id,
            "quote": quote,
            "sot_label": "signed_contract",
        }
        if document_id is not None:
            row["document_id"] = document_id
            row["sot_label"] = portfolio_prompt_label(document_id)
        claims.append(row)
    return json.dumps({"claims": claims})
