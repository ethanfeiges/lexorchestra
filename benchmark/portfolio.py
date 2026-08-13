"""Portfolio (multi-document) benchmark assembly."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import yaml

from benchmark.answers import DocumentAnswers, load_answers
from benchmark.document_types import TYPE_LABELS, primary_fixtures
from docProcessing.io import build_bundle_from_file
from docProcessing.models import SoTBundle
from docProcessing.prompt import _truncate, portfolio_prompt_label
from docProcessing.store import SoTStore

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "legalDocs" / "contracts" / "public"
CASES_DIR = Path(__file__).resolve().parent / "portfolio_cases"

PORTFOLIO_CONDITIONS = ("portfolio_clean", "cross_type_mislabeled")
PORTFOLIO_HEADER = (
    "Portfolio documents (each clause is tagged with document_id — cite only from your assigned document):"
)


@dataclass(frozen=True)
class PortfolioDocument:
    """One document in a portfolio run."""

    document_id: str
    document_type: str
    bundle: SoTBundle
    answers: DocumentAnswers
    store: SoTStore


@dataclass(frozen=True)
class PortfolioContext:
    """Shared prompt state for a cross-type portfolio run."""

    portfolio_id: str
    documents: tuple[PortfolioDocument, ...]
    document_block: str
    condition: str
    mislabeled: tuple[tuple[str, str], ...]


def load_portfolio_case(case_id: str = "primary_five") -> list[str]:
    """Load document ids for a portfolio case YAML."""
    path = CASES_DIR / f"{case_id}.yaml"
    if path.is_file():
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        ids = data.get("document_ids")
        if isinstance(ids, list) and ids:
            return [str(doc_id) for doc_id in ids]
    return primary_fixtures()


def _mislabel_pairs(
    document_ids: list[str],
    seed: int,
) -> list[tuple[str, str]]:
    """Return (display_label_doc_id, content_source_doc_id) swaps."""
    if len(document_ids) < 2:
        return []
    rng = random.Random(seed + 91)
    label_doc = rng.choice(document_ids)
    source_candidates = [doc_id for doc_id in document_ids if doc_id != label_doc]
    source_doc = rng.choice(source_candidates)
    return [(label_doc, source_doc)]


def build_portfolio_context(
    *,
    case_id: str = "primary_five",
    condition: str = "portfolio_clean",
    seed: int = 42,
    document_ids: list[str] | None = None,
) -> PortfolioContext:
    """Build bundles, stores, and combined prompt for a portfolio run."""
    if condition not in PORTFOLIO_CONDITIONS:
        raise ValueError(f"Unknown portfolio condition: {condition}")

    ids = document_ids or load_portfolio_case(case_id)
    documents: list[PortfolioDocument] = []
    for doc_id in ids:
        path = FIXTURES / f"{doc_id}.txt"
        if not path.is_file():
            raise FileNotFoundError(f"Missing portfolio fixture: {path}")
        bundle = build_bundle_from_file(path, seed=seed)
        answers = load_answers(doc_id)
        store = SoTStore(bundle.canonical, doc_id)
        documents.append(
            PortfolioDocument(
                document_id=doc_id,
                document_type=answers.document_type,
                bundle=bundle,
                answers=answers,
                store=store,
            )
        )

    mislabeled: list[tuple[str, str]] = []
    if condition == "cross_type_mislabeled":
        mislabeled = _mislabel_pairs(ids, seed)

    document_block = format_portfolio_for_prompt(
        documents,
        mislabeled=mislabeled,
    )
    return PortfolioContext(
        portfolio_id=case_id,
        documents=tuple(documents),
        document_block=document_block,
        condition=condition,
        mislabeled=tuple(mislabeled),
    )


def portfolio_document_type_label(document_type: str) -> str:
    return TYPE_LABELS.get(document_type, "contract")


def format_portfolio_for_prompt(
    documents: list[PortfolioDocument],
    *,
    mislabeled: list[tuple[str, str]] | None = None,
    header: str | None = None,
) -> str:
    """Format multiple signed canonical documents into one shared prompt block."""
    mislabel_map = dict(mislabeled or [])
    lines: list[str] = [header or PORTFOLIO_HEADER, ""]

    for entry in documents:
        label_doc_id = entry.document_id
        source_doc_id = mislabel_map.get(label_doc_id, label_doc_id)
        source = next(d for d in documents if d.document_id == source_doc_id)
        display_label = portfolio_prompt_label(label_doc_id)
        for clause in source.bundle.canonical:
            text = _truncate(clause.text.replace("\n", " "))
            lines.append(f"[{display_label}] {clause.id}: {text}")

    return "\n".join(lines)
