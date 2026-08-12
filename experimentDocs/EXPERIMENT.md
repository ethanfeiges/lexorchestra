# Running experiments

> **Live Gemini tests:** [`EXPERIMENTS.md`](EXPERIMENTS.md) — what we ran with the API, task-by-task.  
> **Mock/CI tests:** [`MOCK_EXPERIMENTS.md`](MOCK_EXPERIMENTS.md) — simulated agents, no API keys.

LexOrchestra ships committed baselines under `experiments/`. Mock suites power CI; live Gemini requires `GEMINI_API_KEY`.

## Mock baseline (default)

```powershell
python -m benchmark.run_experiment
```

This runs a fixed matrix:

| Axis | Values |
|------|--------|
| Documents | Edgemode, NuScale, Chime MSAs |
| Conditions | `clean`, `noisy_prompt` |
| Strategies | `single`, `parallel_grounded` |
| Mock profiles | `canonical`, `decoy_anchored` |
| Seeds | Deterministic (`DETERMINISTIC_SEEDS`, 24 fixed seeds) |
| Runs | **24** (3 × 2 × 2 × 2) |

### Outputs

Written to `experiments/mock_baseline/`:

- **`results.json`** — one row per run with metrics and task scores
- **`REPORT.md`** — aggregated tables
- **`manifest.json`** — configuration snapshot

Commit these files to GitHub so reviewers can see expected metric patterns without re-running.

### Customize

```powershell
# Smaller run
python -m benchmark.run_experiment `
  --documents edgar_edgemode_inc_ex10.1 `
  --conditions clean noisy_prompt `
  --profiles canonical

# Random seeds (non-reproducible)
python -m benchmark.run_experiment --non-deterministic

# Custom output path (local only — under results/ is gitignored)
python -m benchmark.run_experiment --output results/local_run.json
```

## Metrics

| Metric | Meaning |
|--------|---------|
| **Grounding rate** | Claims with valid `clause_id` + quote in **canonical** SoT |
| **Decoy citation rate** | Claims matching decoy text or `sot_label != signed_contract` |
| **Task accuracy** | Playbook/extract answers matching answer YAML |

### Expected mock baseline pattern

| Profile | `clean` | `noisy_prompt` |
|---------|---------|----------------|
| `canonical` | ~100% all metrics | ~100% all metrics |
| `decoy_anchored` | ~100% (no decoys in prompt) | **Lower** grounding & accuracy |

If `decoy_anchored` + `noisy_prompt` still scores 100%, check that decoys differ from canonical for that seed.

## Ablation experiments (mock-only)

```powershell
python -m benchmark.run_ablations
```

Runs a focused 6-run matrix (2 docs × 3 ablations, strategy `single`):

| Ablation | Condition | verify |
|----------|-----------|--------|
| `full_pipeline` | `noisy_prompt` | True |
| `no_verifier` | `noisy_prompt` | False |
| `unlabeled` | `unlabeled_noisy` | True |

Outputs go to `experiments/ablations/` (`results.json`, `REPORT.md`, `manifest.json`).

See [`experimentDocs/HYPOTHESIS.md`](HYPOTHESIS.md) and [`experimentDocs/FINDINGS.md`](FINDINGS.md) for research framing and results.

## Gold labels

Ground truth for task accuracy: `benchmark/answers/{document_id}.yaml`. See [`benchmark/answers/README.md`](../benchmark/answers/README.md).

## Live LLM baseline (Gemini)

Requires `pip install -e ".[llm]"` and `GEMINI_API_KEY` (or `GOOGLE_API_KEY`).

1. Create an API key at [Google AI Studio](https://aistudio.google.com/apikey).
2. Add to `.env`:

```powershell
GEMINI_API_KEY=your-key-here
```

3. Run the live benchmark:

```powershell
python -m benchmark.run_live_experiment --provider gemini
```

Default model is **`gemini-2.5-pro`**. For faster/cheaper runs:

```powershell
python -m benchmark.run_live_experiment --provider gemini --model gemini-2.5-flash
```

Outputs go to `experiments/live_gemini/` (`results.json`, `REPORT.md`, `manifest.json`).

This runs a **small** live matrix (8 runs by default: 4 MSAs × 2 conditions):

| Axis | Values |
|------|--------|
| Documents | Edgemode, NuScale, Aspira, Pulmatrix MSAs |
| Conditions | `clean`, `noisy_prompt` |
| Strategy | `parallel_grounded` (default) |
| Model | `gemini-2.5-pro` (default) |
| Seeds | Deterministic (`DETERMINISTIC_SEEDS`) |

If the API key is not set, the runner prints a clear message and exits with code **2**.

### Outputs

Written to `experiments/live_gemini/`:

- **`results.json`** — one row per run with metrics and task scores
- **`REPORT.md`** — aggregated tables
- **`manifest.json`** — configuration snapshot (`status: completed` after a run)

Commit these files after a live run so reviewers can inspect real LLM baseline metrics.

### Customize

```powershell
python -m benchmark.run_live_experiment `
  --provider gemini `
  --documents edgar_edgemode_inc_ex10.1 `
  --conditions clean noisy_prompt `
  --model gemini-2.5-pro `
  --output experiments/live_gemini/results.json
```

## Adding a new MSA

1. Fetch: `python -m benchmark.fetch_contracts`
2. Author answers: `benchmark/answers/{document_id}.yaml`
3. Validate: `assert_all_answers_valid([document_id])`
4. Re-run: `python -m benchmark.run_experiment --documents {document_id}`

## CI suggestion

```yaml
- run: pip install -e ".[dev]"
- run: python -m pytest tests/ -q
- run: python -m benchmark.run_experiment
- run: git diff --exit-code experiments/mock_baseline/
```

Fails if committed baseline drifts without intentional update.
