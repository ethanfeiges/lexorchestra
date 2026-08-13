# LexOrchestra Stub Matrix Report

Generated: 2026-08-13 02:32 UTC

## Run configuration

- **mode**: `stub_matrix`
- **status**: `completed`
- **provider**: `stub`
- **documents**: `['edgar_edgemode_inc_ex10.1', 'edgar_amd_ex10.79', 'edgar_hg_holdings_inc_ex10.2', 'edgar_emerald_holding_inc_ex10.43', 'edgar_enviri_corp_ex10.1']`
- **conditions**: `['clean', 'noisy_prompt', 'portfolio_clean', 'cross_type_mislabeled']`
- **strategies**: `['single', 'parallel_grounded', 'parallel_source_probe', 'parallel_cross_type_discrimination']`
- **model**: `canonical-stub`
- **deterministic**: `True`
- **seeds**: `DETERMINISTIC_SEEDS`
- **generated**: `2026-08-13T02:32:28.011749+00:00`
- **completed_runs**: `32`
- **expected_runs**: `32`
- **notes**: `Canonical stub clients; validates pipeline per strategy without Gemini API.`

## Summary by condition

| Condition | Runs | Grounding | Decoy rate | Task accuracy |
|-----------|------|-----------|------------|---------------|
| clean | 15 | 100% | 0% | 100% |
| cross_type_mislabeled | 1 | 100% | 100% | 100% |
| noisy_prompt | 15 | 100% | 0% | 100% |
| portfolio_clean | 1 | 100% | 100% | 100% |

## Summary by model

| Model | Runs | Grounding | Decoy rate | Task accuracy |
|-------|------|-----------|------------|---------------|
| canonical-stub | 32 | 100% | 6% | 100% |

## Summary by document type

| Document type | Runs | Grounding | Decoy rate | Task accuracy |
|---------------|------|-----------|------------|---------------|
| credit | 6 | 100% | 0% | 100% |
| employment | 6 | 100% | 0% | 100% |
| msa | 6 | 100% | 0% | 100% |
| nda | 6 | 100% | 0% | 100% |
| portfolio | 2 | 100% | 100% | 100% |
| software_license | 6 | 100% | 0% | 100% |

## Summary by strategy

| Strategy | Runs | Grounding | Decoy rate | Task accuracy |
|----------|------|-----------|------------|---------------|
| parallel_cross_type_discrimination | 2 | 100% | 100% | 100% |
| parallel_grounded | 10 | 100% | 0% | 100% |
| parallel_source_probe | 10 | 100% | 0% | 100% |
| single | 10 | 100% | 0% | 100% |

## Per-run detail

| Document | Type | Condition | Strategy | Model | Seed | Decoys | Ground | Decoy | Acc |
|----------|------|-----------|----------|-------|------|--------|--------|-------|-----|
| portfolio:primary_five | portfolio | portfolio_clean | parallel_cross_type_discrimination | canonical-stub | 11001 | — | 100% | 100% | 100% |
| portfolio:primary_five | portfolio | cross_type_mislabeled | parallel_cross_type_discrimination | canonical-stub | 11002 | edgar_emerald_holding_inc_ex10.43->edgar_hg_holdings_inc_ex10.2 | 100% | 100% | 100% |
| edgar_edgemode_inc_ex10.1 | msa | clean | single | canonical-stub | 11003 | — | 100% | 0% | 100% |
| edgar_edgemode_inc_ex10.1 | msa | clean | parallel_grounded | canonical-stub | 11004 | — | 100% | 0% | 100% |
| edgar_edgemode_inc_ex10.1 | msa | clean | parallel_source_probe | canonical-stub | 11005 | — | 100% | 0% | 100% |
| edgar_edgemode_inc_ex10.1 | msa | noisy_prompt | single | canonical-stub | 11006 | bad_parse_extra_clause, bad_parse_wrong_ids | 100% | 0% | 100% |
| edgar_edgemode_inc_ex10.1 | msa | noisy_prompt | parallel_grounded | canonical-stub | 11007 | outdated_wrong_terms, bad_parse_wrong_ids | 100% | 0% | 100% |
| edgar_edgemode_inc_ex10.1 | msa | noisy_prompt | parallel_source_probe | canonical-stub | 11008 | draft_missing_section, bad_parse_wrong_ids | 100% | 0% | 100% |
| edgar_amd_ex10.79 | software_license | clean | single | canonical-stub | 11009 | — | 100% | 0% | 100% |
| edgar_amd_ex10.79 | software_license | clean | parallel_grounded | canonical-stub | 11010 | — | 100% | 0% | 100% |
| edgar_amd_ex10.79 | software_license | clean | parallel_source_probe | canonical-stub | 11011 | — | 100% | 0% | 100% |
| edgar_amd_ex10.79 | software_license | noisy_prompt | single | canonical-stub | 11012 | draft_missing_section | 100% | 0% | 100% |
| edgar_amd_ex10.79 | software_license | noisy_prompt | parallel_grounded | canonical-stub | 11013 | bad_parse_wrong_ids | 100% | 0% | 100% |
| edgar_amd_ex10.79 | software_license | noisy_prompt | parallel_source_probe | canonical-stub | 11014 | bad_parse_extra_clause | 100% | 0% | 100% |
| edgar_hg_holdings_inc_ex10.2 | nda | clean | single | canonical-stub | 11015 | — | 100% | 0% | 100% |
| edgar_hg_holdings_inc_ex10.2 | nda | clean | parallel_grounded | canonical-stub | 11016 | — | 100% | 0% | 100% |
| edgar_hg_holdings_inc_ex10.2 | nda | clean | parallel_source_probe | canonical-stub | 11017 | — | 100% | 0% | 100% |
| edgar_hg_holdings_inc_ex10.2 | nda | noisy_prompt | single | canonical-stub | 11018 | outdated_wrong_terms, bad_parse_extra_clause | 100% | 0% | 100% |
| edgar_hg_holdings_inc_ex10.2 | nda | noisy_prompt | parallel_grounded | canonical-stub | 11019 | draft_missing_section | 100% | 0% | 100% |
| edgar_hg_holdings_inc_ex10.2 | nda | noisy_prompt | parallel_source_probe | canonical-stub | 11020 | draft_missing_section, outdated_wrong_terms | 100% | 0% | 100% |
| edgar_emerald_holding_inc_ex10.43 | employment | clean | single | canonical-stub | 11021 | — | 100% | 0% | 100% |
| edgar_emerald_holding_inc_ex10.43 | employment | clean | parallel_grounded | canonical-stub | 11022 | — | 100% | 0% | 100% |
| edgar_emerald_holding_inc_ex10.43 | employment | clean | parallel_source_probe | canonical-stub | 11023 | — | 100% | 0% | 100% |
| edgar_emerald_holding_inc_ex10.43 | employment | noisy_prompt | single | canonical-stub | 11024 | outdated_wrong_terms | 100% | 0% | 100% |
| edgar_emerald_holding_inc_ex10.43 | employment | noisy_prompt | parallel_grounded | canonical-stub | 11001 | outdated_wrong_terms | 100% | 0% | 100% |
| edgar_emerald_holding_inc_ex10.43 | employment | noisy_prompt | parallel_source_probe | canonical-stub | 11002 | bad_parse_wrong_ids, bad_parse_extra_clause | 100% | 0% | 100% |
| edgar_enviri_corp_ex10.1 | credit | clean | single | canonical-stub | 11003 | — | 100% | 0% | 100% |
| edgar_enviri_corp_ex10.1 | credit | clean | parallel_grounded | canonical-stub | 11004 | — | 100% | 0% | 100% |
| edgar_enviri_corp_ex10.1 | credit | clean | parallel_source_probe | canonical-stub | 11005 | — | 100% | 0% | 100% |
| edgar_enviri_corp_ex10.1 | credit | noisy_prompt | single | canonical-stub | 11006 | bad_parse_extra_clause, bad_parse_wrong_ids | 100% | 0% | 100% |
| edgar_enviri_corp_ex10.1 | credit | noisy_prompt | parallel_grounded | canonical-stub | 11007 | outdated_wrong_terms, bad_parse_wrong_ids | 100% | 0% | 100% |
| edgar_enviri_corp_ex10.1 | credit | noisy_prompt | parallel_source_probe | canonical-stub | 11008 | draft_missing_section, bad_parse_wrong_ids | 100% | 0% | 100% |

## Interpretation

- **Grounding rate** measures whether claims cite valid clause IDs and exact quotes from the canonical signed contract.
- **Decoy citation rate** rises when the model anchors on corrupted document versions shown in the prompt.
- **Task accuracy** compares verified answers against pre-authored gold labels.
