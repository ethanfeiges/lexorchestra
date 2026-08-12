"""Load per-document benchmark answer keys."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

ANSWERS_DIR = Path(__file__).resolve().parent


class PlaybookRuleAnswer(BaseModel):
    id: str
    question: str
    expected: str
    canonical_clause_ids: list[str]
    required_substrings: list[str] = Field(default_factory=list)
    notes: str | None = None


class ExtractQuestionAnswer(BaseModel):
    id: str
    question: str
    acceptable_clause_ids: list[str]
    required_substrings: list[str]


class DocumentAnswers(BaseModel):
    document_id: str
    document_type: str = "msa"
    rules: list[PlaybookRuleAnswer]
    extract_questions: list[ExtractQuestionAnswer]


def load_answers(document_id: str, answers_dir: Path | None = None) -> DocumentAnswers:
    """Load benchmark answers for a document."""
    base = answers_dir or ANSWERS_DIR
    path = base / f"{document_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No benchmark answers at {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return DocumentAnswers.model_validate(data)


def list_answer_documents(answers_dir: Path | None = None) -> list[str]:
    """Return document IDs with answer key files."""
    base = answers_dir or ANSWERS_DIR
    if not base.exists():
        return []
    return sorted(
        p.stem for p in base.glob("*.yaml") if p.name != "README.yaml"
    )
