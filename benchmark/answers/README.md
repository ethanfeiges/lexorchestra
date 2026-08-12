# Benchmark answers (`benchmark/answers/`)

Expected answers for benchmark **task accuracy**. After each run, verified agent claims are scored against these YAML files in `benchmark/metrics.py`.

Answers are derived from the **canonical parse** of each signed contract (`legalDocs/contracts/public/{document_id}.txt`). They do not reference decoys and do not change between runs.

## Files

One YAML per document: `{document_id}.yaml` (same ID as the fixture).

Loaded by `benchmark.answers.load_answers()`; validated by `benchmark.answers_validate.assert_all_answers_valid()` before experiment runs.

## Schema

### Document metadata

| Field | Purpose |
|-------|---------|
| `document_id` | Fixture id |
| `document_type` | `msa`, `software_license`, `nda`, `employment`, or `credit` |

### Playbook rules (`rules`)

Pass/fail legal checks. A task scores **correct** only if the claim is **grounded** in canonical, cites an allowed clause, matches `expected`, and includes every `required_substrings` entry in the quote.

| Field | Purpose |
|-------|---------|
| `id` | Rule identifier (matches agent `rule_id`) |
| `question` | Prompt text |
| `expected` | `pass` or `fail` |
| `canonical_clause_ids` | Clause IDs that may support the verdict |
| `required_substrings` | Text that must appear in the grounded quote |
| `notes` | Author reference only — not used in scoring |

### Extract questions (`extract_questions`)

Factual lookups. A task scores **correct** only if the claim is **grounded**, cites an `acceptable_clause_ids` entry, and includes every `required_substrings` entry in the quote.

| Field | Purpose |
|-------|---------|
| `id` | Question identifier |
| `question` | Prompt text |
| `acceptable_clause_ids` | Valid source clauses |
| `required_substrings` | Text that must appear in the grounded quote |

Clause IDs (`c-001`, …) come from `build_bundle_from_file` on the fixture.

## Primary fixtures (default matrix)

| Document ID | Type | Playbook rules | Extract questions |
|-------------|------|----------------|-------------------|
| `edgar_edgemode_inc_ex10.1` | msa | ICC arbitration (pass), mutual indemnity (fail) | Fee indexation % |
| `edgar_amd_ex10.79` | software_license | Perpetual license (pass), license fees (fail) | CA governing law |
| `edgar_hg_holdings_inc_ex10.2` | nda | Mutual confidentiality (fail), return of materials (pass) | 5-year term |
| `edgar_emerald_holding_inc_ex10.43` | employment | Confidentiality duty (pass), mutual indemnity (fail) | Province governing law |
| `edgar_enviri_corp_ex10.1` | credit | NY governing law (pass), ICC arbitration (fail) | Amendment No. 14 |

## Alternate MSAs

| Document ID | Playbook rules | Extract questions |
|-------------|----------------|-------------------|
| `edgar_nuscale_power_corp_ex10.15` | $10M liability cap (pass), mutual indemnity (fail) | Agreement term |
| `edgar_aspira_women_s_health_inc_ex10.1` | ICC arbitration (fail), mutual indemnity (fail) | Initial term |
| `edgar_pulmatrix_inc_ex10.6` | ICC arbitration (fail), mutual indemnity (pass) | Initial term |
| `edgar_chime_financial_inc_ex10.1` | AAA arbitration (pass), mutual indemnity (fail) | Arbitration venue |

## Validation

```powershell
python -c "from benchmark.answers_validate import assert_all_answers_valid; assert_all_answers_valid()"
```

Checks:

- Every referenced clause ID exists in the canonical parse
- Every `required_substrings` entry appears in at least one referenced clause

Also runs automatically in `python -m benchmark.run_experiment` (unless `--skip-answers-check`).

## Add or edit answers

1. Parse the fixture and locate supporting clauses: `build_bundle_from_file(legalDocs/contracts/public/{document_id}.txt)`.
2. Edit or create `benchmark/answers/{document_id}.yaml`.
3. Validate: `assert_all_answers_valid(["{document_id}"])`.
4. Re-run experiments for that document.
