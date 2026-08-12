# LexOrchestra

Parallel contract subtasks with a canonical source of truth. Agents can see decoy document versions in the prompt; the verifier only trusts the signed parse.

**Question:** when plausible wrong versions sit next to the real contract, does orchestration + canonical verification still produce grounded answers?

## How it works

1. **Parse** — real SEC EDGAR MSAs → clause store with stable IDs (`signed_contract` + programmatic decoys).
2. **Orchestrate** — extract and playbook tasks run in parallel; output is structured claims, not free text.
3. **Verify** — every claim checked against the canonical store. Decoy quotes fail even if they look right.

Benchmark axes: `clean` vs `noisy_prompt` (decoys in context), `single` vs `parallel_grounded` (scheduling). Verifier and answer keys stay fixed.

## Quick start

No API keys needed for the default path (mock agents, no LLM calls):

```powershell
pip install -e ".[dev]"
python -m benchmark.run_experiment
python -m benchmark.run_ablations
python -m pytest tests/ -q
python scripts/check_baseline.py
```

Outputs: `experiments/mock_baseline/`, `experiments/ablations/` — each has `results.json`, `REPORT.md`, `manifest.json`. CI fails if the mock baseline drifts.

More flags: [`experimentDocs/EXPERIMENT.md`](experimentDocs/EXPERIMENT.md).

## Default matrix

| Axis | Values |
|------|--------|
| Documents | Edgemode, NuScale, Chime MSAs |
| Conditions | `clean`, `noisy_prompt` |
| Strategies | `single`, `parallel_grounded` |
| Mock profiles | `canonical`, `decoy_anchored` |

24 runs (3 × 2 × 2 × 2). Override:

```powershell
python -m benchmark.run_experiment `
  --documents edgar_edgemode_inc_ex10.1 `
  --conditions clean noisy_prompt `
  --profiles canonical
```

### Tasks

Per-document answer keys in `benchmark/answers/{document_id}.yaml`:

- **Playbook** — pass/fail rules with required quotes (e.g. ICC arbitration present?)
- **Extract** — factual answers tied to clause IDs (e.g. fee indexation %)

Task accuracy requires grounded claims that match the key. Decoy text that happens to look similar still fails verification.

### Metrics

| Metric | What it is |
|--------|------------|
| Grounding rate | Claims with valid clause_id + quote in signed contract |
| Decoy citation rate | Claims matching decoy text or wrong `sot_label` |
| Task accuracy | Playbook/extract scored against answer key |

### Mock profiles

| Profile | Behavior |
|---------|----------|
| `canonical` | Always cites `signed_contract` |
| `decoy_anchored` | Cites decoy text from the prompt |

## Live runs (optional)

```powershell
pip install -e ".[llm]"
$env:GEMINI_API_KEY = "your-key"
python -m benchmark.run_live_experiment --provider gemini
```

Key: [Google AI Studio](https://aistudio.google.com/apikey). Results → `experiments/live_gemini/`.

## Contract data

Real MSAs from SEC EDGAR EX-10 in [`legalDocs/contracts/public/`](legalDocs/contracts/public/). Decoys are corruptions of each parse, not separate synthetic docs.

```powershell
python -m benchmark.fetch_contracts --limit 3
```

## Layout

```
docProcessing/    parse, bundle, prompt formatting
orchestrator/     tasks, parallel runner
grounding/        verifier, decoy detection
models/           mock + optional Gemini client
benchmark/        answer keys, experiment runners
legalDocs/        SEC EDGAR contract fixtures
experiments/      committed baselines
experimentDocs/   run write-ups and findings
context/          design docs
tests/
```

## Docs

- [`experimentDocs/EXPERIMENTS.md`](experimentDocs/EXPERIMENTS.md) — live Gemini runs
- [`experimentDocs/MOCK_EXPERIMENTS.md`](experimentDocs/MOCK_EXPERIMENTS.md) — mock baseline + ablations
- [`experimentDocs/FINDINGS.md`](experimentDocs/FINDINGS.md) — interpretation
- [`experimentDocs/HYPOTHESIS.md`](experimentDocs/HYPOTHESIS.md) — research question
- [`context/STORE.md`](context/STORE.md) — architecture and decisions

## License

MIT — see [`LICENSE`](LICENSE).
