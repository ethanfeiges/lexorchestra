"""Document-type registry and primary fixture selection."""

from __future__ import annotations

import json
from pathlib import Path

from benchmark.answers import list_answer_documents

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "legalDocs" / "contracts" / "manifest.json"

DOCUMENT_TYPES = (
    "msa",
    "software_license",
    "nda",
    "employment",
    "credit",
)

TYPE_QUERIES: dict[str, str] = {
    "msa": "master services agreement",
    "software_license": "software license agreement",
    "nda": "non-disclosure agreement",
    "employment": "employment agreement",
    "credit": "credit agreement",
}

TYPE_LABELS: dict[str, str] = {
    "msa": "Master Services Agreement",
    "software_license": "Software License Agreement",
    "nda": "Non-Disclosure Agreement",
    "employment": "Employment Agreement",
    "credit": "Credit Agreement",
}


def load_manifest(manifest_path: Path | None = None) -> dict:
    path = manifest_path or MANIFEST_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def document_type_for_id(document_id: str, manifest_path: Path | None = None) -> str:
    """Return document_type for a fixture id (defaults to msa)."""
    manifest = load_manifest(manifest_path)
    for contract in manifest.get("contracts", []):
        if contract.get("id") == document_id:
            return contract.get("document_type", "msa")
    return "msa"


def primary_fixtures(
    *,
    manifest_path: Path | None = None,
    require_answer_key: bool = True,
) -> list[str]:
    """Return one primary document id per document type."""
    manifest = load_manifest(manifest_path)
    answer_ids = set(list_answer_documents())
    primaries: dict[str, str] = {}

    for contract in manifest.get("contracts", []):
        doc_id = contract.get("id")
        dtype = contract.get("document_type", "msa")
        if not doc_id or dtype not in DOCUMENT_TYPES:
            continue
        if not contract.get("primary_fixture"):
            continue
        if require_answer_key and doc_id not in answer_ids:
            continue
        primaries[dtype] = doc_id

    return [primaries[t] for t in DOCUMENT_TYPES if t in primaries]
