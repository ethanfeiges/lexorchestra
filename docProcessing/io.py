"""Save/load SoT bundles and build from contract files."""

from __future__ import annotations

import json
from pathlib import Path

from docProcessing.bundle import build_bundle
from docProcessing.corruption_plan import CorruptionMode
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
    document_type: str | None = None,
    *,
    corruption_mode: CorruptionMode = "local",
    use_corruption_cache: bool = True,
) -> SoTBundle:
    """Parse a contract file and build an SoT bundle. Primary entry point."""
    clauses = parse_document(path)
    document_id = path.stem
    if document_type is None:
        try:
            from benchmark.document_types import document_type_for_id

            document_type = document_type_for_id(document_id)
        except ImportError:
            document_type = "msa"
    return build_bundle(
        clauses=clauses,
        document_id=document_id,
        source_path=str(path),
        seed=seed,
        corruptions=corruptions,
        document_type=document_type,
        corruption_mode=corruption_mode,
        use_corruption_cache=use_corruption_cache,
    )
