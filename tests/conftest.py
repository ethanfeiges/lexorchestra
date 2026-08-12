"""Shared pytest fixtures for LexOrchestra."""

from pathlib import Path

import pytest

CONTRACTS_DIR = Path(__file__).resolve().parents[1] / "legalDocs" / "contracts"
PUBLIC_DIR = CONTRACTS_DIR / "public"
MANIFEST_PATH = CONTRACTS_DIR / "manifest.json"

# Primary real MSA for unit tests (Edgemode ↔ Cudo Ventures, SEC EX-10.1)
PRIMARY_MSA = PUBLIC_DIR / "edgar_edgemode_inc_ex10.1.txt"


def _public_msas() -> list[Path]:
    if not PUBLIC_DIR.exists():
        return []
    return sorted(PUBLIC_DIR.glob("*.txt"))


@pytest.fixture(scope="session")
def primary_msa_path() -> Path:
    if not PRIMARY_MSA.exists():
        pytest.skip(
            "Real MSA fixtures missing. Run: python -m benchmark.fetch_contracts"
        )
    return PRIMARY_MSA


@pytest.fixture(scope="session")
def public_msa_paths() -> list[Path]:
    paths = _public_msas()
    if not paths:
        pytest.skip(
            "No public MSAs in legalDocs/contracts/public/. "
            "Run: python -m benchmark.fetch_contracts"
        )
    return paths
