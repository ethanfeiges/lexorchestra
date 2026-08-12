# Ablation baseline

Committed output of `python -m benchmark.run_ablations` — **6 runs**.

## Matrix

2 documents × 3 ablations, strategy `single`, seeds `11001`–`11006`. All use mock profile `decoy_anchored`.

| Ablation | Condition | verify |
|----------|-----------|--------|
| full_pipeline | noisy_prompt | True |
| no_verifier | noisy_prompt | False |
| unlabeled | unlabeled_noisy | True |

Full catalog: [`experimentDocs/MOCK_EXPERIMENTS.md`](../../experimentDocs/MOCK_EXPERIMENTS.md).
