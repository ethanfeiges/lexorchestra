# Running experiments

> **Gemini test catalog:** [`EXPERIMENTS.md`](EXPERIMENTS.md) — what we ran with the API, task-by-task.

All experiments require a Gemini API key. Results are committed under `experiments/live_gemini/`.

## Default run

```powershell
python -m benchmark.run_experiment --provider gemini
```

This runs a fixed matrix:

| Axis | Values |
|------|--------|
| Documents | Edgemode, NuScale, Aspira, Pulmatrix MSAs |
| Conditions | `clean`, `noisy_prompt` |
| Strategy | `parallel_grounded` (default) |
| Model | `gemini-2.0-flash` (default) |
| Seeds | Deterministic (`DETERMINISTIC_SEEDS`) |
| Runs | **8** (4 docs × 2 conditions) |

### Outputs

Written to `experiments/live_gemini/`:

- **`results.json`** — one row per run with metrics and task scores
- **`REPORT.md`** — aggregated tables
- **`manifest.json`** — configuration snapshot

Commit these files after a run to preserve the baseline for comparison.

### Customize

```powershell
# Smaller run
python -m benchmark.run_experiment `
  --provider gemini `
  --documents edgar_edgemode_inc_ex10.1 `
  --conditions clean noisy_prompt

# Sequential subtasks (fewer API calls)
python -m benchmark.run_experiment --provider gemini --strategy single

# Custom output path (local only — under results/ is gitignored)
python -m benchmark.run_experiment --output results/local_run.json
```

## Setup

1. Create an API key at [Google AI Studio](https://aistudio.google.com/apikey).
2. Add to `.env`:

```powershell
GEMINI_API_KEY=your-key-here
```

3. Install dependencies:

```powershell
pip install -e ".[dev]"
```

If the API key is not set, the runner prints a clear message and exits with code **2**.

## Metrics

| Metric | Meaning |
|--------|---------|
| **Grounding rate** | Claims with valid `clause_id` + quote in **canonical** SoT |
| **Decoy citation rate** | Claims matching decoy text or `sot_label != signed_contract` |
| **Task accuracy** | Playbook/extract answers matching answer YAML |

See [`experimentDocs/HYPOTHESIS.md`](HYPOTHESIS.md) and [`experimentDocs/FINDINGS.md`](FINDINGS.md) for research framing and results.

## Gold labels

Ground truth for task accuracy: `benchmark/answers/{document_id}.yaml`. See [`benchmark/answers/README.md`](../benchmark/answers/README.md).

## Adding a new MSA

1. Fetch: `python -m benchmark.fetch_contracts`
2. Author answers: `benchmark/answers/{document_id}.yaml`
3. Validate: `assert_all_answers_valid([document_id])`
4. Re-run: `python -m benchmark.run_experiment --provider gemini --documents {document_id}`

## CI

```yaml
- run: pip install -e ".[dev]"
- run: python -m pytest tests/ -q
- run: python scripts/sync_experiment_docs.py --check
```

Live experiment runs are not part of CI because they require an API key.
