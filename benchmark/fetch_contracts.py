"""Fetch real public contracts from SEC EDGAR for LexOrchestra fixtures."""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path

DEFAULT_USER_AGENT = "LexOrchestra/0.1 (research; contact: lexorchestra-dev@example.com)"
EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"
REQUEST_DELAY_SEC = 0.15
MIN_CONTRACT_CHARS = 3000

SEARCH_QUERIES = [
    '"master services agreement"',
    '"software license agreement"',
    '"limitation of liability"',
]


@dataclass(frozen=True)
class ContractRecord:
    """Metadata for a fetched public contract."""

    id: str
    source: str
    company: str
    cik: str
    form: str
    file_type: str
    file_description: str
    filing_date: str
    accession: str
    filename: str
    url: str
    local_path: str
    char_count: int


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip = True
        elif tag in {"p", "br", "div", "tr", "li", "h1", "h2", "h3", "h4", "td"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._skip = False
        elif tag in {"p", "div", "tr", "li", "h1", "h2", "h3", "h4"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def _normalize_cik(cik: str) -> str:
    return str(int(cik))


def _accession_no_dashes(accession: str) -> str:
    return accession.replace("-", "")


def _build_document_url(cik: str, accession: str, filename: str) -> str:
    return (
        f"{SEC_ARCHIVES_BASE}/{_normalize_cik(cik)}/"
        f"{_accession_no_dashes(accession)}/{filename}"
    )


def _extract_sec_text_payload(raw: str) -> str:
    """Prefer SEC <TEXT> block when present."""
    match = re.search(r"<TEXT>(.*)</TEXT>", raw, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1)
    return raw


def html_to_text(html: str) -> str:
    """Convert SEC filing HTML to normalized plain text."""
    payload = _extract_sec_text_payload(html)
    parser = _HTMLTextExtractor()
    parser.feed(payload)
    parser.close()
    text = parser.get_text()
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _slugify(value: str, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
    return slug[:max_len] or "contract"


def _request(url: str, user_agent: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json, text/html, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def search_ex10_contracts(
    query: str,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    start_date: str = "2024-01-01",
    end_date: str = "2025-12-31",
    size: int = 40,
) -> list[dict]:
    """Search SEC EFTS for EX-10 contract exhibits matching a query."""
    params = urllib.parse.urlencode(
        {
            "q": query,
            "forms": "8-K,10-K,10-Q",
            "dateRange": "custom",
            "startdt": start_date,
            "enddt": end_date,
            "size": str(size),
        }
    )
    url = f"{EFTS_URL}?{params}"
    raw = _request(url, user_agent)
    data = json.loads(raw.decode("utf-8"))
    hits = data.get("hits", {}).get("hits", [])
    results: list[dict] = []
    for hit in hits:
        source = hit.get("_source", {})
        file_type = str(source.get("file_type", ""))
        if not file_type.startswith("EX-10"):
            continue
        doc_id = hit.get("_id", "")
        if ":" not in doc_id:
            continue
        accession, filename = doc_id.split(":", 1)
        ciks = source.get("ciks") or []
        if not ciks:
            continue
        results.append(
            {
                "accession": accession,
                "filename": filename,
                "cik": ciks[0],
                "form": source.get("form", ""),
                "file_type": file_type,
                "file_description": source.get("file_description") or "",
                "filing_date": source.get("file_date") or "",
                "company": (source.get("display_names") or ["Unknown"])[0],
            }
        )
    return results


def download_contract_text(
    cik: str,
    accession: str,
    filename: str,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
) -> tuple[str, str]:
    """Download an EDGAR exhibit and return (plain_text, source_url)."""
    url = _build_document_url(cik, accession, filename)
    raw_bytes = _request(url, user_agent)
    raw = raw_bytes.decode("utf-8", errors="replace")
    return html_to_text(raw), url


def fetch_public_contracts(
    output_dir: Path,
    *,
    limit: int = 3,
    user_agent: str = DEFAULT_USER_AGENT,
    queries: list[str] | None = None,
) -> list[ContractRecord]:
    """
    Fetch real SEC EDGAR EX-10 contracts into output_dir.

    Returns metadata records for each saved contract.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    active_queries = queries or SEARCH_QUERIES
    seen_keys: set[str] = set()
    records: list[ContractRecord] = []

    for query in active_queries:
        if len(records) >= limit:
            break
        time.sleep(REQUEST_DELAY_SEC)
        hits = search_ex10_contracts(query, user_agent=user_agent)
        for hit in hits:
            if len(records) >= limit:
                break
            dedupe_key = f"{hit['accession']}:{hit['filename']}"
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            time.sleep(REQUEST_DELAY_SEC)
            try:
                text, url = download_contract_text(
                    hit["cik"],
                    hit["accession"],
                    hit["filename"],
                    user_agent=user_agent,
                )
            except urllib.error.HTTPError:
                continue

            if len(text) < MIN_CONTRACT_CHARS:
                continue

            company_slug = _slugify(hit["company"].split("(")[0])
            contract_id = f"edgar_{company_slug}_{hit['file_type'].lower().replace('-', '')}"
            if any(r.id == contract_id for r in records):
                contract_id = f"{contract_id}_{len(records) + 1}"

            local_name = f"{contract_id}.txt"
            local_path = output_dir / local_name
            local_path.write_text(text, encoding="utf-8")

            record = ContractRecord(
                id=contract_id,
                source="sec_edgar",
                company=hit["company"],
                cik=hit["cik"],
                form=hit["form"],
                file_type=hit["file_type"],
                file_description=hit["file_description"],
                filing_date=hit["filing_date"],
                accession=hit["accession"],
                filename=hit["filename"],
                url=url,
                local_path=str(local_path.as_posix()),
                char_count=len(text),
            )
            records.append(record)

    return records


def write_manifest(records: list[ContractRecord], manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": "sec_edgar",
        "description": "Real public material contracts fetched from SEC EDGAR EX-10 exhibits.",
        "contracts": [asdict(r) for r in records],
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_manifest(manifest_path: Path) -> dict:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch real public contracts from SEC EDGAR into fixtures."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("legalDocs/contracts/public"),
        help="Directory for fetched contract text files",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("legalDocs/contracts/manifest.json"),
        help="Path for manifest JSON",
    )
    parser.add_argument("--limit", type=int, default=3, help="Number of contracts to fetch")
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="SEC-required User-Agent string (include contact email)",
    )
    args = parser.parse_args()

    records = fetch_public_contracts(
        args.output_dir,
        limit=args.limit,
        user_agent=args.user_agent,
    )
    if not records:
        raise SystemExit("No contracts fetched. Try different queries or date range.")

    write_manifest(records, args.manifest)
    print(f"Fetched {len(records)} contracts:")
    for record in records:
        print(f"  - {record.id}: {record.char_count} chars ({record.url})")
    print(f"Manifest written to {args.manifest}")


if __name__ == "__main__":
    main()
