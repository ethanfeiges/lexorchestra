# LexOrchestra

Parallel Gemini subtasks on real SEC EDGAR contracts across five document types. Agents can see decoy document versions in the prompt; the verifier only trusts the signed parse.

**Question:** when plausible wrong versions sit next to the real contract, does orchestration + canonical verification still produce grounded answers — across MSAs, software licenses, NDAs, employment agreements, and credit agreements?

## How it works

1. **Parse** — real SEC EX-10 filings → clause store with stable IDs (`c-012`, etc.). This canonical parse is ground truth.
2. **Bundle** — build a prompt with `signed_contract` (exact canonical copy) plus document-specific decoys from a seeded corruption plan.
3. **Orchestrate** — extract and playbook tasks run in parallel (or other strategies below); output is structured JSON claims, not free text.
4. **Verify** — every claim checked against the canonical store. Decoy quotes fail even if they look right. Task accuracy scored against answer keys in `benchmark/answers/`.

Truth is fixed before any LLM call. The model never votes on which document version is authoritative.

Benchmark axes: `clean` vs `noisy_prompt` (decoys in context); `single`, `parallel_grounded`, `parallel_source_probe`, or `parallel_cross_type_discrimination` (scheduling and source routing). Verifier and answer keys stay fixed.

### Metrics

| Metric | What it is |
|--------|------------|
| Grounding rate | Claims with valid `clause_id` + quote in signed contract |
| Decoy citation rate | Claims matching decoy text or wrong `sot_label` |
| Task accuracy | Playbook/extract scored against answer key |
| Source fidelity | Grounding on canonical-scoped tasks (`parallel_source_probe`) |
| Cross-document citation rate | Portfolio claims anchored on the wrong document |

## Quick start

```powershell
pip install -e ".[dev]"
copy .env.example .env          # set GEMINI_API_KEY
python -m pytest tests/ -q
python -m benchmark.run_experiment --provider gemini
python scripts/sync_experiment_docs.py --check
```

Tests run without API calls (corruption plans default to local mode). Results land in `experiments/live_gemini/` — `results.json`, `REPORT.md`, `manifest.json`.

Smoke test on one document:

```powershell
python -m benchmark.run_experiment --provider gemini `
  --documents edgar_edgemode_inc_ex10.1 --conditions clean
```

More flags: [`experimentDocs/EXPERIMENT.md`](experimentDocs/EXPERIMENT.md).

### Optional: Gemini corruption plans

Decoys come from per-document corruption plans (`docProcessing/corruption_plan.py`). Local mode uses regex extraction; Gemini mode generates harder edits and caches to `legalDocs/corruption_plans/`:

```powershell
python scripts/generate_corruption_plans.py --mode gemini --seed 42
```

## Default matrix

| Axis | Values |
|------|--------|
| Model | `gemini-flash-latest` |
| Documents | One primary per type (see below) |
| Conditions | `clean`, `noisy_prompt` |
| Strategy | `parallel_grounded` (default) |

10 runs (5 types × 2 conditions). Override:

```powershell
python -m benchmark.run_experiment `
  --provider gemini `
  --documents edgar_edgemode_inc_ex10.1 `
  --conditions clean noisy_prompt `
  --strategy parallel_source_probe
```

Portfolio cross-type runs cap concurrent API calls at 5 to reduce rate-limit failures.

| Document type | Primary fixture | Example tasks |
|---------------|-----------------|---------------|
| MSA | `edgar_edgemode_inc_ex10.1` | ICC arbitration, mutual indemnity, fee indexation |
| Software license | `edgar_amd_ex10.79` | Perpetual license, license fees, governing law |
| NDA | `edgar_hg_holdings_inc_ex10.2` | Mutual confidentiality, return of materials, term |
| Employment | `edgar_emerald_holding_inc_ex10.43` | Confidentiality duty, governing law |
| Credit | `edgar_enviri_corp_ex10.1` | NY governing law, amendment number |

### Tasks

Per-document answer keys in `benchmark/answers/{document_id}.yaml`:

- **Playbook** — pass/fail rules with required quotes (e.g. ICC arbitration present?)
- **Extract** — factual answers tied to clause IDs (e.g. fee indexation %)

Task accuracy requires grounded claims that match the key. Decoy text that happens to look similar still fails verification.

## Experiment results

Full matrix: **32 runs** (5 types × 2 conditions × 3 per-doc strategies + 2 portfolio runs). Reproduce the stub matrix locally (no API key):

```powershell
python scripts/run_stub_matrix.py
```

Live Gemini matrix (requires `GEMINI_API_KEY`):

```powershell
python -m benchmark.run_experiment --provider gemini `
  --strategies single parallel_grounded parallel_source_probe parallel_cross_type_discrimination `
  --conditions clean noisy_prompt portfolio_clean cross_type_mislabeled
```

**Live status (2026-08-13):** Gemini free-tier quota exhausted (`429 RESOURCE_EXHAUSTED`). One prior live run saved; full live re-run pending quota reset.

### By orchestration method

| Strategy | Runs | Agents per run | Grounding | Decoy | Accuracy | Notes |
|----------|------|----------------|-----------|-------|----------|-------|
| `single` | 10 | 1 (extract → playbook) | 100% | 0% | 100% | Fewest API calls; sequential subtasks |
| `parallel_grounded` | 10 | 2 (extract ∥ playbook) | 100% | 0% | 100% | Default; **live:** 100% ground / 67% acc on Edgemode MSA |
| `parallel_source_probe` | 10 | 4 (canonical + decoy + discriminate) | 100% | 0% | 100% | Adds source-fidelity and decoy-probe metrics |
| `parallel_cross_type_discrimination` | 2 | 15 (5 docs × 3 tasks, max 5 concurrent) | 100% | — | 100% | Portfolio prompt; 0% cross-document citations |

Stub rows validate the pipeline end-to-end with canonical answer-key clients. Live Gemini differs on task accuracy (model reasoning), not grounding verification.

### Live Gemini (partial, 1/32)

| Document | Condition | Strategy | Grounding | Decoy | Accuracy |
|----------|-----------|----------|-----------|-------|----------|
| Edgemode MSA | clean | `parallel_grounded` | 100% | 0% | 67% |

Task scores: `extract:fee_indexation` pass · `playbook:mutual_indemnity` pass · `playbook:icc_arbitration` fail.

Reports: [`experiments/stub_matrix/REPORT.md`](experiments/stub_matrix/REPORT.md) (full matrix) · [`experiments/live_gemini/REPORT.md`](experiments/live_gemini/REPORT.md) (live partial)

Test suite: 92 passed, 1 skipped.

## Contract data

Real contracts from SEC EDGAR EX-10 in [`legalDocs/contracts/public/`](legalDocs/contracts/public/). Decoys are corruptions of each parse, not separate synthetic docs. See [`context/phases/MULTI_TYPE.md`](context/phases/MULTI_TYPE.md) for the five-type design.

```powershell
python -m benchmark.fetch_contracts --limit 3
```

## Layout

```
docProcessing/    parse, bundle, corruption plans, prompts
orchestrator/     tasks, parallel runner, portfolio runner
grounding/        verifier, decoy and cross-document detection
models/           Gemini client and test stubs
benchmark/        answer keys, experiment runner, metrics
legalDocs/        SEC EDGAR fixtures; corruption_plans/ cache
experiments/      committed Gemini baseline results
experimentDocs/   run write-ups and findings
context/          design docs and decision log
tests/
scripts/          doc sync; generate_corruption_plans.py
```

## Docs

- [`context/phases/MULTI_TYPE.md`](context/phases/MULTI_TYPE.md) — five document types and portfolio strategy
- [`context/phases/DOCUMENTS.md`](context/phases/DOCUMENTS.md) — parsing, bundles, corruption plans
- [`experimentDocs/EXPERIMENTS.md`](experimentDocs/EXPERIMENTS.md) — Gemini runs and task outcomes
- [`experimentDocs/FINDINGS.md`](experimentDocs/FINDINGS.md) — interpretation
- [`experimentDocs/HYPOTHESIS.md`](experimentDocs/HYPOTHESIS.md) — research question
- [`context/STORE.md`](context/STORE.md) — architecture and decisions

## License

MIT — see [`LICENSE`](LICENSE).
