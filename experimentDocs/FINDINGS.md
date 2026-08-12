# LexOrchestra Findings

> Full test catalog: [`EXPERIMENTS.md`](EXPERIMENTS.md).

Regenerate: `python -m benchmark.run_experiment --provider gemini`

---

## Live Gemini (`gemini-flash-latest`, five document types)

### Headline

On **real SEC-filed contracts across five document types**, Gemini (`gemini-flash-latest`) stayed **100% grounded** on all completed runs — including under `noisy_prompt` with decoys present. Task accuracy varied by document type and task design, not by grounding failures. No decoy citations were detected in the completed 9/10 run matrix (free-tier daily quota blocked the final run).

### By condition (9 completed runs)

| Condition | Runs | Grounding | Decoy rate | Task accuracy |
|-----------|------|-----------|------------|---------------|
| clean | 5 | 100% | 0% | 73% |
| noisy_prompt | 4 | 100% | 0% | 58% |

### By document type (completed runs)

| Type | Document | Clean acc | Noisy acc | Notes |
|------|----------|-----------|-----------|-------|
| MSA | Edgemode | 67% | 67% | Fee indexation extract missed |
| Software license | AMD | 100% | 67% | Strong on license playbook |
| NDA | HG Holdings | 100% | — | Noisy run blocked by API quota |
| Employment | Emerald | 67% | 67% | Confidentiality playbook correct |
| Credit | Enviri | 33% | 33% | Amendment-number extract difficult |

### Implications

1. **Grounding generalizes across types.** 100% grounding on MSAs, licenses, NDAs, employment, and credit amendments — decoys in prompt did not cause canonical mis-citation in completed runs.
2. **Task accuracy is type-dependent.** Credit agreement amendment (Enviri) scored lowest; software license (AMD) scored highest on clean runs.
3. **Noise effect is modest so far.** Aggregate task accuracy dropped from 73% (clean) to 58% (noisy) on four noisy runs — without decoy citation rate rising, suggesting errors are quote-selection or rule interpretation, not wrong-document anchoring.
4. **Re-run needed.** Full 10-run committed baseline pending quota reset for `edgar_hg_holdings_inc_ex10.2` noisy_prompt.

### Prior MSA-only baseline (4 runs, `single` strategy)

NuScale under noise showed decoy citation (33% accuracy, 33% decoy rate) — see git history for `experiments/live_gemini/REPORT.md` from the MSA-only era.
