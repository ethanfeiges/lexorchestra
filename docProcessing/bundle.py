"""Generate SoT bundles with deterministic invalid candidates."""

from __future__ import annotations

import copy
import hashlib
import random
from typing import Callable

from docProcessing.corruption_plan import (
    CorruptionMode,
    DocumentCorruptionPlan,
    apply_span_edit,
    pick_span_edit,
    resolve_corruption_plan,
)
from docProcessing.models import Clause, SoTBundle, SoTCandidate

CORRUPTION_LABELS: dict[str, str] = {
    "missing_clause": "draft_missing_section",
    "altered_text": "outdated_wrong_terms",
    "extra_clause": "bad_parse_extra_clause",
    "reordered": "bad_parse_wrong_ids",
}

DEFAULT_CORRUPTIONS = list(CORRUPTION_LABELS.keys())


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


def _clause_index_by_id(clauses: list[Clause], clause_id: str) -> int | None:
    for i, clause in enumerate(clauses):
        if clause.id == clause_id:
            return i
    return None


def _target_index(
    clauses: list[Clause],
    document_type: str,
    rng: random.Random,
    plan: DocumentCorruptionPlan,
) -> int:
    if plan.missing_clause_ids:
        for clause_id in plan.missing_clause_ids:
            idx = _clause_index_by_id(clauses, clause_id)
            if idx is not None:
                return idx
    finder = CORRUPTION_TARGETS.get(document_type, _find_liability_clause_indices)
    return rng.choice(finder(clauses))


def corrupt_missing_clause(
    clauses: list[Clause],
    rng: random.Random,
    *,
    document_type: str = "msa",
    plan: DocumentCorruptionPlan,
) -> list[Clause]:
    if len(clauses) <= 1:
        return _renumber_sequential(clauses[:0])

    idx = _target_index(clauses, document_type, rng, plan)
    remaining = [c for i, c in enumerate(clauses) if i != idx]
    return _renumber_sequential(remaining)


def corrupt_altered_text(
    clauses: list[Clause],
    rng: random.Random,
    *,
    document_type: str = "msa",
    plan: DocumentCorruptionPlan,
) -> list[Clause]:
    edit = pick_span_edit(plan, clauses, rng)
    if edit is not None:
        return apply_span_edit(clauses, edit)

    idx = _target_index(clauses, document_type, rng, plan)
    result = copy.deepcopy(clauses)
    result[idx] = Clause(
        id=result[idx].id,
        text=result[idx].text + " (as amended)",
        start_offset=result[idx].start_offset,
        end_offset=result[idx].end_offset,
    )
    return result


def corrupt_extra_clause(
    clauses: list[Clause],
    rng: random.Random,
    *,
    plan: DocumentCorruptionPlan,
) -> list[Clause]:
    result = copy.deepcopy(clauses)
    spec = plan.extra_clause
    if spec is None:
        insert_at = rng.randint(0, len(result))
        fake_text = "Miscellaneous. The parties agree to amend this Agreement upon mutual consent."
    else:
        insert_at = min(spec.insert_index, len(result))
        fake_text = spec.text

    prev_end = result[insert_at - 1].end_offset if insert_at > 0 else 0
    next_start = result[insert_at].start_offset if insert_at < len(result) else prev_end
    fake_clause = Clause(
        id=_format_clause_id(insert_at + 1),
        text=fake_text,
        start_offset=prev_end,
        end_offset=next_start if next_start > prev_end else prev_end + len(fake_text),
    )
    result.insert(insert_at, fake_clause)
    return _renumber_sequential(result)


def corrupt_reordered(clauses: list[Clause], rng: random.Random) -> list[Clause]:
    texts = [c.text for c in clauses]
    indices = list(range(len(clauses)))
    rng.shuffle(indices)
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
    *,
    corruption_mode: CorruptionMode = "local",
    use_corruption_cache: bool = True,
) -> SoTBundle:
    """Build an SoT bundle with signed_contract plus seeded decoy candidates."""
    active_corruptions = corruptions if corruptions is not None else DEFAULT_CORRUPTIONS
    canonical = copy.deepcopy(clauses)
    plan = resolve_corruption_plan(
        canonical,
        document_id,
        seed,
        mode=corruption_mode,
        use_cache=use_corruption_cache,
    )

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
        rng = _corruption_rng(seed, corruption)
        if corruption == "reordered":
            corrupted_clauses = handler(canonical, rng)
        elif corruption in ("missing_clause", "altered_text"):
            corrupted_clauses = handler(
                canonical,
                rng,
                document_type=document_type,
                plan=plan,
            )
        else:
            corrupted_clauses = handler(canonical, rng, plan=plan)
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
