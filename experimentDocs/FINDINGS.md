# LexOrchestra Findings

> Full test catalog: [`EXPERIMENTS.md`](EXPERIMENTS.md).

Regenerate stub matrix: `python scripts/run_stub_matrix.py`  
Regenerate live: `python -m benchmark.run_experiment --provider gemini`

---

## Full matrix by strategy (stub, 32/32)

Canonical stub clients prove the pipeline for every orchestration method:

| Strategy | Runs | Grounding | Task accuracy | Extra metrics |
|----------|------|-----------|---------------|---------------|
| `single` | 10 | 100% | 100% | — |
| `parallel_grounded` | 10 | 100% | 100% | source fidelity 100% |
| `parallel_source_probe` | 10 | 100% | 100% | source fidelity 100% |
| `parallel_cross_type_discrimination` | 2 | 100% | 100% | cross-doc citations 0% |

Stub runs use answer-key responses — they validate orchestration and verification, not model reasoning under noise.

## Live Gemini (partial, 1/32)

Quota exhausted (`429`) on 2026-08-13 before a full live matrix could complete.

| Document | Strategy | Condition | Grounding | Accuracy |
|----------|----------|-----------|-----------|----------|
| Edgemode MSA | `parallel_grounded` | clean | 100% | 67% |

ICC arbitration playbook failed despite perfect grounding — task accuracy and grounding measure different things.

## Implications

1. **All four strategies execute end-to-end.** Stub matrix covers 5 document types, both prompt conditions, and both portfolio conditions.
2. **Live accuracy lags grounding.** The one saved Gemini run grounded every claim but missed one playbook rule.
3. **Re-run live when quota resets** to compare model behavior across strategies on the same fixtures.
