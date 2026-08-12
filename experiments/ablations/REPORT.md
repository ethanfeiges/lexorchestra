# LexOrchestra Ablation Report

Generated: 2026-08-12 19:30 UTC

## Run configuration

- **mode**: `mock_ablation`
- **documents**: `['edgar_edgemode_inc_ex10.1', 'edgar_nuscale_power_corp_ex10.15']`
- **strategy**: `single`
- **ablations**: `['full_pipeline', 'no_verifier', 'unlabeled']`
- **deterministic**: `True`
- **generated**: `2026-08-12T19:30:27.556867+00:00`

## Summary by condition

| Condition | Runs | Grounding | Decoy rate | Task accuracy |
|-----------|------|-----------|------------|---------------|
| noisy_prompt | 4 | 100% | 50% | 83% |
| unlabeled_noisy | 2 | 50% | 100% | 33% |

## Summary by mock profile

| Profile | Runs | Grounding | Decoy rate | Task accuracy |
|---------|------|-----------|------------|---------------|
| decoy_anchored | 6 | 83% | 67% | 67% |

## Summary by ablation

| Ablation | Runs | Grounding | Decoy rate | Task accuracy |
|----------|------|-----------|------------|---------------|
| full_pipeline | 2 | 100% | 100% | 67% |
| no_verifier | 2 | 100% | 0% | 100% |
| unlabeled | 2 | 50% | 100% | 33% |

## Summary by strategy

| Strategy | Runs | Grounding | Decoy rate | Task accuracy |
|----------|------|-----------|------------|---------------|
| single | 6 | 83% | 67% | 67% |

## Per-run detail

| Document | Condition | Strategy | Profile | Seed | Decoys | Ground | Decoy | Acc | Ablation |
|----------|-----------|----------|---------|------|--------|--------|-------|-----|----------|
| edgar_edgemode_inc_ex10.1 | noisy_prompt | single | decoy_anchored | 11001 | outdated_wrong_terms | 100% | 100% | 67% | full_pipeline |
| edgar_nuscale_power_corp_ex10.15 | noisy_prompt | single | decoy_anchored | 11002 | bad_parse_wrong_ids, bad_parse_extra_clause | 100% | 100% | 67% | full_pipeline |
| edgar_edgemode_inc_ex10.1 | noisy_prompt | single | decoy_anchored | 11003 | bad_parse_extra_clause | 100% | 0% | 100% | no_verifier |
| edgar_nuscale_power_corp_ex10.15 | noisy_prompt | single | decoy_anchored | 11004 | outdated_wrong_terms | 100% | 0% | 100% | no_verifier |
| edgar_edgemode_inc_ex10.1 | unlabeled_noisy | single | decoy_anchored | 11005 | bad_parse_wrong_ids | 0% | 100% | 0% | unlabeled |
| edgar_nuscale_power_corp_ex10.15 | unlabeled_noisy | single | decoy_anchored | 11006 | bad_parse_extra_clause, bad_parse_wrong_ids | 100% | 100% | 67% | unlabeled |

## Interpretation

- **canonical** mock profile simulates agents that always cite `signed_contract` correctly.
- **decoy_anchored** mock profile simulates agents that faithfully use decoy text — grounding and task accuracy should drop under `noisy_prompt`.
- Comparing profiles on the same seeds shows what the verifier catches without live LLM cost.
