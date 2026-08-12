"""Validate benchmark answers against canonical clause parses."""

from __future__ import annotations

from pathlib import Path

from benchmark.answers import DocumentAnswers, list_answer_documents, load_answers
from docProcessing.io import build_bundle_from_file

FIXTURES = Path(__file__).resolve().parents[1] / "legalDocs" / "contracts" / "public"


def validate_answers(answers: DocumentAnswers, clauses: dict[str, str]) -> list[str]:
    """Return list of validation errors (empty if valid)."""
    errors: list[str] = []

    for rule in answers.rules:
        for clause_id in rule.canonical_clause_ids:
            if clause_id not in clauses:
                errors.append(f"{rule.id}: clause {clause_id} not in canonical parse")
        for needle in rule.required_substrings:
            found = any(needle.lower() in clauses[cid].lower() for cid in rule.canonical_clause_ids if cid in clauses)
            if not found:
                errors.append(
                    f"{rule.id}: required substring {needle!r} not in canonical clauses"
                )

    for question in answers.extract_questions:
        for clause_id in question.acceptable_clause_ids:
            if clause_id not in clauses:
                errors.append(f"{question.id}: clause {clause_id} not in canonical parse")
        for needle in question.required_substrings:
            found = any(
                needle.lower() in clauses[cid].lower()
                for cid in question.acceptable_clause_ids
                if cid in clauses
            )
            if not found:
                errors.append(
                    f"{question.id}: required substring {needle!r} not in acceptable clauses"
                )

    return errors


def validate_all_answers(documents: list[str] | None = None) -> dict[str, list[str]]:
    """Validate answer YAML for each document. Returns doc_id → errors."""
    doc_ids = documents or list_answer_documents()
    report: dict[str, list[str]] = {}
    for doc_id in doc_ids:
        path = FIXTURES / f"{doc_id}.txt"
        if not path.exists():
            report[doc_id] = [f"fixture missing: {path}"]
            continue
        bundle = build_bundle_from_file(path, seed=42)
        clauses = {c.id: c.text for c in bundle.canonical}
        answers = load_answers(doc_id)
        report[doc_id] = validate_answers(answers, clauses)
    return report


def assert_all_answers_valid(documents: list[str] | None = None) -> None:
    report = validate_all_answers(documents)
    failures = {k: v for k, v in report.items() if v}
    if failures:
        lines = [f"{doc}: {errs}" for doc, errs in failures.items()]
        raise AssertionError("Answer validation failed:\n" + "\n".join(lines))
