# LexOrchestra Live Gemini Baseline

Generated: 2026-08-12 19:39 UTC

## Run configuration

- **mode**: `live_gemini`
- **status**: `completed`
- **provider**: `gemini`
- **documents**: `['edgar_edgemode_inc_ex10.1', 'edgar_nuscale_power_corp_ex10.15']`
- **conditions**: `['clean', 'noisy_prompt']`
- **strategy**: `single`
- **model**: `gemini-2.5-flash`
- **deterministic**: `True`
- **seeds**: `DETERMINISTIC_SEEDS`
- **generated**: `2026-08-12T19:39:22.663229+00:00`

## Summary by condition

| Condition | Runs | Grounding | Decoy rate | Task accuracy |
|-----------|------|-----------|------------|---------------|
| clean | 2 | 83% | 0% | 67% |
| noisy_prompt | 2 | 67% | 17% | 50% |

## Summary by strategy

| Strategy | Runs | Grounding | Decoy rate | Task accuracy |
|----------|------|-----------|------------|---------------|
| single | 4 | 75% | 8% | 58% |

## Per-run detail

| Document | Condition | Strategy | Profile | Seed | Decoys | Ground | Decoy | Acc |
|----------|-----------|----------|---------|------|--------|--------|-------|-----|
| edgar_edgemode_inc_ex10.1 | clean | single | — | 11001 | — | 100% | 0% | 67% |
| edgar_edgemode_inc_ex10.1 | noisy_prompt | single | — | 11002 | bad_parse_wrong_ids, bad_parse_extra_clause | 100% | 0% | 67% |
| edgar_nuscale_power_corp_ex10.15 | clean | single | — | 11003 | — | 67% | 0% | 67% |
| edgar_nuscale_power_corp_ex10.15 | noisy_prompt | single | — | 11004 | outdated_wrong_terms | 33% | 33% | 33% |

## Interpretation

- **Grounding rate** measures whether Gemini cited valid clause IDs and exact quotes from the canonical signed contract.
- **Decoy citation rate** rises when the model anchors on corrupted document versions shown in the prompt.
- **Task accuracy** compares verified answers against pre-authored gold labels.
