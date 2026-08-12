"""Save/load SoT bundles and build from contract files."""

from __future__ import annotations

import json
from pathlib import Path

from docProcessing.bundle import build_bundle
from docProcessing.models import SoTBundle
from docProcessing.parser import parse_document


def save_bundle(bundle: SoTBundle, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        bundle.model_dump_json(indent=2),
        encoding="utf-8",
    )


def load_bundle(path: Path) -> SoTBundle:
    data = json.loads(path.read_text(encoding="utf-8"))
    return SoTBundle.model_validate(data)


def build_bundle_from_file(
    path: Path,
    seed: int = 42,
    corruptions: list[str] | None = None,
) -> SoTBundle:
    """Parse a contract file and build an SoT bundle. Primary entry point."""
    clauses = parse_document(path)
    document_id = path.stem
    return build_bundle(
        clauses=clauses,
        document_id=document_id,
        source_path=str(path),
        seed=seed,
        corruptions=corruptions,
    )
