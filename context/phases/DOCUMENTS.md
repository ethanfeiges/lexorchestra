# Documents layer — contract parsing and bundles

> **Phase spec** for the `docProcessing/` package: parse contracts into clauses, build decoy bundles, format prompt blocks.
>
> **Gemini experiments:** [`experimentDocs/EXPERIMENTS.md`](../experimentDocs/EXPERIMENTS.md). Read [`context/STORE.md`](../STORE.md) for full project context.

---

## Your role

You are implementing the **`docProcessing/` package** for LexOrchestra — a legal-document orchestration experiment. This layer parses contract files, indexes clauses, and builds decoy bundles that later phases (orchestration, grounding, benchmark) depend on.

**Do not implement orchestration, LLM clients, or the grounding verifier in this phase.** Build only what is listed under Deliverables.

---

## Goal

Turn a raw contract file into:

1. A **canonical clause store** — the single source of truth for verification.
2. An **SoT bundle** — canonical plus programmatically generated invalid candidates (noise) for the experiment.

Downstream layers will pass SoT candidates to subagents in prompts but verify claims against **canonical only**. Your job is to produce both structures reliably and expose a clean Python API.

---

## Why this phase matters

The experiment measures whether AI orchestration can distinguish **noise vs actual SoT** under subtasks. Invalid SoT candidates must be plausible hard negatives — not random garbage — so models can realistically cite them. The SoT phase defines and generates that noise.

---

## Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | `docProcessing/models.py` | `Clause`, `SoTCandidate`, `SoTBundle` dataclasses / Pydantic models |
| 2 | `docProcessing/parser.py` | PDF/DOCX/TXT → canonical `list[Clause]` |
| 3 | `docProcessing/store.py` | Read-only store over canonical clauses + lookup API |
| 4 | `docProcessing/bundle.py` | Generate invalid candidates from canonical |
| 5 | `docProcessing/prompt.py` | Turns a bundle into **text for LLM prompts** (not a CLI — see below) |
| 6 | `docProcessing/io.py` | Save/load bundles + `build_bundle_from_file()` entry point |
| 7 | `tests/docProcessing/` | Unit tests for parser, store, bundle generator, prompt formatter, io |
| 8 | `fixtures/contracts/public/` | Real MSAs from SEC EDGAR + `manifest.json` |

No CLI in this project — bundles are built by calling Python functions (tests and benchmark call them directly).

Update `context/STORE.md` implementation status when done.

---

## Repository layout (create this)

```
lexorchestra/
├── context/
│   ├── STORE.md
│   └── phases/
│       └── DOCUMENTS.md                 # this file
├── docProcessing/
│   ├── __init__.py
│   ├── models.py
│   ├── parser.py
│   ├── store.py
│   ├── bundle.py
│   ├── prompt.py
│   └── io.py
├── tests/
│   └── docProcessing/
│       ├── test_parser.py
│       ├── test_store.py
│       ├── test_bundle.py
│       ├── test_prompt.py
│       └── test_io.py
├── fixtures/
│   └── contracts/
│       ├── manifest.json          # SEC source metadata
│       └── public/                # real MSAs from SEC EDGAR EX-10
│           ├── edgar_edgemode_inc_ex10.1.txt
│           ├── edgar_nuscale_power_corp_ex10.15.txt
│           └── edgar_chime_financial_inc_ex10.1.txt
├── benchmark/
│   └── fetch_contracts.py         # fetch more real MSAs from SEC
├── pyproject.toml                 # or requirements.txt
└── README.md
```

Use `lexorchestra/` as package root **or** flat `docProcessing/` at repo root — pick one and stay consistent. Prefer flat layout at repo root since the workspace is already `AI Orchestration/`.

---

## Glossary

| Term | Meaning |
|------|---------|
| **MSA** | Master Services Agreement — a standard contract between a vendor and client for ongoing services. Common in legal AI demos because it has liability caps, indemnification, term, etc. |
| **Canonical / signed_contract** | The true parsed document — not a draft or decoy. |

Fixtures are **real MSAs only** — fetched from SEC EDGAR EX-10 exhibits under `fixtures/contracts/public/`. Do not use synthetic contract text.

---

## Building bundles vs formatting prompts

Two separate Python APIs — no terminal commands.

| | **`io.build_bundle_from_file()`** | **`prompt.format_candidates_for_prompt()`** |
|---|-----------------------------------|---------------------------------------------|
| **When** | Start of a run / in tests | Each LLM call (orchestration phase) |
| **Input** | Path to `.txt` contract file | `SoTBundle` or list of candidates in memory |
| **Output** | `SoTBundle` (optionally saved as JSON) | String pasted into the LLM prompt |

**Build flow (tests, benchmark, orchestration):**
```python
from pathlib import Path
from docProcessing.io import build_bundle_from_file, save_bundle

bundle = build_bundle_from_file(
    Path("fixtures/contracts/public/edgar_edgemode_inc_ex10.1.txt"),
    seed=42,
)
save_bundle(bundle, Path("tmp/edgar_edgemode_inc_ex10.1.json"))  # optional persistence
```

**Prompt flow (orchestration, later):**
```python
from docProcessing.prompt import format_candidates_for_prompt

text_block = format_candidates_for_prompt(bundle.candidates, labels=["signed_contract", "outdated_wrong_terms"])
# → inserted into LLM API call
```

`build_bundle_from_file` chains: parse → `build_bundle()`. Callers never need a CLI.

---

## Data models

Implement in `docProcessing/models.py`. Use Pydantic v2 or dataclasses with validation.

### `Clause`

```python
id: str              # "c-001", "c-002", ... zero-padded, document-order
text: str            # full clause text
start_offset: int    # char offset in extracted plain text
end_offset: int      # exclusive
```

Rules:
- IDs assigned sequentially at parse time, never reused within a document.
- `text` must equal `plain_text[start_offset:end_offset]` after normalization.

### `SoTCandidate`

```python
label: str           # see "Candidate labels" below — tells humans what this version represents
valid: bool          # True only for signed_contract (the real document)
clauses: list[Clause]
corruption: str | None   # None if valid; else internal corruption type (missing_clause, etc.)
```

### Candidate labels (use these exact strings)

Each bundle has **one true document** and **up to four fake versions**. Labels describe the *story* behind each version — what mistake it simulates in a real law firm workflow.

| `label` | Valid? | `corruption` | What it simulates |
|---------|--------|--------------|-------------------|
| `signed_contract` | **yes** | `None` | The real executed contract. **Only this one is truth.** Verifier always uses this. |
| `draft_missing_section` | no | `missing_clause` | An old draft from *before* a section was added (e.g. liability clause not in yet). |
| `outdated_wrong_terms` | no | `altered_text` | A stale cached copy with wrong numbers (e.g. $500K cap instead of $1M). |
| `bad_parse_extra_clause` | no | `extra_clause` | A corrupted parse that *invented* a clause that isn't in the real contract. |
| `bad_parse_wrong_ids` | no | `reordered` | Same contract text, but clause IDs were scrambled during a bad re-parse. |

**Terminology:** Docs may say "canonical" — that means `signed_contract`. Same thing.

**Why agents see fakes:** In a real deal room you'd have drafts, cached exports, and bad OCR side by side. The experiment tests whether models cite the signed contract or accidentally use a decoy. Labels make it obvious which is which when reading logs or prompts.

---

### `SoTBundle`

```python
document_id: str     # slug from filename or uuid
source_path: str     # original file path
canonical: list[Clause]
candidates: list[SoTCandidate]   # always includes signed_contract
```

Invariant: exactly one candidate has `valid=True`, label `signed_contract`, and its `clauses` match `canonical`.

---

## Parser (`docProcessing/parser.py`)

### Input

- `.txt` — required for v1
- `.pdf` — optional if PyMuPDF (`fitz`) available; skip gracefully if not installed
- `.docx` — optional if `python-docx` available

Start with `.txt`. PDF/DOCX are nice-to-have, not blockers.

### Text extraction

1. Read file as UTF-8 plain text (for `.txt`).
2. Normalize: unify line endings to `\n`, collapse runs of 3+ blank lines to 2.

### Clause splitting (v1 — keep simple)

Split on lines matching numbered heading patterns:

```
^\d+\.\s          # "1. Definitions"
^\d+\.\d+\.?\s    # "1.1 Term"
^Section\s+\d+    # "Section 4"
```

If no headings found, fall back to split on `\n\n` (paragraph chunks). Minimum chunk length: 40 characters; merge tiny chunks with previous.

### Output

Return `list[Clause]` with sequential IDs `c-001`, `c-002`, … and correct offsets.

### Public API

```python
def parse_document(path: Path) -> list[Clause]: ...
def parse_text(text: str, document_id: str = "inline") -> list[Clause]: ...
```

---

## Store (`docProcessing/store.py`)

Read-only wrapper over canonical clauses.

```python
class SoTStore:
    def __init__(self, clauses: list[Clause], document_id: str): ...

    @property
    def document_id(self) -> str: ...

    def get_all(self) -> list[Clause]: ...
    def get(self, clause_id: str) -> Clause | None: ...
    def contains(self, clause_id: str) -> bool: ...
    def quote_matches(self, clause_id: str, quote: str, threshold: float = 0.85) -> bool: ...
```

`quote_matches` — used later by grounding; implement now so SoT phase is testable:
- Normalize whitespace on both sides.
- Return `True` if `quote` is a substring of clause text, OR fuzzy ratio ≥ threshold (use `difflib.SequenceMatcher` — no extra deps).

---

## Bundle generator (`docProcessing/bundle.py`)

Generate invalid candidates from canonical. Each corruption is **deterministic** given a seed so benchmarks reproduce.

### Corruption types (implement all four)

Each corruption powers one decoy label (see table above):

| `corruption` | → `label` | Behavior |
|--------------|-----------|----------|
| `missing_clause` | `draft_missing_section` | Remove one clause. Default target: clause whose text contains `"liability"` (case-insensitive); else remove middle clause. Renumber IDs sequentially after removal. |
| `altered_text` | `outdated_wrong_terms` | Copy canonical; pick same target clause; replace one numeric/capital phrase via fixed substitution table (e.g. `$1,000,000` → `$500,000`, ` thirty (30) ` → ` fifteen (15) `). IDs unchanged. |
| `extra_clause` | `bad_parse_extra_clause` | Append one fake clause with plausible legal boilerplate (template string in code). New ID = next sequential. |
| `reordered` | `bad_parse_wrong_ids` | Same clause texts, shuffle order with fixed seed, reassign IDs `c-001`… in new order. |

### Public API

```python
def build_bundle(
    clauses: list[Clause],
    document_id: str,
    source_path: str,
    seed: int = 42,
    corruptions: list[str] | None = None,  # default: all four
) -> SoTBundle: ...
```

Bundle structure:
- `canonical` field = original clauses (same as `signed_contract` candidate)
- `candidates` = `[signed_contract] + [one decoy per corruption]`
- Valid candidate: `label="signed_contract"`, `valid=True`, `corruption=None`
- Invalid candidates: use labels from the table above, `valid=False`

---

## Prompt formatter (`docProcessing/prompt.py`)

**This is not a CLI command.** It is a Python function that orchestration calls when building an LLM request.

**Problem it solves:** A bundle is structured data (lists of clauses). LLMs need a single text block. `prompt.py` converts the bundle into that block.

**Example — what orchestration does later:**
```python
from docProcessing.prompt import format_candidates_for_prompt

text_block = format_candidates_for_prompt(
    bundle.candidates,
    labels=["signed_contract", "outdated_wrong_terms"],  # which versions to show the model
)
# text_block gets appended to the LLM prompt before "Task: check playbook rule X"
```

### Public API

```python
def format_candidates_for_prompt(
    candidates: list[SoTCandidate],
    labels: list[str] | None = None,  # filter which to include; None = all
) -> str: ...
```

Output format (exact):

```
Document versions (cite from signed_contract only):

[signed_contract] c-001: First clause text...
[signed_contract] c-002: Second clause text...

[outdated_wrong_terms] c-001: ...
[draft_missing_section] c-001: ...
...
```

Include a header line instructing agents to cite `signed_contract` only. Truncate individual clause text to 500 chars with `...` if longer.

Also expose:

```python
def get_candidate_by_label(bundle: SoTBundle, label: str) -> SoTCandidate | None: ...
def signed_contract_candidate(bundle: SoTBundle) -> SoTCandidate: ...  # the valid one
```

---

## I/O (`docProcessing/io.py`)

```python
def save_bundle(bundle: SoTBundle, path: Path) -> None: ...
def load_bundle(path: Path) -> SoTBundle: ...

def build_bundle_from_file(
    path: Path,
    seed: int = 42,
    corruptions: list[str] | None = None,
) -> SoTBundle:
    """Parse contract file, build SoT bundle. Primary entry point — no CLI."""
    ...
```

JSON must be human-readable (`indent=2`). `document_id` derived from filename stem.

---

## Contract fixtures (real MSAs only)

**Do not create synthetic contracts.** All canonical documents and all noise/decoy candidates must be derived from real public MSAs.

### Source

Real Master Services Agreements from [SEC EDGAR](https://www.sec.gov/edgar) EX-10 material-contract exhibits. Fetch via:

```powershell
python -m benchmark.fetch_contracts --limit 3 --user-agent "YourName you@email.com"
```

Stored under `fixtures/contracts/public/` with metadata in `fixtures/contracts/manifest.json`.

### Current fixtures

| File | Company |
|------|---------|
| `public/edgar_edgemode_inc_ex10.1.txt` | Edgemode MSA with Cudo Ventures |
| `public/edgar_nuscale_power_corp_ex10.15.txt` | NuScale amended MSA with Fluor |
| `public/edgar_chime_financial_inc_ex10.1.txt` | Chime MSA with Bancorp Bank |

Real MSAs include liability caps, indemnification, term, and payment language — giving the bundle generator realistic clauses to drop, alter, or reorder as decoys.

### Noise generation

Decoys (`draft_missing_section`, `outdated_wrong_terms`, `bad_parse_extra_clause`, `bad_parse_wrong_ids`) are **programmatic corruptions of the parsed real MSA**, not separate fake documents. The canonical `signed_contract` candidate is the true parse of the real filing.

---

## Tests (required)

Use `pytest`. No LLM calls.

### `test_parser.py`

- Parses a real MSA from `fixtures/contracts/public/` into ≥3 clauses with sequential IDs
- Offsets match actual text slices
- Heading-based split works on numbered sections (inline test string)
- Paragraph fallback works when no headings (inline test string)

### `test_store.py`

- `get` / `contains` for valid and invalid IDs
- `quote_matches`: exact substring passes; wrong quote fails; fuzzy passes close paraphrase

### `test_bundle.py`

- Bundle has 1 valid + 4 invalid candidates (default)
- `missing_clause` decoy has fewer clauses than canonical
- `altered_text` decoy: same IDs, at least one clause text differs
- `extra_clause` decoy: more clauses than canonical
- `reordered` decoy: same texts multiset, different ID mapping
- Same seed → identical bundle (deterministic)

### `test_prompt.py`

- Output contains all requested labels
- `signed_contract` label present
- Truncation works for long clauses

### `test_io.py`

- `build_bundle_from_file()` returns valid bundle from a real MSA in `public/`
- `save_bundle` / `load_bundle` round-trip preserves data

---

## Acceptance criteria

Phase is **done** when:

- [ ] `pytest tests/docProcessing/` passes
- [ ] `build_bundle_from_file()` on a real MSA in `fixtures/contracts/public/` produces a valid bundle
- [ ] All decoy candidates are corruptions of the real canonical parse (no synthetic source documents)
- [ ] `save_bundle` / `load_bundle` round-trip works
- [ ] All four corruption types produce distinct, plausible decoys
- [ ] No imports from `orchestrator/`, `grounding/`, or `models/` (LLM) — SoT is standalone
- [ ] `context/STORE.md` implementation status updated for parser, store, bundle generator

---

## Constraints

- **Python 3.11+**
- **Minimize dependencies:** stdlib + `pydantic` (optional but preferred) + `pytest`. PDF/DOCX libs optional.
- **No LLM calls** in this phase.
- **No CLI** — programmatic API only (`build_bundle_from_file`).
- **No FastAPI** in this phase.
- **Keep parser simple** — no ML, no unstructured.io unless you hit a blocker and document why in STORE.md decisions log.
- **Deterministic corruptions** — always seedable for reproducible benchmarks.
- **Do not** implement grounding verifier logic beyond `quote_matches` on the store.

---

## Integration points (for later phases — do not build now)

| Consumer | Will use |
|----------|----------|
| Orchestrator | `format_candidates_for_prompt()`, `load_bundle()` |
| Grounding verifier | `SoTStore(canonical)`, `quote_matches()` |
| Benchmark | `build_bundle_from_file()`, `load_bundle()` |

Design public APIs accordingly; keep them stable.

---

## Suggested implementation order

1. `models.py` — types first
2. `parser.py` + real MSA fixtures in `fixtures/contracts/public/`
3. `store.py` + tests
4. `bundle.py` + noise from real MSAs + tests
5. `prompt.py` + tests
6. `io.py` + `build_bundle_from_file` + tests
7. Update STORE.md status

---

## After completing this phase

The next Cursor prompt will cover **Grounding verifier** (claims → canonical check + decoy detection metric). Orchestration comes after that.

When finished, summarize in chat:
- Files created
- How to run tests (`pytest tests/docProcessing/`)
- Any decisions made (add to STORE.md decisions log)
