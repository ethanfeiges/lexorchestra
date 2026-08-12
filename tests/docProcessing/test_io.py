"""Tests for docProcessing.io."""

import json
from pathlib import Path

from docProcessing.io import build_bundle_from_file, load_bundle, save_bundle


def test_build_bundle_from_file_returns_valid_bundle(primary_msa_path: Path):
    bundle = build_bundle_from_file(primary_msa_path, seed=42)
    assert bundle.document_id == "edgar_edgemode_inc_ex10.1"
    assert len(bundle.canonical) >= 3
    assert any(c.valid for c in bundle.candidates)


def test_save_and_load_round_trip(primary_msa_path: Path, tmp_path: Path):
    bundle = build_bundle_from_file(primary_msa_path, seed=42)
    out_path = tmp_path / "bundle.json"
    save_bundle(bundle, out_path)
    loaded = load_bundle(out_path)
    assert loaded.model_dump() == bundle.model_dump()
    raw = json.loads(out_path.read_text(encoding="utf-8"))
    assert "canonical" in raw
    assert raw["document_id"] == "edgar_edgemode_inc_ex10.1"
