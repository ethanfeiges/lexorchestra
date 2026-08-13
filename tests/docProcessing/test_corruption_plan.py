"""Tests for document-specific corruption plans."""

from pathlib import Path

from docProcessing.corruption_plan import (
    extract_spans,
    generate_local_plan,
    pick_span_edit,
    resolve_corruption_plan,
)
from docProcessing.parser import parse_document

FIXTURES = Path(__file__).resolve().parents[2] / "legalDocs" / "contracts"
PRIMARY = FIXTURES / "public" / "edgar_edgemode_inc_ex10.1.txt"


def _clauses():
    return parse_document(PRIMARY)


def test_extract_spans_finds_document_specific_values():
    spans = extract_spans(_clauses())
    categories = {s.category for s in spans}
    originals = {s.original for s in spans}
    assert "money" in categories or "rate" in categories
    assert "duration" in categories
    assert any("$" in o or "days" in o.lower() for o in originals)


def test_local_plan_edits_use_document_text():
    clauses = _clauses()
    plan = generate_local_plan(clauses, "edgar_edgemode_inc_ex10.1", seed=42)
    assert plan.span_edits
    assert all(edit.original != edit.replacement for edit in plan.span_edits)
    by_id = {c.id: c.text for c in clauses}
    assert all(edit.original in by_id[edit.clause_id] for edit in plan.span_edits)


def test_same_seed_same_plan():
    clauses = _clauses()
    p1 = resolve_corruption_plan(
        clauses, "edgar_edgemode_inc_ex10.1", 42, use_cache=False
    )
    p2 = resolve_corruption_plan(
        clauses, "edgar_edgemode_inc_ex10.1", 42, use_cache=False
    )
    assert p1.model_dump() == p2.model_dump()


def test_different_seeds_different_plans():
    clauses = _clauses()
    p1 = resolve_corruption_plan(
        clauses, "edgar_edgemode_inc_ex10.1", 1, use_cache=False
    )
    p2 = resolve_corruption_plan(
        clauses, "edgar_edgemode_inc_ex10.1", 2, use_cache=False
    )
    assert p1.model_dump() != p2.model_dump()


def test_pick_span_edit_is_deterministic():
    clauses = _clauses()
    plan = generate_local_plan(clauses, "edgar_edgemode_inc_ex10.1", seed=7)
    import random

    rng1 = random.Random(99)
    rng2 = random.Random(99)
    e1 = pick_span_edit(plan, clauses, rng1)
    e2 = pick_span_edit(plan, clauses, rng2)
    assert e1 == e2
