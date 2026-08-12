"""Parse contract files into canonical clauses."""

from __future__ import annotations

import re
from pathlib import Path

from docProcessing.models import Clause

HEADING_PATTERN = re.compile(
    r"^(?:\d+\.\s|\d+\.\d+\.?\s|Section\s+\d+)",
    re.MULTILINE | re.IGNORECASE,
)

MIN_CHUNK_LENGTH = 40


def normalize_text(text: str) -> str:
    """Unify line endings and collapse excessive blank lines."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _format_clause_id(index: int) -> str:
    return f"c-{index:03d}"


def _merge_tiny_ranges(ranges: list[tuple[int, int]], normalized: str) -> list[tuple[int, int]]:
    """Merge spans shorter than MIN_CHUNK_LENGTH with the previous span."""
    if not ranges:
        return []

    merged: list[tuple[int, int]] = [ranges[0]]
    for start, end in ranges[1:]:
        if len(normalized[start:end]) < MIN_CHUNK_LENGTH:
            prev_start, _ = merged[-1]
            merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))

    if len(merged) == 1:
        return merged

    result: list[tuple[int, int]] = [merged[0]]
    for start, end in merged[1:]:
        if len(normalized[start:end]) < MIN_CHUNK_LENGTH:
            prev_start, _ = result[-1]
            result[-1] = (prev_start, end)
        else:
            result.append((start, end))
    return result


def _ranges_to_clauses(ranges: list[tuple[int, int]], normalized: str) -> list[Clause]:
    clauses: list[Clause] = []
    for i, (start, end) in enumerate(ranges):
        text = normalized[start:end]
        if not text.strip():
            continue
        clauses.append(
            Clause(
                id=_format_clause_id(len(clauses) + 1),
                text=text,
                start_offset=start,
                end_offset=end,
            )
        )
    return clauses


def _split_by_headings(text: str) -> list[tuple[int, int]] | None:
    """Split text at numbered heading boundaries. Returns None if no headings found."""
    matches = list(HEADING_PATTERN.finditer(text))
    if not matches:
        return None

    ranges: list[tuple[int, int]] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        if text[start:end].strip():
            ranges.append((start, end))

    return _merge_tiny_ranges(ranges, text) if ranges else None


def _split_by_paragraphs(text: str) -> list[tuple[int, int]]:
    """Fallback: split on blank lines (paragraph chunks)."""
    if not text.strip():
        return []

    ranges: list[tuple[int, int]] = []
    parts = re.split(r"\n\n", text)
    offset = 0
    for i, part in enumerate(parts):
        if i > 0:
            offset += 2
        start = offset
        end = start + len(part)
        if part.strip():
            ranges.append((start, end))
        offset = end

    return _merge_tiny_ranges(ranges, text)


def parse_text(text: str, document_id: str = "inline") -> list[Clause]:
    """Parse normalized plain text into clauses with sequential IDs and offsets."""
    del document_id  # reserved for future logging/metadata
    normalized = normalize_text(text)
    ranges = _split_by_headings(normalized)
    if ranges is None:
        ranges = _split_by_paragraphs(normalized)
    return _ranges_to_clauses(ranges, normalized)


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_pdf(path: Path) -> str:
    try:
        import fitz  # type: ignore[import-untyped]  # PyMuPDF
    except ImportError as exc:
        raise ImportError(
            "PDF support requires PyMuPDF. Install with: pip install pymupdf"
        ) from exc

    doc = fitz.open(path)
    try:
        return "\n\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def _read_docx(path: Path) -> str:
    try:
        from docx import Document  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "DOCX support requires python-docx. Install with: pip install python-docx"
        ) from exc

    document = Document(str(path))
    return "\n\n".join(p.text for p in document.paragraphs if p.text.strip())


def _extract_raw_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return _read_text_file(path)
    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".docx":
        return _read_docx(path)
    raise ValueError(f"Unsupported file type: {suffix}")


def parse_document(path: Path) -> list[Clause]:
    """Parse a contract file (.txt, .pdf, or .docx) into canonical clauses."""
    raw = _extract_raw_text(path)
    normalized = normalize_text(raw)
    return parse_text(normalized, document_id=path.stem)
