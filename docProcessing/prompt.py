"""Format SoT candidates as text for LLM prompts."""

from __future__ import annotations

from docProcessing.models import SoTBundle, SoTCandidate

HEADER = "Document versions (cite from signed_contract only):"
UNLABELED_HEADER = "Document versions (labels are arbitrary):"
# Live LLM runs need enough text for answer-relevant quotes (e.g. ICC at ~7k in c-007).
MAX_CLAUSE_LENGTH = 12_000


def _truncate(text: str, max_len: int = MAX_CLAUSE_LENGTH) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def format_candidates_for_prompt(
    candidates: list[SoTCandidate],
    labels: list[str] | None = None,
    *,
    header: str | None = None,
    label_aliases: dict[str, str] | None = None,
) -> str:
    """Convert structured candidates into a single text block for LLM prompts."""
    if labels is not None:
        label_set = set(labels)
        filtered = [c for c in candidates if c.label in label_set]
    else:
        filtered = candidates

    lines: list[str] = [header or HEADER, ""]

    for candidate in filtered:
        display_label = (
            label_aliases.get(candidate.label, candidate.label)
            if label_aliases
            else candidate.label
        )
        for clause in candidate.clauses:
            text = _truncate(clause.text.replace("\n", " "))
            lines.append(f"[{display_label}] {clause.id}: {text}")

    return "\n".join(lines)


def get_candidate_by_label(bundle: SoTBundle, label: str) -> SoTCandidate | None:
    for candidate in bundle.candidates:
        if candidate.label == label:
            return candidate
    return None


def portfolio_prompt_label(document_id: str) -> str:
    """Prompt label for a document's signed canonical block."""
    return f"signed_contract:{document_id}"


def signed_contract_candidate(bundle: SoTBundle) -> SoTCandidate:
    candidate = get_candidate_by_label(bundle, "signed_contract")
    if candidate is None:
        raise ValueError("Bundle has no signed_contract candidate")
    return candidate
