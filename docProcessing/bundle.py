"""Generate SoT bundles with deterministic invalid candidates."""

from __future__ import annotations

import copy
import hashlib
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
    ("$1,000,000", "$750,000"),
    ("$1M", "$500K"),
    ("$1M", "$750K"),
    ("$500,000", "$250,000"),
    ("$500,000", "$750,000"),
    (" thirty (30) ", " fifteen (15) "),
    (" thirty (30) ", " forty-five (45) "),
    (" sixty (60) ", " thirty (30) "),
    (" sixty (60) ", " forty-five (45) "),
    (" ninety (90) ", " forty-five (45) "),
    (" ninety (90) ", " one hundred twenty (120) "),
    ("12 months", "6 months"),
    ("12 months", "18 months"),
    ("24 months", "12 months"),
    ("24 months", "36 months"),
    ("30 days", "15 days"),
    ("30 days", "45 days"),
    ("60 days", "30 days"),
    ("60 days", "90 days"),
    ("binding arbitration", "non-binding mediation"),
    ("exclusive jurisdiction", "non-exclusive jurisdiction"),
    ("shall not disclose", "may disclose"),
    ("without limitation", "subject to the limitations set forth herein"),
]

NUMERIC_FACTORS: tuple[float, ...] = (0.5, 0.75, 1.25, 1.5, 2.0)

TEXT_SUFFIXES: tuple[str, ...] = (
    " [REVISED]",
    " (as amended)",
    " — see Schedule A",
)

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
    (
        "Assignment. Neither party may assign this Agreement without the prior written "
        "consent of the other party, except in connection with a merger or sale of "
        "substantially all of its assets."
    ),
    (
        "Notices. All notices under this Agreement shall be in writing and delivered "
        "by certified mail, overnight courier, or email to the addresses set forth on "
        "the signature page."
    ),
    (
        "Survival. The provisions of Sections relating to confidentiality, indemnification, "
        "limitation of liability, and governing law shall survive termination or expiration "
        "of this Agreement."
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


def _find_liability_clause_indices(clauses: list[Clause]) -> list[int]:
    indices = [i for i, c in enumerate(clauses) if "liability" in c.text.lower()]
    return indices or [len(clauses) // 2]


def _find_license_clause_indices(clauses: list[Clause]) -> list[int]:
    indices = [
        i
        for i, c in enumerate(clauses)
        if "license" in c.text.lower()
        and ("grant" in c.text.lower() or "licenses to" in c.text.lower())
    ]
    return indices or [len(clauses) // 2]


def _find_confidentiality_clause_indices(clauses: list[Clause]) -> list[int]:
    indices = [
        i
        for i, c in enumerate(clauses)
        if "confidential" in c.text.lower()
        and (
            "term" in c.text.lower()
            or "disclosure" in c.text.lower()
            or "information" in c.text.lower()
        )
    ]
    return indices or [len(clauses) // 2]


def _find_employment_terms_clause_indices(clauses: list[Clause]) -> list[int]:
    indices = [
        i
        for i, c in enumerate(clauses)
        if "confidential" in c.text.lower()
        or "non-compete" in c.text.lower()
        or "not to disclose" in c.text.lower()
    ]
    return indices or [len(clauses) // 2]


def _find_credit_terms_clause_indices(clauses: list[Clause]) -> list[int]:
    indices = [
        i
        for i, c in enumerate(clauses)
        if "credit" in c.text.lower()
        or "revolving" in c.text.lower()
        or "interest" in c.text.lower()
        or "governing law" in c.text.lower()
    ]
    return indices or [len(clauses) // 2]


CORRUPTION_TARGETS: dict[str, Callable[[list[Clause]], list[int]]] = {
    "msa": _find_liability_clause_indices,
    "software_license": _find_license_clause_indices,
    "nda": _find_confidentiality_clause_indices,
    "employment": _find_employment_terms_clause_indices,
    "credit": _find_credit_terms_clause_indices,
}


def _corruption_rng(seed: int, corruption: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{corruption}".encode()).digest()
    return random.Random(int.from_bytes(digest[:4], "big"))


def _target_index(clauses: list[Clause], document_type: str, rng: random.Random) -> int:
    finder = CORRUPTION_TARGETS.get(document_type, _find_liability_clause_indices)
    return rng.choice(finder(clauses))


def _apply_substitution(text: str, rng: random.Random) -> str:
    applicable = [pair for pair in SUBSTITUTIONS if pair[0] in text]
    if applicable:
        old, new = rng.choice(applicable)
        return text.replace(old, new, 1)

    numbers = list(re.finditer(r"\$[\d,]+(?:\.\d+)?|\b\d+\b", text))
    if numbers:
        match = rng.choice(numbers)
        old_val = match.group()
        factor = rng.choice(NUMERIC_FACTORS)
        if old_val.startswith("$"):
            digits = re.sub(r"[^\d]", "", old_val)
            if digits:
                new_num = str(max(1, int(int(digits) * factor)))
                new_val = f"${int(new_num):,}" if "," in old_val else f"${new_num}"
                return text[: match.start()] + new_val + text[match.end() :]
        else:
            new_val = str(max(1, int(int(old_val) * factor)))
            return text[: match.start()] + new_val + text[match.end() :]

    return text + rng.choice(TEXT_SUFFIXES)


def corrupt_missing_clause(
    clauses: list[Clause],
    rng: random.Random,
    *,
    document_type: str = "msa",
) -> list[Clause]:
    if len(clauses) <= 1:
        return _renumber_sequential(clauses[:0])

    idx = _target_index(clauses, document_type, rng)
    remaining = [c for i, c in enumerate(clauses) if i != idx]
    return _renumber_sequential(remaining)


def corrupt_altered_text(
    clauses: list[Clause],
    rng: random.Random,
    *,
    document_type: str = "msa",
) -> list[Clause]:
    idx = _target_index(clauses, document_type)
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


CORRUPTION_HANDLERS: dict[str, Callable[..., list[Clause]]] = {
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
    document_type: str = "msa",
) -> SoTBundle:
    """Build an SoT bundle with signed_contract plus deterministic decoy candidates."""
    active_corruptions = corruptions if corruptions is not None else DEFAULT_CORRUPTIONS
    canonical = copy.deepcopy(clauses)

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
        if corruption in ("missing_clause", "altered_text"):
            corrupted_clauses = handler(
                canonical,
                random.Random(seed),
                document_type=document_type,
            )
        else:
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
