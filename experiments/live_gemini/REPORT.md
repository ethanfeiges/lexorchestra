# LexOrchestra Gemini Experiment Report

Generated: 2026-08-18 10:25 UTC

## Run configuration

- **mode**: `live_gemini`
- **status**: `success`
- **provider**: `gemini`
- **documents**: `['edgar_amd_ex10.79']`
- **conditions**: `['clean']`
- **strategies**: `['single']`
- **model**: `gemini-flash-latest`
- **deterministic**: `True`
- **seeds**: `DETERMINISTIC_SEEDS`
- **generated**: `2026-08-18T10:25:00Z`

## Summary by condition

| Condition | Runs | Grounding | Decoy rate | Task accuracy |
|-----------|------|-----------|------------|---------------|
| clean | 1 | 100% | 0% | 100% |

## Summary by model

| Model | Runs | Grounding | Decoy rate | Task accuracy |
|-------|------|-----------|------------|---------------|
| gemini-flash-latest | 1 | 100% | 0% | 100% |

## Summary by document type

| Document type | Runs | Grounding | Decoy rate | Task accuracy |
|---------------|------|-----------|------------|---------------|
| software_license | 1 | 100% | 0% | 100% |

## Summary by strategy

| Strategy | Runs | Grounding | Decoy rate | Task accuracy |
|----------|------|-----------|------------|---------------|
| single | 1 | 100% | 0% | 100% |

## Per-run detail

| Document | Type | Condition | Strategy | Model | Seed | Decoys | Ground | Decoy | Acc |
|----------|------|-----------|----------|-------|------|--------|--------|-------|-----|
| edgar_amd_ex10.79 | software_license | clean | single | gemini-flash-latest | 11001 | — | 100% | 0% | 100% |

## Interpretation

- **Grounding rate** measures whether claims cite valid clause IDs and exact quotes from the canonical signed contract.
- **Decoy citation rate** remains at 0% because the live run used the clean condition.
- **Task accuracy** reached 100% on the smoke test: `playbook:perpetual_license`, `playbook:license_fees`, and `extract:governing_law` all passed.
