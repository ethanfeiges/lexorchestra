# LexOrchestra Mock Baseline

Generated: 2026-08-12 19:31 UTC

## Run configuration

- **mode**: `mock`
- **documents**: `['edgar_edgemode_inc_ex10.1', 'edgar_nuscale_power_corp_ex10.15', 'edgar_chime_financial_inc_ex10.1']`
- **conditions**: `['clean', 'noisy_prompt']`
- **strategies**: `['single', 'parallel_grounded']`
- **profiles**: `['canonical', 'decoy_anchored']`
- **deterministic**: `True`
- **generated**: `2026-08-12T19:31:28.323659+00:00`

## Summary by condition

| Condition | Runs | Grounding | Decoy rate | Task accuracy |
|-----------|------|-----------|------------|---------------|
| clean | 12 | 100% | 0% | 100% |
| noisy_prompt | 12 | 75% | 50% | 67% |

## Summary by mock profile

| Profile | Runs | Grounding | Decoy rate | Task accuracy |
|---------|------|-----------|------------|---------------|
| canonical | 12 | 100% | 0% | 100% |
| decoy_anchored | 12 | 75% | 50% | 67% |

## Summary by strategy

| Strategy | Runs | Grounding | Decoy rate | Task accuracy |
|----------|------|-----------|------------|---------------|
| parallel_grounded | 12 | 83% | 25% | 81% |
| single | 12 | 92% | 25% | 86% |

## Per-run detail

| Document | Condition | Strategy | Profile | Seed | Decoys | Ground | Decoy | Acc |
|----------|-----------|----------|---------|------|--------|--------|-------|-----|
| edgar_edgemode_inc_ex10.1 | clean | single | canonical | 11001 | — | 100% | 0% | 100% |
| edgar_edgemode_inc_ex10.1 | clean | parallel_grounded | canonical | 11002 | — | 100% | 0% | 100% |
| edgar_edgemode_inc_ex10.1 | noisy_prompt | single | canonical | 11003 | bad_parse_extra_clause | 100% | 0% | 100% |
| edgar_edgemode_inc_ex10.1 | noisy_prompt | parallel_grounded | canonical | 11004 | outdated_wrong_terms | 100% | 0% | 100% |
| edgar_edgemode_inc_ex10.1 | clean | single | decoy_anchored | 11005 | — | 100% | 0% | 100% |
| edgar_edgemode_inc_ex10.1 | clean | parallel_grounded | decoy_anchored | 11006 | — | 100% | 0% | 100% |
| edgar_edgemode_inc_ex10.1 | noisy_prompt | single | decoy_anchored | 11007 | outdated_wrong_terms, bad_parse_wrong_ids | 100% | 100% | 67% |
| edgar_edgemode_inc_ex10.1 | noisy_prompt | parallel_grounded | decoy_anchored | 11008 | draft_missing_section, bad_parse_wrong_ids | 0% | 100% | 0% |
| edgar_nuscale_power_corp_ex10.15 | clean | single | canonical | 11009 | — | 100% | 0% | 100% |
| edgar_nuscale_power_corp_ex10.15 | clean | parallel_grounded | canonical | 11010 | — | 100% | 0% | 100% |
| edgar_nuscale_power_corp_ex10.15 | noisy_prompt | single | canonical | 11011 | outdated_wrong_terms, draft_missing_section | 100% | 0% | 100% |
| edgar_nuscale_power_corp_ex10.15 | noisy_prompt | parallel_grounded | canonical | 11012 | draft_missing_section | 100% | 0% | 100% |
| edgar_nuscale_power_corp_ex10.15 | clean | single | decoy_anchored | 11013 | — | 100% | 0% | 100% |
| edgar_nuscale_power_corp_ex10.15 | clean | parallel_grounded | decoy_anchored | 11014 | — | 100% | 0% | 100% |
| edgar_nuscale_power_corp_ex10.15 | noisy_prompt | single | decoy_anchored | 11015 | bad_parse_wrong_ids, bad_parse_extra_clause | 100% | 100% | 67% |
| edgar_nuscale_power_corp_ex10.15 | noisy_prompt | parallel_grounded | decoy_anchored | 11016 | bad_parse_wrong_ids | 0% | 100% | 0% |
| edgar_chime_financial_inc_ex10.1 | clean | single | canonical | 11017 | — | 100% | 0% | 100% |
| edgar_chime_financial_inc_ex10.1 | clean | parallel_grounded | canonical | 11018 | — | 100% | 0% | 100% |
| edgar_chime_financial_inc_ex10.1 | noisy_prompt | single | canonical | 11019 | draft_missing_section | 100% | 0% | 100% |
| edgar_chime_financial_inc_ex10.1 | noisy_prompt | parallel_grounded | canonical | 11020 | draft_missing_section, outdated_wrong_terms | 100% | 0% | 100% |
| edgar_chime_financial_inc_ex10.1 | clean | single | decoy_anchored | 11021 | — | 100% | 0% | 100% |
| edgar_chime_financial_inc_ex10.1 | clean | parallel_grounded | decoy_anchored | 11022 | — | 100% | 0% | 100% |
| edgar_chime_financial_inc_ex10.1 | noisy_prompt | single | decoy_anchored | 11023 | bad_parse_wrong_ids | 0% | 100% | 0% |
| edgar_chime_financial_inc_ex10.1 | noisy_prompt | parallel_grounded | decoy_anchored | 11024 | outdated_wrong_terms | 100% | 100% | 67% |

## Interpretation

- **canonical** mock profile simulates agents that always cite `signed_contract` correctly.
- **decoy_anchored** mock profile simulates agents that faithfully use decoy text — grounding and task accuracy should drop under `noisy_prompt`.
- Comparing profiles on the same seeds shows what the verifier catches without live LLM cost.
