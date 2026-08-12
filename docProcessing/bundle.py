"""Generate SoT bundles with deterministic invalid candidates."""

from __future__ import annotations

import copy
import random
import re
from typing import Callable

from docProcessing.models import Clause, SoTBundle, SoTCandidate

CORRUPTION_LABELS: dict[str, str] = {
    "missing_clause": "draft_missing_section",
    "altered_text": "outdated_wrong_terms",
    "extra_clause": "bad_parse_extra_clause",
    "reordered": "bad_parse_wrong_ids",
}

DEFAULT_CORRUPTIONS = list(CORRUPTION_LABELS.keys())

SUBSTITUTIONS: list[tuple[str, str]] = [
    ("$1,000,000", "$500,000"),
    ("$1M", "$500K"),
    ("$500,000", "$250,000"),
    (" thirty (30) ", " fifteen (15) "),
    (" sixty (60) ", " thirty (30) "),
    (" ninety (90) ", " forty-five (45) "),
    ("12 months", "6 months"),
    ("24 months", "12 months"),
    ("30 days", "15 days"),
    ("60 days", "30 days"),
]

FAKE_CLAUSE_TEMPLATES: list[str] = [
    (
        "Miscellaneous. The parties agree that any dispute arising under this Agreement "
        "shall be resolved through binding arbitration in accordance with the rules of "
        "the American Arbitration Association. The prevailing party shall be entitled to "
        "recover reasonable attorneys' fees and costs."
    ),
    (
        "Force Majeure. Neither party shall be liable for any failure or delay in "
        "performance due to causes beyond its reasonable control, including acts of God, "
        "war, terrorism, or government action, for a period of ninety (90) days."
    ),
    (
        "Audit Rights. The customer may audit the vendor's records once per calendar year "
        "upon thirty (30) days written notice, during normal business hours, subject to "
        "confidentiality obligations."
    ),
]


def _format_clause_id(index: int) -> str:
    return f"c-{index:03d}"


def _renumber_sequential(clauses: list[Clause]) -> list[Clause]:
    return [
        Clause(
            id=_format_clause_id(i + 1),
            text=c.text,
            start_offset=c.start_offset,
            end_offset=c.end_offset,
        )
        for i, c in enumerate(clauses)
    ]


def _find_liability_clause_index(clauses: list[Clause]) -> int:
    for i, clause in enumerate(clauses):
        if "liability" in clause.text.lower():
            return i
    return len(clauses) // 2


def _apply_substitution(text: str, rng: random.Random) -> str:
    applicable = [pair for pair in SUBSTITUTIONS if pair[0] in text]
    if applicable:
        old, new = rng.choice(applicable)
        return text.replace(old, new, 1)

    numbers = list(re.finditer(r"\$[\d,]+(?:\.\d+)?|\b\d+\b", text))
    if numbers:
        match = rng.choice(numbers)
        old_val = match.group()
        if old_val.startswith("$"):
            digits = re.sub(r"[^\d]", "", old_val)
            if digits:
                new_num = str(max(1, int(digits) // 2))
                new_val = f"${int(new_num):,}" if "," in old_val else f"${new_num}"
                return text[: match.start()] + new_val + text[match.end() :]
        else:
            new_val = str(max(1, int(old_val) // 2))
            return text[: match.start()] + new_val + text[match.end() :]

    return text + " [REVISED]"


def corrupt_missing_clause(clauses: list[Clause], rng: random.Random) -> list[Clause]:
    if len(clauses) <= 1:
        return _renumber_sequential(clauses[:0])

    idx = _find_liability_clause_index(clauses)
    remaining = [c for i, c in enumerate(clauses) if i != idx]
    return _renumber_sequential(remaining)


def corrupt_altered_text(clauses: list[Clause], rng: random.Random) -> list[Clause]:
    idx = _find_liability_clause_index(clauses)
    result = copy.deepcopy(clauses)
    result[idx] = Clause(
        id=result[idx].id,
        text=_apply_substitution(result[idx].text, rng),
        start_offset=result[idx].start_offset,
        end_offset=result[idx].end_offset,
    )
    return result


def corrupt_extra_clause(clauses: list[Clause], rng: random.Random) -> list[Clause]:
    result = copy.deepcopy(clauses)
    next_id = _format_clause_id(len(result) + 1)
    last_end = result[-1].end_offset if result else 0
    fake_text = rng.choice(FAKE_CLAUSE_TEMPLATES)
    result.append(
        Clause(
            id=next_id,
            text=fake_text,
            start_offset=last_end,
            end_offset=last_end + len(fake_text),
        )
    )
    return result


def corrupt_reordered(clauses: list[Clause], rng: random.Random) -> list[Clause]:
    texts = [c.text for c in clauses]
    indices = list(range(len(clauses)))
    rng.shuffle(indices)
    # Ensure order actually changes when possible
    if len(clauses) > 1 and indices == list(range(len(clauses))):
        indices[0], indices[1] = indices[1], indices[0]

    shuffled_texts = [texts[i] for i in indices]
    return _renumber_sequential(
        [
            Clause(
                id=_format_clause_id(i + 1),
                text=text,
                start_offset=clauses[0].start_offset if clauses else 0,
                end_offset=clauses[-1].end_offset if clauses else 0,
            )
            for i, text in enumerate(shuffled_texts)
        ]
    )


CORRUPTION_HANDLERS: dict[str, Callable[[list[Clause], random.Random], list[Clause]]] = {
    "missing_clause": corrupt_missing_clause,
    "altered_text": corrupt_altered_text,
    "extra_clause": corrupt_extra_clause,
    "reordered": corrupt_reordered,
}


def build_bundle(
    clauses: list[Clause],
    document_id: str,
    source_path: str,
    seed: int = 42,
    corruptions: list[str] | None = None,
) -> SoTBundle:
    """Build an SoT bundle with signed_contract plus deterministic decoy candidates."""
    active_corruptions = corruptions if corruptions is not None else DEFAULT_CORRUPTIONS
    canonical = copy.deepcopy(clauses)
    rng = random.Random(seed)

    signed = SoTCandidate(
        label="signed_contract",
        valid=True,
        clauses=copy.deepcopy(canonical),
        corruption=None,
    )

    candidates: list[SoTCandidate] = [signed]

    for corruption in active_corruptions:
        if corruption not in CORRUPTION_HANDLERS:
            raise ValueError(f"Unknown corruption type: {corruption}")
        handler = CORRUPTION_HANDLERS[corruption]
        corrupted_clauses = handler(canonical, random.Random(seed))
        candidates.append(
            SoTCandidate(
                label=CORRUPTION_LABELS[corruption],
                valid=False,
                clauses=corrupted_clauses,
                corruption=corruption,
            )
        )

    return SoTBundle(
        document_id=document_id,
        source_path=source_path,
        canonical=canonical,
        candidates=candidates,
    )
