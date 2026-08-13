# LexOrchestra — Gemini Experiments

> **All experiments run through the Gemini API** — real SEC contracts across **five document types**, orchestrated subtasks, mechanical verification.

Last synced: **2026-08-13**

---

## Orchestrated subtasks

Runs use **`parallel_grounded`** by default: Gemini runs **extract** and **playbook** **in parallel** (two subtasks, same model), then the **grounding verifier** checks all claims against the canonical signed contract only.

Additional strategies:

| Strategy | What it tests |
|----------|---------------|
| `single` | One model, extract → playbook sequentially (fewer API calls) |
| `parallel_source_probe` | Canonical extract ∥ playbook ∥ decoy extract ∥ discrimination extract |

Use `parallel_source_probe` to measure whether agents cite the **correct or incorrect labeled source** when decoys appear in the prompt.

---

## Real-world scenario

Deal teams rarely have one clean file. LexOrchestra models:

| Production problem | Decoy type |
|--------------------|------------|
| Executed contract on EDGAR | `signed_contract` (canonical) |
| Stale SharePoint draft with old pricing | `outdated_wrong_terms` |
| Draft missing a section | `draft_missing_section` |
| Bad OCR / wrong clause IDs | `bad_parse_wrong_ids` |
| Parser adding a fake clause | `bad_parse_extra_clause` |

**Example (MSA):** Counsel asks "Is Fluor capped at $10M?" The model sees the **signed NuScale–Fluor MSA** and an **old draft** with different liability language.

**Example (NDA):** Counterparty asks "Is confidentiality mutual?" against a one-way NDA with a stale draft showing different survival terms.

---

## Default experiment matrix

| Setting | Value |
|---------|--------|
| Provider | Google Gemini (AI Studio) |
| Model | `gemini-flash-latest` |
| Strategy | `parallel_grounded` (extract ∥ playbook) |
| Conditions | `clean`, `noisy_prompt` |
| Documents | **5** primaries (one per document type) |
| Runs | **10 runs** (5 types × 2 conditions) |
| Verification | On |

### Documents by type

| Document type | Primary fixture | Company / deal | Example tasks |
|---------------|-----------------|----------------|---------------|
| MSA | `edgar_edgemode_inc_ex10.1` | EdgeMode ↔ Cudo Ventures | ICC arbitration, mutual indemnity, fee indexation |
| Software license | `edgar_amd_ex10.79` | AMD ↔ Broadcom | Perpetual license, license fees, CA governing law |
| NDA | `edgar_hg_holdings_inc_ex10.2` | HG Holdings | Mutual confidentiality, return of materials, 5-year term |
| Employment | `edgar_emerald_holding_inc_ex10.43` | Emerald Holding | Confidentiality duty, governing law |
| Credit | `edgar_enviri_corp_ex10.1` | Enviri | NY governing law, Amendment No. 14 |

Additional MSAs (NuScale, Aspira, Pulmatrix, Chime) remain available via `--documents`; Chime excluded from defaults due to token quota.

Answer keys: `benchmark/answers/{document_id}.yaml`

Design: [`context/phases/MULTI_TYPE.md`](../context/phases/MULTI_TYPE.md)

---

## Committed results status

**Stub matrix (32/32):** [`experiments/stub_matrix/REPORT.md`](../experiments/stub_matrix/REPORT.md) — all four strategies, canonical stub clients.

**Live Gemini (1/32 partial):** quota exhausted on 2026-08-13. One saved run (Edgemode MSA · clean · `parallel_grounded`: 100% grounding, 67% accuracy).

| Strategy | Stub runs | Stub grounding | Stub accuracy | Live note |
|----------|-----------|----------------|---------------|-----------|
| `single` | 10 | 100% | 100% | pending quota |
| `parallel_grounded` | 10 | 100% | 100% | 1 live run (67% acc) |
| `parallel_source_probe` | 10 | 100% | 100% | pending quota |
| `parallel_cross_type_discrimination` | 2 | 100% | 100% | pending quota |

Re-run stub matrix: `python scripts/run_stub_matrix.py`

Re-run live matrix:

```powershell
python -m benchmark.run_experiment --provider gemini --model gemini-flash-latest `
  --strategies single parallel_grounded parallel_source_probe parallel_cross_type_discrimination `
  --conditions clean noisy_prompt portfolio_clean cross_type_mislabeled
```
Source-probe smoke test:

```powershell
python -m benchmark.run_experiment --provider gemini `
  --strategy parallel_source_probe `
  --documents edgar_edgemode_inc_ex10.1 `
  --conditions noisy_prompt
```

---

## Re-run commands

```powershell
# GEMINI_API_KEY in .env

# Default: 5 document types × 2 conditions, parallel subtasks
python -m benchmark.run_experiment --provider gemini

# Source-probe strategy (4 parallel agents per run)
python -m benchmark.run_experiment --provider gemini --strategy parallel_source_probe

# Fewer API calls (sequential subtasks)
python -m benchmark.run_experiment --provider gemini --strategy single

# One document smoke test
python -m benchmark.run_experiment --provider gemini `
  --documents edgar_amd_ex10.79 --conditions noisy_prompt
```

---

## Pipeline per API call

1. Parse SEC EX-10 → canonical clauses.
2. Resolve **document-specific corruption plan** (`corruption_plan.py`; local or cached Gemini plan) → build decoy bundle (seeded).
3. Prompt Gemini with document block + task instructions (JSON claims schema).
4. **Parallel:** extract subtask ∥ playbook subtask (or source probes).
5. Verify every claim against canonical SoT.
6. Score vs answer YAML; report metrics by document type.

Pre-generate Gemini corruption plans (optional, one-time per document/seed):

```powershell
python scripts/generate_corruption_plans.py --mode gemini --seed 42
```

---

## Related docs

| File | Contents |
|------|----------|
| [`FINDINGS.md`](FINDINGS.md) | Interpretation |
| [`HYPOTHESIS.md`](HYPOTHESIS.md) | Research question |

Check: `python scripts/sync_experiment_docs.py --check`
