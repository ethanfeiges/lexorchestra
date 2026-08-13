"""Document-specific corruption plans for decoy bundle generation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from docProcessing.models import Clause

CorruptionMode = Literal["local", "gemini", "auto"]

DEFAULT_CACHE_DIR = (
    Path(__file__).resolve().parents[1] / "legalDocs" / "corruption_plans"
)

CATEGORIES = (
    "money",
    "duration",
    "percentage",
    "date",
    "obligation",
    "jurisdiction",
    "rate",
)

MONEY_PATTERN = re.compile(
    r"(?:\$|€|£)\s*[\d,]+(?:\.\d{1,2})?"
    r"|[\d,]+(?:\.\d{2})?\s*(?:USD|EUR|GBP|dollars?|Euros?)"
    r"|\b(?:one|two|three|four|five|ten|twenty|thirty|forty|fifty|sixty|"
    r"seventy|eighty|ninety|one hundred)\s+(?:million|thousand|hundred)\b",
    re.IGNORECASE,
)
DURATION_PATTERN = re.compile(
    r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|"
    r"ninety|one hundred(?:\s+twenty)?)\s*(?:\(\s*\d+\s*\))?\s*"
    r"(?:calendar\s+)?(?:days?|months?|years?|hours?|weeks?|Working Days?)\b",
    re.IGNORECASE,
)
PERCENTAGE_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*%\s*(?:\([^)]*\))?"
    r"|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|"
    r"ninety|one hundred)\s+per\s+cent\b",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(
    r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+)?"
    r"(?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+\d{1,2},?\s+\d{4}\b"
    r"|\b\d{4}-\d{2}-\d{2}\b",
    re.IGNORECASE,
)
OBLIGATION_PATTERN = re.compile(
    r"\b(?:shall not|shall|must not|must|may not|may|will not|will)\b",
    re.IGNORECASE,
)
JURISDICTION_PATTERN = re.compile(
    r"\blaws of (?:the )?[A-Z][a-z]+(?: [A-Z][a-z]+)*\b"
    r"|\b(?:Florida|Nevada|California|New York|Delaware|Texas|United Kingdom|"
    r"England and Wales|Norway)\b(?: courts?)?",
    re.IGNORECASE,
)
RATE_PATTERN = re.compile(
    r"\$\s*[\d,]+(?:\.\d{1,2})?\s*/\s*(?:hour|month|year|KW hour|kWh)\b",
    re.IGNORECASE,
)

PATTERN_BY_CATEGORY: dict[str, re.Pattern[str]] = {
    "money": MONEY_PATTERN,
    "duration": DURATION_PATTERN,
    "percentage": PERCENTAGE_PATTERN,
    "date": DATE_PATTERN,
    "obligation": OBLIGATION_PATTERN,
    "jurisdiction": JURISDICTION_PATTERN,
    "rate": RATE_PATTERN,
}

LOCAL_FACTORS: tuple[float, ...] = (0.5, 0.67, 0.75, 1.25, 1.33, 1.5, 2.0)


class SpanEdit(BaseModel):
    clause_id: str
    category: str
    original: str
    replacement: str


class ExtraClauseSpec(BaseModel):
    text: str
    insert_index: int = Field(ge=0)


class DocumentCorruptionPlan(BaseModel):
    document_id: str
    seed: int
    content_hash: str
    mode: CorruptionMode
    span_edits: list[SpanEdit] = Field(default_factory=list)
    missing_clause_ids: list[str] = Field(default_factory=list)
    extra_clause: ExtraClauseSpec | None = None


def content_hash(clauses: list[Clause]) -> str:
    joined = "\n".join(c.text for c in clauses)
    return hashlib.sha256(joined.encode()).hexdigest()[:16]


def _cache_path(
    cache_dir: Path,
    document_id: str,
    seed: int,
    digest: str,
) -> Path:
    return cache_dir / f"{document_id}_seed{seed}_{digest}.json"


def extract_spans(clauses: list[Clause]) -> list[SpanEdit]:
    """Find corruptible spans in each clause (original == replacement placeholder)."""
    found: list[SpanEdit] = []
    seen: set[tuple[str, str, str]] = set()
    for clause in clauses:
        for category, pattern in PATTERN_BY_CATEGORY.items():
            for match in pattern.finditer(clause.text):
                original = match.group()
                key = (clause.id, category, original)
                if key in seen or len(original.strip()) < 3:
                    continue
                seen.add(key)
                found.append(
                    SpanEdit(
                        clause_id=clause.id,
                        category=category,
                        original=original,
                        replacement=original,
                    )
                )
    return found


def _parse_money_amount(text: str) -> float | None:
    digits = re.sub(r"[^\d.]", "", text.replace(",", ""))
    if not digits:
        return None
    try:
        return float(digits)
    except ValueError:
        return None


def _format_money(original: str, amount: float) -> str:
    if "," in original or re.search(r"\.\d{2}", original):
        formatted = f"{amount:,.2f}".rstrip("0").rstrip(".")
        if "." not in formatted and re.search(r"\.\d{2}", original):
            formatted += ".00"
    else:
        formatted = str(int(round(amount))) if amount == int(amount) else f"{amount:.2f}"
    if original.strip().startswith("$"):
        return re.sub(r"[\d,.]+", formatted.replace(",", ","), original, count=1)
    if original.strip().startswith("€"):
        return re.sub(r"[\d,\s.]+", formatted, original, count=1)
    return formatted


def _local_money_replacement(original: str, rng: random.Random, pool: list[str]) -> str:
    amount = _parse_money_amount(original)
    if amount is not None and amount > 0:
        factor = rng.choice(LOCAL_FACTORS)
        return _format_money(original, max(1.0, amount * factor))
    alts = [p for p in pool if p != original]
    return rng.choice(alts) if alts else original + " (revised)"


def _local_duration_replacement(original: str, rng: random.Random, pool: list[str]) -> str:
    alts = [p for p in pool if p.lower() != original.lower()]
    if alts:
        return rng.choice(alts)
    num_match = re.search(r"\d+", original)
    if num_match:
        old = int(num_match.group())
        factor = rng.choice(LOCAL_FACTORS)
        new_num = max(1, int(old * factor))
        return original.replace(num_match.group(), str(new_num), 1)
    return original.replace("days", "weeks", 1)


def _local_percentage_replacement(original: str, rng: random.Random) -> str:
    num_match = re.search(r"(\d+(?:\.\d+)?)", original)
    if not num_match:
        return original
    old = float(num_match.group())
    delta = rng.choice([-5, -3, -2, 2, 3, 5, 7, 10])
    new_val = max(0.1, old + delta)
    if "." in num_match.group():
        return original.replace(num_match.group(), f"{new_val:.1f}", 1)
    return original.replace(num_match.group(), str(int(new_val)), 1)


def _local_date_replacement(original: str, rng: random.Random) -> str:
    year_match = re.search(r"\b(20\d{2})\b", original)
    if year_match:
        year = int(year_match.group())
        return original.replace(year_match.group(), str(year + rng.choice([-2, -1, 1, 2])), 1)
    return original + " (amended)"


def _local_obligation_replacement(original: str, rng: random.Random) -> str:
    swaps = [
        ("shall not", "may"),
        ("shall", "may"),
        ("must not", "need not"),
        ("must", "may"),
        ("may not", "shall"),
        ("will not", "will"),
    ]
    low = original.lower()
    for old, new in swaps:
        if low == old:
            return new if original.islower() else new.capitalize()
    return original


def _local_jurisdiction_replacement(
    original: str, rng: random.Random, pool: list[str]
) -> str:
    alts = [p for p in pool if p.lower() != original.lower()]
    if alts:
        return rng.choice(alts)
    fallbacks = ["California", "New York", "Delaware", "Texas", "Nevada"]
    pick = rng.choice(fallbacks)
    return re.sub(r"[A-Z][a-z]+(?: [A-Z][a-z]+)*", pick, original, count=1)


def _local_rate_replacement(original: str, rng: random.Random) -> str:
    amount = _parse_money_amount(original)
    if amount is not None and amount > 0:
        factor = rng.choice(LOCAL_FACTORS)
        return _format_money(original, max(0.01, amount * factor))
    return original


def _assign_local_replacements(
    spans: list[SpanEdit],
    rng: random.Random,
) -> list[SpanEdit]:
    by_category: dict[str, list[str]] = {}
    for span in spans:
        by_category.setdefault(span.category, []).append(span.original)

    edits: list[SpanEdit] = []
    for span in spans:
        pool = by_category.get(span.category, [])
        if span.category == "money":
            replacement = _local_money_replacement(span.original, rng, pool)
        elif span.category == "duration":
            replacement = _local_duration_replacement(span.original, rng, pool)
        elif span.category == "percentage":
            replacement = _local_percentage_replacement(span.original, rng)
        elif span.category == "date":
            replacement = _local_date_replacement(span.original, rng)
        elif span.category == "obligation":
            replacement = _local_obligation_replacement(span.original, rng)
        elif span.category == "jurisdiction":
            replacement = _local_jurisdiction_replacement(span.original, rng, pool)
        elif span.category == "rate":
            replacement = _local_rate_replacement(span.original, rng)
        else:
            replacement = span.original

        if replacement != span.original:
            edits.append(span.model_copy(update={"replacement": replacement}))
    rng.shuffle(edits)
    return edits


def _eligible_missing_clause_ids(clauses: list[Clause], rng: random.Random) -> list[str]:
    if len(clauses) <= 2:
        return [clauses[0].id] if clauses else []
    middle = [c.id for c in clauses[1:-1]]
    rng.shuffle(middle)
    return middle


def _local_extra_clause(clauses: list[Clause], rng: random.Random) -> ExtraClauseSpec:
    """Build a fake clause echoing topics found in this document."""
    topics: list[str] = []
    joined = " ".join(c.text.lower() for c in clauses)
    for keyword, label in (
        ("confidential", "Confidentiality"),
        ("indemn", "Indemnification"),
        ("terminat", "Termination"),
        ("liabil", "Limitation of Liability"),
        ("payment", "Payment Terms"),
        ("insurance", "Insurance"),
        ("data protection", "Data Protection"),
        ("force majeure", "Force Majeure"),
        ("audit", "Audit Rights"),
        ("assign", "Assignment"),
    ):
        if keyword in joined:
            topics.append(label)

    topic = rng.choice(topics) if topics else "Miscellaneous"
    durations = [
        s.original
        for s in extract_spans(clauses)
        if s.category == "duration"
    ]
    duration = rng.choice(durations) if durations else "thirty (30) days"
    bodies = [
        (
            f"{topic}. Either party may suspend performance upon written notice if the "
            f"other party fails to cure a material breach within {duration}. "
            f"The non-breaching party may pursue any remedies available at law or equity."
        ),
        (
            f"{topic}. The parties agree that any amendment to this section requires "
            f"written consent and {duration} prior notice to the other party's "
            f"authorized representative."
        ),
        (
            f"{topic}. Notwithstanding any other provision, obligations under this "
            f"section survive termination for {duration} following the effective date "
            f"of termination."
        ),
    ]
    return ExtraClauseSpec(
        text=rng.choice(bodies),
        insert_index=rng.randint(0, max(0, len(clauses) - 1)),
    )


def generate_local_plan(
    clauses: list[Clause],
    document_id: str,
    seed: int,
) -> DocumentCorruptionPlan:
    rng = random.Random(seed)
    spans = extract_spans(clauses)
    edits = _assign_local_replacements(spans, rng)
    return DocumentCorruptionPlan(
        document_id=document_id,
        seed=seed,
        content_hash=content_hash(clauses),
        mode="local",
        span_edits=edits,
        missing_clause_ids=_eligible_missing_clause_ids(clauses, rng),
        extra_clause=_local_extra_clause(clauses, rng),
    )


def _gemini_system_prompt() -> str:
    return (
        "You generate plausible-but-wrong legal contract corruptions for benchmark testing. "
        "Return JSON only with keys: span_edits (list), extra_clause (object). "
        "Each span_edits item: clause_id, category, original (exact substring from input), "
        "replacement (plausible wrong value in same format). "
        "Categories: money, duration, percentage, date, obligation, jurisdiction, rate. "
        "Make replacements document-specific and subtle—not generic boilerplate. "
        "extra_clause: {text: string (1-3 sentences, new clause fitting this contract), "
        "insert_index: int}. "
        "Provide 6-12 span_edits across varied categories when possible."
    )


def _gemini_user_payload(
    clauses: list[Clause],
    spans: list[SpanEdit],
    document_id: str,
    seed: int,
) -> str:
    clause_excerpts = [
        {"id": c.id, "text": c.text[:1200]}
        for c in clauses[: min(25, len(clauses))]
    ]
    span_sample = [
        {"clause_id": s.clause_id, "category": s.category, "original": s.original}
        for s in spans[:40]
    ]
    return json.dumps(
        {
            "document_id": document_id,
            "seed": seed,
            "clauses": clause_excerpts,
            "spannables": span_sample,
        },
        indent=2,
    )


async def _generate_gemini_plan_async(
    clauses: list[Clause],
    document_id: str,
    seed: int,
    *,
    model: str = "gemini-flash-latest",
) -> DocumentCorruptionPlan:
    from models.gemini_client import GeminiClient

    spans = extract_spans(clauses)
    client = GeminiClient(model=model)
    raw = await client.complete(
        _gemini_system_prompt(),
        _gemini_user_payload(clauses, spans, document_id, seed),
    )
    data = json.loads(raw)

    span_edits: list[SpanEdit] = []
    clause_ids = {c.id for c in clauses}
    for item in data.get("span_edits", []):
        clause_id = item.get("clause_id", "")
        original = item.get("original", "")
        replacement = item.get("replacement", "")
        category = item.get("category", "money")
        if (
            clause_id in clause_ids
            and original
            and replacement
            and original != replacement
        ):
            clause = next(c for c in clauses if c.id == clause_id)
            if original in clause.text:
                span_edits.append(
                    SpanEdit(
                        clause_id=clause_id,
                        category=category,
                        original=original,
                        replacement=replacement,
                    )
                )

    if not span_edits:
        return generate_local_plan(clauses, document_id, seed)

    rng = random.Random(seed)
    extra_raw = data.get("extra_clause") or {}
    extra_text = extra_raw.get("text", "").strip()
    insert_index = extra_raw.get("insert_index", rng.randint(0, max(0, len(clauses) - 1)))
    extra = None
    if extra_text:
        extra = ExtraClauseSpec(
            text=extra_text,
            insert_index=min(max(0, int(insert_index)), max(0, len(clauses) - 1)),
        )
    else:
        extra = _local_extra_clause(clauses, rng)

    return DocumentCorruptionPlan(
        document_id=document_id,
        seed=seed,
        content_hash=content_hash(clauses),
        mode="gemini",
        span_edits=span_edits,
        missing_clause_ids=_eligible_missing_clause_ids(clauses, rng),
        extra_clause=extra,
    )


def _should_use_gemini(mode: CorruptionMode) -> bool:
    if mode == "local":
        return False
    if mode == "gemini":
        return True
    from models.gemini_client import resolve_gemini_api_key

    return bool(resolve_gemini_api_key())


def resolve_corruption_plan(
    clauses: list[Clause],
    document_id: str,
    seed: int,
    *,
    mode: CorruptionMode = "local",
    cache_dir: Path | None = None,
    use_cache: bool = True,
    gemini_model: str = "gemini-flash-latest",
) -> DocumentCorruptionPlan:
    """Load or build a document-specific corruption plan (cached for reproducibility)."""
    digest = content_hash(clauses)
    cache_root = cache_dir or DEFAULT_CACHE_DIR
    path = _cache_path(cache_root, document_id, seed, digest)

    if use_cache and path.exists():
        plan = DocumentCorruptionPlan.model_validate_json(
            path.read_text(encoding="utf-8")
        )
        if plan.content_hash == digest:
            return plan

    if _should_use_gemini(mode):
        try:
            plan = asyncio.run(
                _generate_gemini_plan_async(
                    clauses,
                    document_id,
                    seed,
                    model=gemini_model,
                )
            )
        except Exception:
            plan = generate_local_plan(clauses, document_id, seed)
    else:
        plan = generate_local_plan(clauses, document_id, seed)

    if use_cache:
        cache_root.mkdir(parents=True, exist_ok=True)
        path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    return plan


def pick_span_edit(
    plan: DocumentCorruptionPlan,
    clauses: list[Clause],
    rng: random.Random,
) -> SpanEdit | None:
    """Choose one applicable edit from the plan for altered_text corruption."""
    by_id = {c.id: c.text for c in clauses}
    applicable = [
        edit
        for edit in plan.span_edits
        if edit.original in by_id.get(edit.clause_id, "")
        and edit.replacement != edit.original
    ]
    return rng.choice(applicable) if applicable else None


def apply_span_edit(clauses: list[Clause], edit: SpanEdit) -> list[Clause]:
    result = []
    for clause in clauses:
        if clause.id != edit.clause_id:
            result.append(clause)
            continue
        if edit.original not in clause.text:
            result.append(clause)
            continue
        result.append(
            clause.model_copy(
                update={"text": clause.text.replace(edit.original, edit.replacement, 1)}
            )
        )
    return result
