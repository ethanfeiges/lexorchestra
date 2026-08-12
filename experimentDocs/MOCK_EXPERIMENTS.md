# LexOrchestra — Mock & Ablation Experiments

> Simulated agent runs for **CI, verifier validation, and regression testing** — no LLM API keys.
> Live Gemini tests: [`EXPERIMENTS.md`](EXPERIMENTS.md). How to re-run: [`EXPERIMENT.md`](EXPERIMENT.md).

Last synced: **2026-08-12**

---

## Why mock runs exist

Mock experiments do not test whether Gemini (or any LLM) reads contracts well. They test whether **the pipeline** — parser, orchestrator, verifier, metrics — behaves correctly when you control agent outputs.

Use mock runs for:

- GitHub CI (`python -m benchmark.run_experiment` + baseline diff)
- Proving the verifier catches decoy citations when agents misbehave
- Ablation studies (verifier on/off) without API cost

---

## Suite 1 — Mock baseline (24 runs)

**Command:** `python -m benchmark.run_experiment`  
**Output:** `experiments/mock_baseline/`

### Matrix

| Axis | Values |
|------|--------|
| Documents | `edgar_edgemode_inc_ex10.1`, `edgar_nuscale_power_corp_ex10.15`, `edgar_chime_financial_inc_ex10.1` |
| Conditions | `clean`, `noisy_prompt` |
| Strategies | `single`, `parallel_grounded` |
| Mock profiles | `canonical`, `decoy_anchored` |
| Seeds | `11001`–`11024` |

**Formula:** 3 × 2 × 2 × 2 = **24 runs**.

### Mock profiles

| Profile | Simulated behavior |
|---------|-------------------|
| `canonical` | Always cites `signed_contract` with answer-aligned quotes |
| `decoy_anchored` | Cites decoy text/labels from the prompt |

### Conditions

| Condition | Prompt |
|-----------|--------|
| `clean` | `signed_contract` only |
| `noisy_prompt` | `signed_contract` + 1–2 decoys |

Decoy types: `draft_missing_section`, `outdated_wrong_terms`, `bad_parse_extra_clause`, `bad_parse_wrong_ids`.

### Results summary

| Group | Grounding | Decoy rate | Task accuracy |
|-------|-----------|------------|---------------|
| `clean` (12 runs) | 100% | 0% | 100% |
| `noisy_prompt` (12 runs) | 75% | 50% | 67% |
| `canonical` profile | 100% | 0% | 100% |
| `decoy_anchored` profile | 75% | 50% | 67% |

Per-run table: [`experiments/mock_baseline/REPORT.md`](../experiments/mock_baseline/REPORT.md).

### Interpretive comparisons

| Comparison | What it tests |
|------------|---------------|
| `clean` vs `noisy_prompt` | Does noise change outcomes when agents cite decoys? |
| `canonical` vs `decoy_anchored` | Verifier vs simulated bad agent |
| `single` vs `parallel_grounded` | More parallel claims → more decoy exposure |

---

## Suite 2 — Ablations (6 runs)

**Command:** `python -m benchmark.run_ablations`  
**Output:** `experiments/ablations/`

### Matrix

2 documents (Edgemode, NuScale) × 3 ablations, strategy `single`, seeds `11001`–`11006`.  
All use mock profile **`decoy_anchored`**.

| Ablation | Condition | verify | Purpose |
|----------|-----------|--------|---------|
| `full_pipeline` | `noisy_prompt` | True | Baseline with verification |
| `no_verifier` | `noisy_prompt` | False | Trust model claims (naive scoring) |
| `unlabeled` | `unlabeled_noisy` | True | Anonymous `version_N` labels |

### Results summary

| Ablation | Grounding | Decoy rate | Task accuracy |
|----------|-----------|------------|---------------|
| full_pipeline | 100% | 100% | 67% |
| no_verifier | 100% | 0% | **100%** |
| unlabeled | 50% | 100% | 33% |

Per-run table: [`experiments/ablations/REPORT.md`](../experiments/ablations/REPORT.md).

### Key takeaway

Disabling the verifier raises naive task accuracy **67% → 100%** while hiding decoy citations — proof that mechanical verification is load-bearing in the pipeline design.

---

## Gold tasks (shared with live runs)

Each run scores **3 tasks** per document:

| Document | Playbook rules | Extract question |
|----------|----------------|------------------|
| Edgemode | ICC arbitration? · Mutual indemnity? | Fee indexation % |
| NuScale | Fluor $10M liability cap? · Mutual indemnity? | Agreement term |
| Chime | AAA arbitration? · Mutual indemnity? | Arbitration venue |

Answer keys: [`benchmark/answers/README.md`](../benchmark/answers/README.md).
