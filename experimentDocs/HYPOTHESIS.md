# LexOrchestra Research Hypothesis

## Research question

Does mechanical grounding verification improve contract-analysis reliability when LLM prompts include plausible but incorrect document versions (decoys)?

We test whether a canonical Source-of-Truth (SoT) store plus quote-level verification catches decoy citations that naive task scoring would accept.

## Metrics

| Metric | Definition |
|--------|------------|
| **Grounding rate** | Fraction of claims with `clause_id` + quote matching the **canonical** SoT |
| **Decoy citation rate** | Fraction of claims matching decoy text or citing a non-canonical `sot_label` |
| **Task accuracy** | Fraction of playbook/extract tasks scored correct against the answer key |

Task scoring requires grounded claims with matching substrings and clause IDs unless the ablation disables verification (naive scoring trusts model verdicts only).

## Experimental conditions

| Condition | Description |
|-----------|-------------|
| `clean` | Only canonical text in prompt |
| `noisy_prompt` | 1–2 decoys with semantic labels (`signed_contract`, `outdated_wrong_terms`, …) |
| `unlabeled_noisy` | Same decoys, but labels remapped to anonymous `version_1`, `version_2`, … |

## Ablation baselines (mock-only)

| Ablation | Setup | Expected effect |
|----------|-------|-----------------|
| **full_pipeline** | `decoy_anchored` + `noisy_prompt` + verify=True | Low task accuracy when decoy quotes fail canonical check |
| **no_verifier** | Same + verify=False | 100% grounding (naive trust), high task accuracy, 0% decoy detection |
| **unlabeled** | `decoy_anchored` + `unlabeled_noisy` + verify=True | Verifier still catches wrong quotes; labels give no authority hint |

## Confounds

- **Mock profiles, not live LLMs.** Results isolate verifier behavior; live models may partially self-correct.
- **Seed-dependent decoy sampling.** Different seeds pick different decoy subsets and shuffles.
- **Decoy severity varies.** Some decoys (`outdated_wrong_terms`) alter key substrings; others share clause IDs but wrong text.
- **Strategy interaction.** `parallel_grounded` runs two extract/playbook models; failures compound differently than `single`.
- **Naive scoring in no_verifier.** Task accuracy under verify=False uses verdict-only scoring, not quote substring checks — this measures trust cost, not end-user quality.

## Falsification criteria

The hypothesis is **weakened** if:

1. `canonical` profile under `noisy_prompt` drops below 95% task accuracy (verifier or prompt assembly is broken).
2. `no_verifier` ablation shows **lower** task accuracy than `full_pipeline` on the same seeds (verification is not the binding constraint).
3. `unlabeled_noisy` with verify=True matches `no_verifier` task accuracy (anonymous labels alone prevent decoy detection — verifier adds no value).

The hypothesis is **supported** if:

1. `decoy_anchored` + `noisy_prompt` + verify=True shows materially lower task accuracy than `canonical` on the same document/seed.
2. `no_verifier` shows ≥30 percentage-point task accuracy gain over `full_pipeline` on decoy-anchored runs.
3. `unlabeled` still shows high decoy citation rate under verify=True (mechanical quote check works without label hints).

## Reproduction

## Reproduction

```powershell
python -m benchmark.run_live_experiment --provider gemini   # 4-run live baseline
python -m benchmark.run_experiment      # 24-run mock baseline (see MOCK_EXPERIMENTS.md)
python -m benchmark.run_ablations       # 6-run ablation matrix
python scripts/sync_experiment_docs.py --check
python -m pytest tests/ -q
```

Live test catalog: [`EXPERIMENTS.md`](EXPERIMENTS.md). Mock/CI: [`MOCK_EXPERIMENTS.md`](MOCK_EXPERIMENTS.md).
