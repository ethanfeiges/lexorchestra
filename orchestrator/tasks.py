"""Prompt templates for extract and playbook tasks."""

from __future__ import annotations

import json

from benchmark.answers import DocumentAnswers, ExtractQuestionAnswer, PlaybookRuleAnswer

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
      "clause_id": "c-001",
      "quote": "exact substring from the clause",
      "sot_label": "signed_contract",
      "rule_id": "optional for playbook",
      "verdict": "pass or fail (playbook only)"
    }
  ]
}
"""


def build_extract_prompt(
    document_block: str,
    question: ExtractQuestionAnswer,
) -> tuple[str, str]:
    """Return (system, user) messages for an extract task."""
    user = f"""{document_block}

Task (extract): {question.question}

{RESPONSE_SCHEMA}

Include exactly one claim answering the question."""
    return SYSTEM_PROMPT, user


def build_playbook_prompt(
    document_block: str,
    rules: list[PlaybookRuleAnswer],
    *,
    condition: str = "clean",
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
    user = f"""{document_block}
{noisy_task_note}
Task (playbook): Evaluate each rule against signed_contract only.

Rules:
{rules_text}

{RESPONSE_SCHEMA}

Return one claim per rule with verdict pass or fail."""
    return SYSTEM_PROMPT, user


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
        for key in ("statement", "clause_id", "quote", "sot_label", "rule_id", "verdict"):
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
        claims.append(
            {
                "statement": rule.question,
                "clause_id": clause_id,
                "quote": quote,
                "sot_label": "signed_contract",
                "rule_id": rule.id,
                "verdict": rule.expected,
            }
        )
    return json.dumps({"claims": claims})


def claims_for_answers_extract(
    answers: DocumentAnswers,
    store_clauses: dict[str, str],
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
        claims.append(
            {
                "statement": question.question,
                "clause_id": clause_id,
                "quote": quote,
                "sot_label": "signed_contract",
            }
        )
    return json.dumps({"claims": claims})
