"""Tests for public contract fixtures and fetch metadata."""

import json
from pathlib import Path

import pytest

from benchmark.answers import list_answer_documents
from docProcessing.io import build_bundle_from_file, load_bundle, save_bundle
from benchmark.fetch_contracts import html_to_text, load_manifest

FIXTURES = Path(__file__).resolve().parents[2] / "legalDocs" / "contracts"
PUBLIC_DIR = FIXTURES / "public"
MANIFEST_PATH = FIXTURES / "manifest.json"


@pytest.fixture(scope="module")
def manifest() -> dict:
    if not MANIFEST_PATH.exists():
        pytest.skip("Public contract manifest not found; run: python -m benchmark.fetch_contracts")
    return load_manifest(MANIFEST_PATH)


def test_manifest_lists_public_contracts(manifest: dict):
    assert manifest["source"] == "sec_edgar"
    assert len(manifest["contracts"]) >= 1
    for entry in manifest["contracts"]:
        assert entry["url"].startswith("https://www.sec.gov/")
        assert entry["char_count"] >= 3000
        path = Path(entry["local_path"])
        assert path.exists(), f"Missing fetched contract: {path}"


@pytest.mark.parametrize(
    "contract_path",
    [
        pytest.param(PUBLIC_DIR / f"{doc_id}.txt", id=doc_id)
        for doc_id in list_answer_documents()
        if (PUBLIC_DIR / f"{doc_id}.txt").exists()
    ]
    if PUBLIC_DIR.exists()
    else [],
)
def test_public_contract_parses_and_bundles(contract_path: Path):
    bundle = build_bundle_from_file(contract_path, seed=42)
    assert len(bundle.canonical) >= 3
    assert len(bundle.candidates) == 5
    assert bundle.document_id == contract_path.stem


def test_public_contract_save_load_round_trip(manifest: dict, tmp_path: Path):
    first = manifest["contracts"][0]
    source = Path(first["local_path"])
    bundle = build_bundle_from_file(source, seed=42)
    out = tmp_path / f"{source.stem}.json"
    save_bundle(bundle, out)
    loaded = load_bundle(out)
    assert loaded.model_dump() == bundle.model_dump()


def test_html_to_text_strips_tags():
    html = "<html><body><p>Limitation of Liability</p><p>Cap is $1,000,000.</p></body></html>"
    text = html_to_text(html)
    assert "Limitation of Liability" in text
    assert "Cap is $1,000,000." in text


def test_manifest_is_valid_json():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert "contracts" in data
