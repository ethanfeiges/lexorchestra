# LexOrchestra Findings

> **Live Gemini results** below. Mock/CI findings: [`MOCK_EXPERIMENTS.md`](MOCK_EXPERIMENTS.md).  
> Full test catalog: [`EXPERIMENTS.md`](EXPERIMENTS.md).

Regenerate live: `python -m benchmark.run_live_experiment --provider gemini`

---

## Live Gemini (`gemini-2.5-flash`, 4 runs)

### Headline

On **real SEC-filed MSAs**, Gemini stayed grounded on Edgemode even with decoys in context, but on **NuScale under noise** accuracy dropped from 67% to 33% with a measured decoy citation — the scenario this project is designed to detect (stale draft vs executed contract).

### By condition

| Condition | Runs | Grounding | Decoy rate | Task accuracy |
|-----------|------|-----------|------------|---------------|
| clean | 2 | 83% | 0% | 67% |
| noisy_prompt | 2 | 67% | 17% | 50% |

### Task-level outcomes

**Edgemode (EdgeMode ↔ Cudo Ventures MSA)**

- ICC arbitration playbook: **correct** (clean and noisy).
- Mutual indemnity playbook: **correct** (clean and noisy).
- Fee indexation extract: **wrong** (clean and noisy) — mechanical quote mismatch, not decoy-related.

**NuScale (NuScale ↔ Fluor MSA)**

- Clean: $10M cap **correct**, term **correct**, mutual indemnity **wrong**.
- Noisy (`outdated_wrong_terms`): $10M cap **wrong**, mutual indemnity **wrong**, term **correct**; **decoy citation detected**.

### Implications

1. **Noise is document-dependent.** Edgemode resisted decoys; NuScale did not — you cannot assume one MSA result generalizes.
2. **Playbook errors happen without noise too.** Mutual indemnity failed on NuScale even in `clean` — live models need verification even without decoys.
3. **Verification adds signal.** Decoy citation rate surfaced the NuScale noisy failure; task accuracy alone would not distinguish “wrong quote” from “wrong document version.”

### Mock pipeline validation

Before live runs, mock baselines confirmed verifier and metrics work as designed. See [`MOCK_EXPERIMENTS.md`](MOCK_EXPERIMENTS.md) — not evidence of LLM behavior.
