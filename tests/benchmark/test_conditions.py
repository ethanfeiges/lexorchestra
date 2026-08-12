"""Tests for benchmark conditions."""

import random

from benchmark.conditions import (
    build_prompt_context,
    fresh_seed,
    sample_decoys,
)
from docProcessing.io import build_bundle_from_file
from pathlib import Path

PRIMARY = (
    Path(__file__).resolve().parents[2]
    / "legalDocs" / "contracts"
    / "public"
    / "edgar_edgemode_inc_ex10.1.txt"
)


def test_clean_has_no_decoys():
    decoys = sample_decoys(42, "clean")
    assert decoys == []


def test_noisy_has_decoys():
    decoys = sample_decoys(42, "noisy_prompt")
    assert 1 <= len(decoys) <= 2


def test_fresh_seed_varies():
    seeds = {fresh_seed() for _ in range(20)}
    assert len(seeds) > 1


def test_different_seeds_different_decoy_text():
    b1 = build_bundle_from_file(PRIMARY, seed=1)
    b2 = build_bundle_from_file(PRIMARY, seed=2)
    d1 = next(c for c in b1.candidates if c.corruption == "reordered")
    d2 = next(c for c in b2.candidates if c.corruption == "reordered")
    id_map_1 = {c.id: c.text for c in d1.clauses}
    id_map_2 = {c.id: c.text for c in d2.clauses}
    assert id_map_1 != id_map_2


def test_prompt_context_includes_signed():
    bundle = build_bundle_from_file(PRIMARY, seed=42)
    ctx = build_prompt_context(bundle, "noisy_prompt", 42)
    assert "signed_contract" in ctx.document_block
    assert "[signed_contract]" in ctx.document_block


def test_unlabeled_noisy_uses_anonymous_labels():
    bundle = build_bundle_from_file(PRIMARY, seed=42)
    ctx = build_prompt_context(bundle, "unlabeled_noisy", 42)
    assert "signed_contract" not in ctx.document_block
    assert "labels are arbitrary" in ctx.document_block
    assert "[version_1]" in ctx.document_block
    assert ctx.label_aliases is not None
    assert "signed_contract" in ctx.label_aliases
    assert len(ctx.decoys_in_prompt) >= 1


def test_unlabeled_noisy_decoys_match_noisy_prompt():
    decoys_noisy = sample_decoys(42, "noisy_prompt")
    decoys_unlabeled = sample_decoys(42, "unlabeled_noisy")
    assert decoys_noisy == decoys_unlabeled
