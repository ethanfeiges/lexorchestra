# LexOrchestra — Live Gemini Experiments

> **What we test with the Gemini API** — real MSAs, orchestrated subtasks, mechanical verification.
> Mock/CI (no API): [`MOCK_EXPERIMENTS.md`](MOCK_EXPERIMENTS.md).

Last synced: **2026-08-12**

---

## Orchestrated subtasks

Live runs use **`parallel_grounded`**: Gemini runs **extract** and **playbook** **in parallel** (two subtasks, same model), then the **grounding verifier** checks all claims against the canonical signed contract only.

Use `--strategy single` for one model doing extract → playbook sequentially (fewer API calls).

---

## Real-world scenario

Deal teams rarely have one clean file. LexOrchestra models:

| Production problem | Decoy type |
|--------------------|------------|
| Executed MSA on EDGAR | `signed_contract` (canonical) |
| Stale SharePoint draft with old pricing | `outdated_wrong_terms` |
| Draft missing a section | `draft_missing_section` |
| Bad OCR / wrong clause IDs | `bad_parse_wrong_ids` |
| Parser adding a fake clause | `bad_parse_extra_clause` |

**Example:** Counsel asks “Is Fluor capped at $10M?” The model sees the **signed NuScale–Fluor MSA** and an **old draft** with different liability language. LexOrchestra measures whether answers stay grounded in the executed copy.

---

## Current live matrix (default)

| Setting | Value |
|---------|--------|
| Provider | Google Gemini (AI Studio) |
| Model | `gemini-2.5-flash` |
| Strategy | `parallel_grounded` (extract ∥ playbook) |
| Conditions | `clean`, `noisy_prompt` |
| MSAs | **4** with answer keys (Chime excluded by default — 184 clauses, token quota) |
| Runs | **8** (4 docs × 2 conditions) |
| Verification | On |

### MSAs tested

| Document | Company / deal | Example playbook questions |
|----------|----------------|----------------------------|
| `edgar_edgemode_inc_ex10.1` | EdgeMode ↔ Cudo Ventures | ICC arbitration? Mutual indemnity? Fee indexation %? |
| `edgar_nuscale_power_corp_ex10.15` | NuScale ↔ Fluor | $10M liability cap? Mutual indemnity? Term length? |
| `edgar_aspira_women_s_health_inc_ex10.1` | Aspira consultant MSA | ICC arbitration? Mutual indemnity? Initial term? |
| `edgar_pulmatrix_inc_ex10.6` | Pulmatrix ↔ MannKind | ICC arbitration? Mutual indemnity? Initial term? |
| `edgar_chime_financial_inc_ex10.1` | Chime ↔ Bank (optional) | AAA arbitration? `--include-chime` only |

Answer keys: `benchmark/answers/{document_id}.yaml`

---

## Committed results status

**Last full committed run:** 4 runs (Edgemode + NuScale only, `single` strategy) — see [`experiments/live_gemini/REPORT.md`](../experiments/live_gemini/REPORT.md).

**Expanded 8-run matrix** (4 MSAs, `parallel_grounded`) is configured in code; re-run when Gemini quota allows:

```powershell
python -m benchmark.run_live_experiment --provider gemini --model gemini-2.5-flash
```

Free tier limits (~20 requests/day for Flash) may require splitting runs or waiting for quota reset.

---

## Prior 4-run findings (Edgemode + NuScale, single strategy)

| Document | Condition | Ground | Decoy | Acc |
|----------|-----------|--------|-------|-----|
| Edgemode | clean | 100% | 0% | 67% |
| Edgemode | noisy | 100% | 0% | 67% |
| NuScale | clean | 67% | 0% | 67% |
| NuScale | noisy | 33% | 33% | 33% |

**NuScale under noise** cited decoy text (`outdated_wrong_terms`) — the core failure mode this project detects.

### Task-level detail (prior run)

**Edgemode:** ICC arbitration ✅ · mutual indemnity ✅ · fee indexation ❌ (both conditions).

**NuScale clean:** $10M cap ✅ · term ✅ · mutual indemnity ❌.

**NuScale noisy:** $10M cap ❌ · mutual indemnity ❌ · term ✅ · **decoy citation detected**.

---

## Partial expanded run (Aspira, parallel_grounded)

During quota-limited testing, Aspira completed:

| Condition | Ground | Decoy | Acc |
|-----------|--------|-------|-----|
| clean | 67% | 0% | 67% |
| noisy | 67% | 0% | 67% |

Aspira uses **mediation** (not ICC) and **one-sided** consultant indemnity — real consultant MSA pattern from SEC EX-10.1.

---

## Re-run commands

```powershell
pip install -e ".[llm]"
# GEMINI_API_KEY in .env

# Default: 4 MSAs × 2 conditions, parallel subtasks
python -m benchmark.run_live_experiment --provider gemini

# Fewer API calls (sequential subtasks)
python -m benchmark.run_live_experiment --provider gemini --strategy single

# Include Chime (large; may hit token limits)
python -m benchmark.run_live_experiment --provider gemini --include-chime

# One MSA smoke test
python -m benchmark.run_live_experiment --provider gemini `
  --documents edgar_pulmatrix_inc_ex10.6 --conditions noisy_prompt
```

---

## Pipeline per API call

1. Parse SEC EX-10 → canonical clauses.
2. Build decoy bundle (seeded).
3. Prompt Gemini with document block + task instructions (JSON claims schema).
4. **Parallel:** extract subtask ∥ playbook subtask.
5. Verify every claim against canonical SoT.
6. Score vs answer YAML.

---

## Related docs

| File | Contents |
|------|----------|
| [`MOCK_EXPERIMENTS.md`](MOCK_EXPERIMENTS.md) | Simulated agents, CI, ablations |
| [`FINDINGS.md`](FINDINGS.md) | Interpretation |

Check: `python scripts/sync_experiment_docs.py --check`
