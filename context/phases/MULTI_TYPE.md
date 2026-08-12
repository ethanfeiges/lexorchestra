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
    → build_bundle(document_type=...) → signed_contract + decoys
    → parallel subtasks → verify_claims() → score vs answer key
```

### What changed

| Layer | Change |
|-------|--------|
| `legalDocs/contracts/manifest.json` | `document_type`, `primary_fixture` per contract |
| `benchmark/document_types.py` | Type registry, EDGAR query map, `primary_fixtures()` |
| `docProcessing/bundle.py` | Type-tuned corruption targets (license, confidentiality, credit clauses) |
| `benchmark/answers/*.yaml` | `document_type` field; one key file per primary fixture |
| `orchestrator/runner.py` | New `parallel_source_probe` strategy |
| `benchmark/metrics.py` | `source_fidelity`, `decoy_probe_match_rate`, `explicit_mislabel_rate` |

### What did not change

- Canonical SoT is still extrinsic (parsed filing, not model output).
- Verifier always checks against `bundle.canonical`.
- Decoys are still programmatic corruptions of the same parse.

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
4. Optionally add a corruption target in `docProcessing/bundle.py` → `CORRUPTION_TARGETS`.
5. Validate: `python -c "from benchmark.answers_validate import assert_all_answers_valid; assert_all_answers_valid()"`.

---

## Related docs

- [`context/STORE.md`](../STORE.md) — project memory
- [`context/phases/DOCUMENTS.md`](DOCUMENTS.md) — parsing and bundles
- [`context/phases/ORCHESTRATION.md`](ORCHESTRATION.md) — orchestration phase
- [`experimentDocs/EXPERIMENTS.md`](../../experimentDocs/EXPERIMENTS.md) — Gemini runs
