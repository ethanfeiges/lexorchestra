# Multi-type expansion — five document types

> **Design spec** for expanding LexOrchestra beyond MSAs to five real SEC EDGAR document types with parallel source-probe orchestration.

---

## Goal

Measure whether orchestration + canonical verification keeps agents grounded across **five document families**, not just Master Services Agreements. Each type uses one **primary fixture** (real filed contract), the same decoy bundle pipeline, and type-specific benchmark tasks.

---

## Document types

| Type | Primary fixture | SEC source |
|------|-----------------|------------|
| **MSA** | `edgar_edgemode_inc_ex10.1` | EdgeMode ↔ Cudo Ventures MSA |
| **Software license** | `edgar_amd_ex10.79` | AMD ↔ Broadcom core license |
| **NDA** | `edgar_hg_holdings_inc_ex10.2` | HG Holdings confidentiality agreement |
| **Employment** | `edgar_emerald_holding_inc_ex10.43` | Emerald executive employment agreement |
| **Credit** | `edgar_enviri_corp_ex10.1` | Enviri credit agreement amendment |

Additional MSAs (NuScale, Aspira, Pulmatrix, Chime) remain as alternates; the default experiment matrix uses **one primary per type** (5 documents × 2 conditions = **10 runs**).

---

## Architecture (unchanged core)

```
Real filing (any type)
    → parse_document() → canonical clauses
    → resolve_corruption_plan(document-specific) → build_bundle(seed, corruption_mode=...)
    → signed_contract + decoys
    → parallel subtasks → verify_claims() → score vs answer key
```

### What changed

| Layer | Change |
|-------|--------|
| `legalDocs/contracts/manifest.json` | `document_type`, `primary_fixture` per contract |
| `benchmark/document_types.py` | Type registry, EDGAR query map, `primary_fixtures()` |
| `docProcessing/corruption_plan.py` | Document-specific corruption plans (money, duration, obligation, etc.) |
| `docProcessing/bundle.py` | Applies plans to four decoy types; type-tuned missing-clause targets |
| `benchmark/answers/*.yaml` | `document_type` field; one key file per primary fixture |
| `orchestrator/runner.py` | New `parallel_source_probe` strategy |
| `benchmark/metrics.py` | `source_fidelity`, `decoy_probe_match_rate`, `explicit_mislabel_rate` |

### What did not change

- Canonical SoT is still extrinsic (parsed filing, not model output).
- Verifier always checks against `bundle.canonical`.
- Decoys are still programmatic corruptions of the same parse — but edits are **document-specific** (not global substitution tables).

---

## Document-specific corruption plans

Before building decoys, `resolve_corruption_plan()` scans the canonical clauses for corruptible spans:

| Category | Examples extracted from the contract |
|----------|--------------------------------------|
| `money` | `$303,548.72`, `€ 5,000,000` |
| `duration` | `thirty (30) days`, `12 months`, `90 days' notice` |
| `percentage` | `three per cent (3%)`, fee indexation caps |
| `date` | `January 21, 2025` |
| `obligation` | `shall` / `may` / `shall not` |
| `jurisdiction` | `Florida`, `laws of New York` |
| `rate` | `$130/hour` |

**Local mode** (default, no API): replacements swap or scale values using spans found in *that* document (e.g. replace `30 days` with `14 days` if both appear in the filing).

**Gemini mode**: one API call per `(document, seed)` produces plausible wrong edits by category. Results are cached under `legalDocs/corruption_plans/{document_id}_seed{seed}_{hash}.json`.

```powershell
python scripts/generate_corruption_plans.py --mode gemini --seed 42
```

```python
from docProcessing.io import build_bundle_from_file

bundle = build_bundle_from_file(path, seed=42, corruption_mode="auto")
```

Same `(document, seed)` → identical decoys (reproducible benchmarks). Different document or seed → different corruptions (not predictable across filings).

---

## Orchestration strategies

### `parallel_grounded` (default)

Extract ∥ playbook on the same prompt bundle. Both agents instructed to cite `signed_contract`.

### `parallel_source_probe` (new)

Four parallel agents on the same bundle:

| Agent | Task id | Instruction |
|-------|---------|-------------|
| Canonical extract | `extract` | Cite `signed_contract` only |
| Playbook | `playbook` | Evaluate rules against `signed_contract` |
| Decoy extract | `extract_decoy` | Cite first decoy label in prompt (e.g. `outdated_wrong_terms`) |
| Discrimination extract | `extract_discriminate` | Answer from signed copy; must set `sot_label` |

**Scoring:**

- **Task accuracy** — canonical tasks only (`extract`, `playbook`).
- **Source fidelity** — grounding rate on canonical tasks.
- **Decoy probe match rate** — decoy probe claims matching decoy text.
- **Explicit mislabel rate** — discrimination probe with `sot_label != signed_contract`.

Truth is never voted on by agents; the verifier decides.

### `parallel_cross_type_discrimination` (portfolio)

One **shared prompt** containing all five primary documents, each clause tagged `[signed_contract:{document_id}]`. Parallel **type-specialist** agents — one per document — each run three tasks:

| Agent | Task id | Instruction |
|-------|---------|-------------|
| Type specialist playbook | `playbook:{document_id}` | Evaluate rules against assigned document only |
| Type specialist extract | `extract:{document_id}` | Answer extract question from assigned document |
| Discrimination extract | `extract_discriminate:{document_id}` | Same as extract; must set `document_id` and `sot_label` |

**Portfolio conditions:**

| Condition | Effect |
|-----------|--------|
| `portfolio_clean` | Labels match content (correct routing) |
| `cross_type_mislabeled` | One deterministic doc-pair swap (wrong label on one block) |

**Scoring:**

- **Task accuracy** — canonical portfolio tasks (`extract:*`, `playbook:*`) vs answer keys.
- **Source fidelity** — grounding rate on canonical portfolio tasks.
- **Cross-document citation rate** — claims anchored on a different document than assigned.
- **Explicit mislabel rate** — discrimination tasks with `document_id != expected`.

Entry point: `orchestrator/portfolio_run.py` · case file: `benchmark/portfolio_cases/primary_five.yaml`.

Portfolio runs cap concurrent Gemini API calls at **5** (`max_concurrent` in `run_parallel_cross_type_discrimination`) to reduce rate-limit failures on free tier.

```powershell
python -m benchmark.run_experiment --provider gemini `
  --strategies parallel_cross_type_discrimination `
  --conditions portfolio_clean cross_type_mislabeled
```

---

## Default experiment matrix

| Axis | Value |
|------|--------|
| Documents | 5 primaries (one per type) |
| Conditions | `clean`, `noisy_prompt` |
| Strategy | `parallel_grounded` |
| Runs | 10 |

```powershell
python -m benchmark.run_experiment --provider gemini
```

Source-probe runs (more API calls):

```powershell
python -m benchmark.run_experiment --provider gemini --strategy parallel_source_probe --documents edgar_edgemode_inc_ex10.1 --conditions noisy_prompt
```

---

## Adding a new document type

1. Fetch a real EX-10 exhibit: `python -m benchmark.fetch_contracts --query "..."`.
2. Tag `document_type` and `primary_fixture` in `manifest.json`.
3. Author `benchmark/answers/{document_id}.yaml` from canonical parse.
4. Optionally add a corruption target in `docProcessing/bundle.py` → `CORRUPTION_TARGETS` (for `missing_clause` / fallback targeting).
5. Validate: `python -c "from benchmark.answers_validate import assert_all_answers_valid; assert_all_answers_valid()"`.

---

## Related docs

- [`context/STORE.md`](../STORE.md) — project memory
- [`context/phases/DOCUMENTS.md`](DOCUMENTS.md) — parsing and bundles
- [`context/phases/ORCHESTRATION.md`](ORCHESTRATION.md) — orchestration phase
- [`experimentDocs/EXPERIMENTS.md`](../../experimentDocs/EXPERIMENTS.md) — Gemini runs
