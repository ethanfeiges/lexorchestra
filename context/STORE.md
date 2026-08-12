# LexOrchestra — Context Store

> Project memory for implementation. Update this file as decisions are made and code is added.

---

## Purpose

LexOrchestra runs parallel LLM subtasks on contracts, keeps the parsed document as the single source of truth (SoT), and verifies that model outputs are grounded in that document.

**Committed experiments:** [`experimentDocs/EXPERIMENTS.md`](../experimentDocs/EXPERIMENTS.md). Findings — [`experimentDocs/FINDINGS.md`](../experimentDocs/FINDINGS.md).

---

## Core idea (three parts)

1. **SoT** — The contract, parsed into clauses with stable IDs and text spans. All claims must reference this.
2. **Orchestration** — Parallel agents (extract, playbook check) run on different models; outputs merge at a verifier.
3. **Grounding** — Reject or flag answers that cite clauses that do not exist or do not match the document text.

**Key separation:** The SoT layer owns the document. The orchestration layer never treats model output as truth — it only produces *claims* that get checked against the SoT.

### What this experiment actually is

Yes — at its core, LexOrchestra uses **orchestration to run legal subtasks in parallel**, then **validates every answer against a canonical SoT**. The research question is not "can an LLM read a contract?" but:

> When multiple models produce answers in parallel, and the environment includes **plausible but wrong document representations**, does orchestration + SoT validation improve outcomes vs trusting model output?

The nuance is in **where errors come from** and **what you're measuring**. A naive setup (one clean SoT, mechanical string match, easy questions) will score ~100% and prove nothing. The experiment must include **noise** so accuracy separates strategies and models.

---



## Architecture

```
Contract (PDF/DOCX)
    → Parser → Clause store (SoT)     ← canonical document lives here
                    ↓
              Orchestrator            ← models read SoT, produce claims
                    ↓
              Grounding verifier      ← checks claims against SoT
                    ↓
              Result (grounded answers + flags)
```

---



## SoT layer — how it works



### What problem it solves

LLMs read a contract and answer questions, but they can:

- Cite a section that does not exist ("Section 9.4" when the doc only has 8 sections)
- Paraphrase or misquote language ("liability capped at $500K" when the doc says $1M)
- Sound confident while being wrong

The SoT layer fixes this by making the **parsed document** the only authority. Models do not "remember" the contract — they must point to a specific clause ID and quote in the store. The verifier checks those pointers mechanically.

Think of SoT as a **numbered index of the contract**. Every answer must say: "I am talking about entry `c-012`, and here is the exact text I mean."

### What it does (step by step)

1. **Ingest** — Take one raw file (PDF or DOCX).
2. **Extract text** — Pull plain text out of the file (library TBD: pymupdf, python-docx, etc.).
3. **Split into clauses** — Break the text into meaningful chunks. v1 uses simple rules: split on numbered headings (`1.`, `1.1`, `Section 4`) or blank-line paragraphs if structure is unclear.
4. **Assign stable IDs** — Each chunk gets an ID that never changes for that document run (e.g. `c-001`, `c-002`, …). IDs are assigned in document order.
5. **Record spans** — Store character offsets so you can map back to the original text and highlight citations in a UI later.
6. **Persist** — Save the clause list as the SoT for this document. It is **read-only** for the rest of the run — nothing in orchestration writes back to it.



### What the clause store looks like

After parsing a contract snippet, the SoT might look like:


| id    | text (abbreviated)                                       | start | end  |
| ----- | -------------------------------------------------------- | ----- | ---- |
| c-001 | "This Master Services Agreement ('Agreement') is …"      | 0     | 412  |
| c-002 | "1. Definitions. 'Services' means …"                     | 413   | 890  |
| c-003 | "2. Term. This Agreement begins on the Effective Date …" | 891   | 1200 |
| c-004 | "3. Limitation of Liability. In no event shall …"        | 1201  | 1580 |


The SoT is not embeddings, not a vector DB, not model memory. It is a **structured list of the actual contract text**, addressable by ID.

### What the SoT layer exposes to the rest of the system

Other layers call into SoT through a small interface:

- `get_all_clauses()` — return the full list (used when sending context to models)
- `get_clause(id)` — return one clause by ID (used by the verifier)
- `document_id` — identifier for this parsed document

The orchestration layer **reads** from docProcessing. It never modifies it.

### What goes into the model prompt

When an agent runs, it receives the clause list (or a truncated version for long docs) plus the task instructions. Example prompt fragment:

```
You are analyzing a contract. Here are the clauses:

[c-001] This Master Services Agreement ...
[c-004] 3. Limitation of Liability. In no event shall ...

Task: Does the contract cap liability? Respond with JSON claims only.
Each claim must include: statement, clause_id, quote (exact substring from that clause).
```

The model's job is to produce claims that **reference** SoT entries. The model is not the source of truth — the clause store is.

### What SoT does *not* do (v1)

- Track amendments or "this clause replaced that clause"
- Merge multiple documents (MSA + SOW)
- Decide which model is right — that is orchestration + grounding

---



## Orchestration layer — how it works



### What problem it solves

A contract review is not one question — it is several subtasks that can run independently:

- "What does the liability section say?"
- "Does this contract pass our firm's playbook rules?"

Different models may be better at different tasks, and running tasks in parallel is faster than one serial prompt. Orchestration is the **coordinator**: it decides what to run, on which model, in what order, and how to collect the results.

Orchestration does **not** decide what is true. It only runs workers and hands their output to the grounding verifier.

### The two tasks (v1)


| Task       | Question it answers                                  | Example output claim                                        |
| ---------- | ---------------------------------------------------- | ----------------------------------------------------------- |
| `extract`  | What does the document say about X?                  | "Liability is capped at direct damages" → cites `c-004`     |
| `playbook` | Does the document satisfy rule Y from our checklist? | "Fails playbook: no mutual indemnification" → cites `c-007` |


Each task has:

- A **prompt template** (instructions + SoT clause list + task-specific question or rules)
- One or more **models** assigned to it
- An expected **response schema** (JSON list of claims)



### Playbook input

The playbook is a separate config file (YAML in v1), not part of SoT:

```yaml
rules:
  - id: liability_cap
    question: "Is there a limitation of liability clause?"
  - id: mutual_indemnity
    question: "Is indemnification mutual?"
```

SoT = the contract. Playbook = your firm's checklist. Orchestration combines both when running the `playbook` task.

### Execution flow

```
1. Load document → build SoT (clause store)
2. Load playbook config (if running playbook task)
3. Build task list: [extract, playbook]
4. For each task, for each assigned model:
       spawn async LLM call with (prompt + SoT clauses)
5. Wait for all calls to finish (parallel)
6. Parse each response into Claim objects
7. Pass all claims to grounding verifier
8. Return RunResult
```

Visually, for `parallel_grounded` with two models:

```
                    ┌─→ GPT    → extract  → claims A
SoT + playbook ──→ orchestrator ─┼─→ Claude → extract  → claims B
                    ├─→ GPT    → playbook → claims C
                    └─→ Claude → playbook → claims D
                              ↓
                    grounding verifier (checks A,B,C,D against SoT)
                              ↓
                    merged RunResult
```



### What orchestration produces

Each LLM call returns raw JSON. Orchestration normalizes it into:

```python
{
  "task": "playbook",
  "model": "claude-sonnet",
  "claims": [
    {
      "statement": "Contract includes a limitation of liability clause",
      "clause_id": "c-004",
      "quote": "In no event shall either party's aggregate liability exceed"
    }
  ]
}
```

Orchestration tags every claim with **which task** and **which model** produced it. That provenance matters for benchmarking ("Claude hallucinated more on playbook than GPT") and for conflict resolution.

### Two strategies (what orchestration varies)


| Strategy            | What orchestration does differently                                                         |
| ------------------- | ------------------------------------------------------------------------------------------- |
| `single`            | One model runs both tasks sequentially. Baseline: no parallelism.                           |
| `parallel_grounded` | Different models and/or tasks run at the same time; verifier filters bad claims at the end. |


Same SoT, same verifier, same tasks — only the **scheduling and model assignment** change. That makes benchmarks fair: you are measuring whether parallel multi-model orchestration helps, not changing the definition of truth.

### Conflict handling (orchestration's job ends before this)

When two models both produce **grounded** claims about the same playbook rule but disagree (one says pass, one says fail), orchestration passes both to the verifier/merger. Orchestration itself does not pick a winner — the merger step after grounding does (prefer higher quote match; if tied, flag `needs_review`).

### What orchestration does *not* do

- Parse the document (SoT layer)
- Check if a citation is valid (grounding layer)
- Store long-term memory across documents (no cross-run state in v1)

---



## End-to-end example

**Input:** One services agreement (e.g. MSA) + a 2-rule playbook.

**Step 1 — SoT builds the index**

Parser produces 47 clauses (`c-001` … `c-047`). Stored in SQLite/JSON. Nothing else runs until this finishes.

**Step 2 — Orchestration fans out**

Four LLM calls in parallel:

- GPT → `extract` ("summarize liability terms")
- Claude → `extract` (same question)
- GPT → `playbook` (check liability_cap + mutual_indemnity rules)
- Claude → `playbook` (same rules)

Each call receives the full clause list from SoT in its prompt.

**Step 3 — Models return claims**

Claude playbook returns:

```json
{ "statement": "Liability cap present", "clause_id": "c-004", "quote": "In no event shall..." }
```

GPT playbook returns:

```json
{ "statement": "Liability cap present", "clause_id": "c-009", "quote": "Payment terms are net-30" }
```

**Step 4 — Grounding verifier checks against SoT**

- Claude's claim: `c-004` exists, quote matches → **grounded**
- GPT's claim: `c-009` exists but quote is about payment, not liability → **ungrounded** (`text_mismatch`)

**Step 5 — Result**

User sees: liability cap **present** (Claude, grounded in `c-004`). GPT's claim dropped. No human had to catch the bad citation.

That is the full loop: **SoT holds truth → orchestration gathers opinions → verifier enforces truth.**

### Layer responsibilities (quick reference)


| Layer             | Owns              | Input                   | Output                            |
| ----------------- | ----------------- | ----------------------- | --------------------------------- |
| **SoT**           | The contract text | PDF/DOCX                | Clause store (IDs + text)         |
| **Orchestration** | Running LLM tasks | SoT + playbook + config | Raw claims (tagged by model/task) |
| **Grounding**     | Citation validity | Claims + SoT            | Grounded results + flags          |


---



### Grounding verifier

For each claim:

1. `clause_id` exists in SoT → else **ungrounded** (`missing_clause`).
2. `quote` matches clause text (exact or fuzzy threshold) → else **ungrounded** (`text_mismatch`).
3. Otherwise **grounded**.

When multiple models return grounded claims for the same question:

- Same `clause_id` + similar statement → accept.
- Conflict → prefer claim with higher quote match score; if tie, flag `needs_review`.

No separate arbiter model in v1.

## Experiment design — why this is not trivially 100%



### Why a naive version hits ~100% accuracy

If you only:

- Give agents one perfectly parsed SoT
- Ask simple yes/no playbook questions
- Verify with exact substring match against that same SoT

…then the **verifier** will always reject hallucinated clause IDs, and task accuracy will be high whenever the model reads competently. That tests string matching, not orchestration under realistic confusion.

### What makes it a real experiment

Introduce **SoT candidates** — multiple document representations for the same contract, some valid and some invalid. This mirrors real legal workflows:

- Wrong attachment (draft vs executed copy)
- Stale cache (old parse before redlines)
- OCR/parsing errors (missing or garbled clauses)
- Injected or hallucinated clauses that look plausible

Agents may **see** several SoT versions. The system keeps one **canonical** SoT for verification. The experiment measures whether the pipeline:

1. Produces correct task answers (playbook pass/fail, extraction)
2. Grounds citations in the **canonical** SoT, not a decoy
3. Handles disagreement when models cite different (valid-looking) stores



### SoT candidate labels

For each document, build a **SoT bundle** with one true version and up to four fakes. Labels describe what each version *represents* — not arbitrary version numbers.

| `label` | Valid? | What it simulates |
|---------|--------|-------------------|
| `signed_contract` | **yes** | The real executed contract. Verifier uses this only. ("Canonical" in docs = this label.) |
| `draft_missing_section` | no | Old draft before a section was added (liability clause missing) |
| `outdated_wrong_terms` | no | Stale cached copy with wrong dollar amounts or terms |
| `bad_parse_extra_clause` | no | Bad parse that invented a clause not in the real doc |
| `bad_parse_wrong_ids` | no | Same text, but clause IDs scrambled during re-parse |

Internal `corruption` field (`missing_clause`, `altered_text`, etc.) is for code — labels are for humans and prompts.

Invalid candidates are **hard negatives**: they look usable, and claims grounded in them can pass a superficial read but fail against `signed_contract`. All decoys are **programmatic corruptions of a real parsed MSA** — never separate synthetic source documents.

### Contract data policy

- **Canonical documents:** Real MSAs only, from SEC EDGAR EX-10 exhibits in `fixtures/contracts/public/`.
- **Noise / decoys:** Generated by `build_bundle()` from the canonical parse of that real MSA (`missing_clause`, `altered_text`, `extra_clause`, `reordered`).
- **No synthetic contract fixtures.** Do not add fake MSAs for tests or benchmarks.
- **Fetch more:** `python -m benchmark.fetch_contracts` — see `fixtures/contracts/manifest.json` for source URLs.
- **Primary test MSA:** `fixtures/contracts/public/edgar_edgemode_inc_ex10.1.txt` (Edgemode ↔ Cudo Ventures).

### How noise enters the pipeline

**1. Prompt noise — agents see multiple SoTs**

Orchestration passes 2–3 labeled candidates into each subagent prompt:

```
Document versions (cite from signed_contract only):

[signed_contract]     c-004: Limitation of Liability. In no event shall... (cap: $1M)
[outdated_wrong_terms] c-004: Limitation of Liability. In no event shall... (cap: $500K)  ← wrong
[draft_missing_section] c-003: Term. This Agreement begins...  ← liability section gone
```

Subagents must complete `extract` / `playbook` tasks. Some will incorrectly cite decoy labels or quotes that match a fake version. The **verifier always checks against `signed_contract` only** — so decoy-grounded claims become `ungrounded` or task-wrong.

**2. Output noise — synthetic bad claims in unit tests**

For verifier/orchestration tests without LLM cost, inject claims programmatically (wrong ID, wrong quote, quote matching decoy not canonical). Ensures the pipeline catches known failures.

### Experimental conditions

Compare strategies under increasing difficulty:


| Condition      | Agent sees                                   | Verifier uses | What it tests                                              |
| -------------- | -------------------------------------------- | ------------- | ---------------------------------------------------------- |
| `clean`        | canonical only                               | canonical     | Baseline — expect high scores                              |
| `noisy_prompt` | canonical + 1–2 invalid candidates           | canonical     | Do agents cite decoys? Does parallel + verify beat single? |
| `unlabeled_noisy` | decoys with anonymous `version_N` labels    | canonical     | Ablation: label authority vs quote verification            |
| `noisy_task`   | canonical + decoys + ambiguous playbook rule | canonical     | Task accuracy drops when inference is required (spec only)   |


**Primary metrics** (expect spread across conditions, not 100% everywhere):


| Metric                       | Meaning                                                               |
| ---------------------------- | --------------------------------------------------------------------- |
| **Task accuracy**            | Playbook/extract answer matches answer key                            |
| **Canonical grounding rate** | Claims verified against canonical SoT / total claims                  |
| **Decoy citation rate**      | Claims that match an invalid SoT but not canonical — key failure mode |
| **Cross-model agreement**    | When models disagree, is the grounded winner correct?                 |


Expect `clean` ≈ high, `noisy_prompt` ≈ 70–90% depending on model, `noisy_task` lower.

### End-to-end flow with SoT candidates

```
Contract PDF
    → build SoT bundle (canonical + invalid variants)
    → orchestrator runs subtasks in parallel
          each agent receives: tasks + playbook + [canonical, decoy₁, decoy₂]
    → agents return claims (may cite any candidate they saw)
    → verifier checks claims ONLY against canonical
    → metrics: task accuracy, decoy rate, grounding rate
```

The orchestration layer's job expands slightly: it **assembles the prompt bundle** (which SoT candidates each agent sees) and **never** tells the verifier about decoys. Verifier has one truth.

### What you are NOT testing

- Whether a mechanical verifier rejects obviously fake strings (that's unit tests, expect ~100%)
- Whether one smart model alone can read a clean contract (baseline, not the contribution)



### What you ARE testing

- Under document ambiguity, does **parallel multi-model + canonical verification** beat single-model?
- How often do models **anchor on invalid SoT** when it is present in context?
- Can the pipeline still return correct playbook answers when decoys omit or alter key clauses?

---



## Data model



### `SoTBundle` (per document)

```python
document_id: str
canonical: list[Clause]           # verifier uses this only
candidates: list[{                 # what agents may see in prompts
    label: str                    # e.g. "signed_contract", "outdated_wrong_terms"
    valid: bool
    clauses: list[Clause]
    corruption: str | None        # "missing_clause" | "altered_text" | ...
}]
```



### `Clause` (SoT)

```python
id: str
text: str
start_offset: int
end_offset: int
```



### `Claim` (agent output)

```python
statement: str
clause_id: str
quote: str
sot_label: str | None   # which candidate the agent believes it cited (optional, for decoy metric)
```



### `VerifiedClaim`

```python
claim: Claim
status: "grounded" | "ungrounded"
reason: str | None          # "missing_clause" | "text_mismatch"
model: str
task: str
```



### `RunResult`

```python
document_id: str
strategy: "single" | "parallel_grounded"
verified_claims: list[VerifiedClaim]
needs_review: list[Claim]
```

---



## Benchmark

- **Data:** Real MSAs from SEC EDGAR (`fixtures/contracts/public/`) + answer keys for playbook rules and expected canonical clause IDs.
- **SoT bundles:** For each real MSA, auto-generate decoy candidates from canonical via `build_bundle()` (`missing_clause`, `altered_text`, `extra_clause`, `reordered`).
- **Conditions:** `clean`, `noisy_prompt`, `noisy_task` (see Experiment design above).
- **Metrics:** Task accuracy, canonical grounding rate, decoy citation rate, latency/cost per strategy.
- **Injected bad claims:** Programmatic fake agent claims in verifier unit tests (expect ~100% — separate from LLM eval; not synthetic contract documents).

---



## Tech stack


| Piece         | Choice                                   |
| ------------- | ---------------------------------------- |
| Language      | Python 3.11+                             |
| API           | FastAPI (when needed)                    |
| Orchestration | asyncio + pluggable model clients        |
| SoT storage   | JSON files or SQLite for v1              |
| Models        | OpenAI + Anthropic APIs; optional Ollama |


---



## Repo layout (target)

```
lexorchestra/
├── context/STORE.md          # this file
├── docProcessing/            # parse contracts, build decoy bundles
├── orchestrator/             # tasks, parallel runner
├── grounding/                # verifier
├── models/                   # LLM client adapters
├── benchmark/                # answer keys, conditions, metrics
└── (no CLI — use docProcessing.io.build_bundle_from_file)
```

---



## Development workflow (all phases)

**Rule:** The **agent runs tests itself** after every code change. Do not ask the user to run pytest. Do not mark a phase or task complete until tests pass.

### Agent responsibility (required)

After implementing or editing code, the agent must:

```powershell
python -m pytest tests/ -q
```

Use the Shell tool — do not tell the user to run this. If tests fail, fix and re-run until green, then report the result in chat.

### Optional backup (Cursor hooks)

`.cursor/hooks.json` may also run pytest on file edits and at agent stop. Hooks are supplementary; the agent still runs tests explicitly and reports outcomes.

### Agent checklist (each implementation step)

1. Read the phase prompt (`context/phases/*.md`) and `STORE.md`.
2. Implement the smallest correct change.
3. **Run `python -m pytest tests/ -q` yourself** (Shell tool).
4. Update `STORE.md` implementation status and decisions log.
5. Do not proceed to the next phase with failing tests.

Future phase prompts should include: *"Run pytest yourself before finishing; do not ask the user to run tests."*

---



## Scope



### In scope (v1)

- Single-document parse and canonical clause store
- **SoT bundle generator** (canonical + invalid candidates)
- Two tasks: extract + playbook check
- Parallel execution across 2+ models
- Grounding verifier against **canonical only**
- Benchmark: `clean` vs `noisy_prompt` conditions, decoy citation metric



### Out of scope (v1)

- Amendment chains / multi-doc supersession
- Cross-document conflict detection
- Arbiter/judge LLM
- Full web UI (optional later)
- Five-type violation taxonomy — use grounded/ungrounded only

---



## Implementation status


| Component            | Status      | Notes                        |
| -------------------- | ----------- | ---------------------------- |
| Context store        | done        | —                            |
| Documents layer spec | done        | `context/phases/DOCUMENTS.md`      |
| Clause parser        | done        | `docProcessing/parser.py` — txt + optional pdf/docx |
| Clause store         | done        | `docProcessing/store.py` — lookup + quote_matches |
| Decoy bundle generator | done      | `docProcessing/bundle.py` — 4 deterministic corruptions |
| Prompt formatter     | done        | `docProcessing/prompt.py`              |
| Documents I/O        | done        | `docProcessing/io.py` — build_bundle_from_file |
| Documents tests      | done        | `tests/docProcessing/` — 23 tests      |
| Public contract fetch | done        | `benchmark/fetch_contracts.py` — SEC EDGAR EX-10 |
| Public contract fixtures | done     | `fixtures/contracts/public/` + `manifest.json` |
| Auto-test hooks        | done        | `.cursor/hooks.json` — pytest on edit + agent stop |
| Model clients        | done        | `models/` — Gemini adapter + test stubs |
| Orchestrator         | done        | `orchestrator/` — tasks, runner, run_benchmark_case |
| Grounding verifier   | done        | `grounding/` — canonical-only verify + decoy detect |
| Benchmark            | done        | `benchmark/answers/`, Gemini experiment runner |
| Gemini baseline      | done        | `experiments/live_gemini/` — committed Gemini results |
| CI + doc sync        | done        | `.github/workflows/ci.yml`, `scripts/sync_experiment_docs.py` |


---



## Decisions log


| Date       | Decision                            | Rationale                                                   |
| ---------- | ----------------------------------- | ----------------------------------------------------------- |
| 2026-08-12 | Project name: LexOrchestra          | Legal + orchestration; memorable                            |
| 2026-08-12 | Two strategies only                 | Enough to show orchestration value without benchmark sprawl |
| 2026-08-12 | Grounding = binary + reason string  | Avoid large enum hierarchies                                |
| 2026-08-12 | Single doc, no amendment graph      | Reduces edge cases; still demonstrates SoT                  |
| 2026-08-12 | Context store at `context/STORE.md` | Single memory file for agents and future sessions           |
| 2026-08-12 | SoT bundles with invalid candidates | Prevents trivial 100% accuracy; models must survive decoys  |
| 2026-08-12 | Verifier uses signed_contract only  | Decoys in prompt, never in truth                            |
| 2026-08-12 | Descriptive SoT labels            | signed_contract, draft_missing_section, etc. |
| 2026-08-12 | No CLI                            | `build_bundle_from_file()` only; tests/benchmark call Python API |
| 2026-08-12 | Rule-based parser (no ML)         | Split on numbered headings or paragraph fallback; pymupdf/python-docx optional |
| 2026-08-12 | Pydantic v2 for SoT models        | Validation on Clause offsets and SoTBundle invariants |
| 2026-08-12 | Flat `docProcessing/` at repo root          | Workspace is `AI Orchestration/`; no nested lexorchestra package |
| 2026-08-12 | SEC EDGAR for real contracts      | Fetch EX-10 exhibits via EFTS API; stdlib only; manifest tracks source URLs |
| 2026-08-12 | Auto-run tests on every change    | Agent runs pytest via Shell after edits; never prompt user; hooks optional backup |
| 2026-08-12 | Orchestration phase implemented   | Parallel runner, grounding verifier, answer keys, eval harness |
| 2026-08-12 | Gemini-only experiments           | All benchmark runs via Gemini API; mock profiles removed |
| 2026-08-12 | MAX_CLAUSE_LENGTH 12000           | Live prompts must include deep clause text (ICC at ~7k) |
| 2026-08-12 | experimentDocs/EXPERIMENTS.md + sync rule   | Single catalog; agent updates docs when baselines change |
| 2026-08-12 | Default model gemini-2.0-flash    | NuScale decoy citation under noise in prior runs |


---



## Open questions

- Parser: rule-based section detection vs off-the-shelf (e.g. unstructured.io).
- Chime in live/ablation matrices: 184 clauses / 284k chars — prompt size vs coverage tradeoff.
- Live Gemini Pro (`gemini-2.5-pro`) vs Flash: quality vs cost tradeoff.
- `noisy_task` condition: spec'd but not in default committed matrices.

