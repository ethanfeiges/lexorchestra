# LexOrchestra Findings

> Full test catalog: [`EXPERIMENTS.md`](EXPERIMENTS.md).

Regenerate: `python -m benchmark.run_experiment --provider gemini`

---

## Live Gemini (`gemini-flash-latest`, five document types)

### Headline

The **committed baseline is partial**: only **1 of 10** default-matrix runs is saved in `results.json`. On that run — Edgemode MSA under `clean` with `parallel_grounded` — Gemini stayed **100% grounded** with **0% decoy citations** and **67% task accuracy** (2/3 tasks correct).

A later session attempted a full multi-strategy matrix (including portfolio cross-type runs) but was **aborted** when Gemini free-tier rate limits hit; incremental save left the repo with this single-row baseline.

### Committed run (1 row)

| Document | Type | Condition | Strategy | Grounding | Decoy rate | Task accuracy |
|----------|------|-----------|----------|-----------|------------|---------------|
| `edgar_edgemode_inc_ex10.1` | MSA | clean | `parallel_grounded` | 100% | 0% | 67% |

**Task breakdown:**

| Task | Result |
|------|--------|
| `extract:fee_indexation` | pass |
| `playbook:mutual_indemnity` | pass |
| `playbook:icc_arbitration` | fail |

### Engineering status (2026-08-12)

| Check | Result |
|-------|--------|
| `python -m pytest tests/ -q` | **92 passed, 1 skipped** |
| Portfolio API concurrency cap | **5** parallel calls (`run_parallel_cross_type_discrimination`) |
| Experiment matrix run delay | **20 s** between runs (rate-limit mitigation) |

### Implications (from committed data)

1. **Grounding holds on the saved run.** All three claims cited valid canonical clause IDs and exact quotes.
2. **Task accuracy ≠ grounding.** The ICC arbitration playbook rule failed despite perfect grounding — likely rule interpretation or quote selection, not wrong-document anchoring.
3. **Full baseline pending.** Re-run `python -m benchmark.run_experiment --provider gemini` when quota resets to populate the remaining 9 default-matrix cells and optional portfolio / source-probe strategies.

### Prior MSA-only baseline (4 runs, `single` strategy)

NuScale under noise showed decoy citation (33% accuracy, 33% decoy rate) — see git history for `experiments/live_gemini/REPORT.md` from the MSA-only era.
