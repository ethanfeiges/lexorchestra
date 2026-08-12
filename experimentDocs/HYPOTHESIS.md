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

## Experimental conditions

| Condition | Description |
|-----------|-------------|
| `clean` | Only canonical text in prompt |
| `noisy_prompt` | 1–2 decoys with semantic labels (`signed_contract`, `outdated_wrong_terms`, …) |
| `unlabeled_noisy` | Same decoys, but labels remapped to anonymous `version_1`, `version_2`, … |

## Strategies

| Strategy | Description |
|----------|-------------|
| `single` | One Gemini call runs extract, then playbook sequentially |
| `parallel_grounded` | Extract and playbook run in parallel, then merge at the verifier |

## Confounds

- **Seed-dependent decoy sampling.** Different seeds pick different decoy subsets and shuffles.
- **Decoy severity varies.** Some decoys (`outdated_wrong_terms`) alter key substrings; others share clause IDs but wrong text.
- **Strategy interaction.** `parallel_grounded` runs two subtasks; failures compound differently than `single`.
- **API quota and token limits.** Large MSAs (Chime) may hit Gemini rate limits.

## Falsification criteria

The hypothesis is **weakened** if:

1. Gemini under `noisy_prompt` matches `clean` task accuracy on all documents (decoys have no measurable effect).
2. Decoy citation rate stays at 0% under `noisy_prompt` while task accuracy drops (errors are quote-level, not document-version-level).
3. Grounding rate is high but task accuracy is low even in `clean` (verifier passes bad quotes).

The hypothesis is **supported** if:

1. `noisy_prompt` shows materially lower task accuracy than `clean` on the same document.
2. Decoy citation rate rises under `noisy_prompt` when accuracy drops.
3. Mechanical verification flags claims that cite decoy text even when the model's verdict sounds plausible.

## Reproduction

```powershell
python -m benchmark.run_experiment --provider gemini
python scripts/sync_experiment_docs.py --check
python -m pytest tests/ -q
```

Test catalog: [`EXPERIMENTS.md`](EXPERIMENTS.md).
