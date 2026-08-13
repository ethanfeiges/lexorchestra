# LexOrchestra Gemini Experiment Report

Generated: 2026-08-12 22:49 UTC

## Run configuration

- **mode**: `live_gemini`
- **status**: `partial`
- **provider**: `gemini`
- **documents**: `['edgar_edgemode_inc_ex10.1']`
- **conditions**: `['clean']`
- **strategies**: `['parallel_grounded']`
- **model**: `gemini-flash-latest`
- **deterministic**: `True`
- **seeds**: `DETERMINISTIC_SEEDS`
- **generated**: `2026-08-12T22:49:09.574970+00:00`

## Summary by condition

| Condition | Runs | Grounding | Decoy rate | Task accuracy |
|-----------|------|-----------|------------|---------------|
| clean | 1 | 100% | 0% | 67% |

## Summary by model

| Model | Runs | Grounding | Decoy rate | Task accuracy |
|-------|------|-----------|------------|---------------|
| gemini-flash-latest | 1 | 100% | 0% | 67% |

## Summary by document type

| Document type | Runs | Grounding | Decoy rate | Task accuracy |
|---------------|------|-----------|------------|---------------|
| msa | 1 | 100% | 0% | 67% |

## Summary by strategy

| Strategy | Runs | Grounding | Decoy rate | Task accuracy |
|----------|------|-----------|------------|---------------|
| parallel_grounded | 1 | 100% | 0% | 67% |

## Per-run detail

| Document | Type | Condition | Strategy | Model | Seed | Decoys | Ground | Decoy | Acc |
|----------|------|-----------|----------|-------|------|--------|--------|-------|-----|
| edgar_edgemode_inc_ex10.1 | msa | clean | parallel_grounded | gemini-flash-latest | 11001 | — | 100% | 0% | 67% |

## Interpretation

- **Grounding rate** measures whether claims cite valid clause IDs and exact quotes from the canonical signed contract.
- **Decoy citation rate** rises when the model anchors on corrupted document versions shown in the prompt.
- **Task accuracy** compares verified answers against pre-authored gold labels.
