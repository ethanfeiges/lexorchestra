# LexOrchestra

Legal-document orchestration with a canonical source of truth (SoT), programmatic noise, and citation grounding.

This is a resume project — not a Harvey clone, a production legal product, or a broad benchmark suite. It asks a narrower question:

> When agents see plausible wrong document versions alongside the signed contract, does orchestration plus canonical verification still produce correct, grounded answers?

## Background: agent orchestration in modern applications

Most production AI systems no longer rely on a single monolithic prompt. They **orchestrate** work across multiple specialized steps or agents:

1. **Decompose** a user goal into subtasks (extract a fact, check a policy rule, summarize a section).
2. **Run subtasks in parallel** — often on different models or with different prompts — to reduce latency and let each agent focus on one job.
3. **Collect structured outputs** (claims, citations, tool results) rather than treating free-form text as final.
4. **Verify downstream** — against a database, API, or canonical document store — before surfacing an answer.

This pattern shows up in legal review, customer support, code agents, and RAG pipelines. The orchestrator schedules and merges; it does **not** decide what is true. Truth lives in a separate layer — a CRM record, a code index, or here, a **parsed contract store**.

That separation matters because LLM subagents are unreliable witnesses. They can paraphrase, invent clause numbers, or anchor on whichever document version appeared first in context. Orchestration without verification gives you fast, confident-sounding wrong answers. The hard problem is not "can a model read a contract?" but **can the system enforce that every cited claim points at the right source of truth?**

## Objective: test SoT citation under noise

In real legal workflows, agents rarely see one pristine document. A deal room might contain an executed MSA, an old draft missing a liability section, a cached export with wrong dollar amounts, and a bad OCR parse with scrambled clause IDs. Models are told which copy is authoritative — but under distraction, some still cite the wrong version.

LexOrchestra **simulates that confusion** and **measures whether the pipeline recovers**:

| Layer | Responsibility |
|-------|----------------|
| **SoT** | One canonical parse (`signed_contract`) — the only authority for verification |
| **Orchestration** | Runs extract and playbook subtasks; agents may *see* decoy versions in the prompt |
| **Grounding verifier** | Rejects claims whose clause IDs or quotes do not match the canonical store |
| **Benchmark** | Scores grounding, decoy citation rate, and task accuracy under controlled conditions |

The experiment objective is to **test and ensure correct SoT citation when noise is introduced**. A naive setup (one clean document, easy questions, string matching) scores ~100% and proves little. LexOrchestra adds **programmatic noise**: each run can include 1–2 decoy contract versions derived from the real parse. Metrics then separate agents (or orchestration strategies) that cite truth from those that anchor on decoys — and show whether verification catches the failures either way.

## Core idea

Three layers, one invariant — **verification always uses the signed contract, never model memory**:

1. **SoT** — Parse the contract into clauses with stable IDs. That parse is the only authority for verification.
2. **Orchestration** — Run extract and playbook tasks in parallel (single model or multi-model). Agents produce *claims*, not final answers.
3. **Grounding** — Reject claims whose clause IDs or quotes do not match the canonical store, including claims that match decoy text.

The benchmark varies **what agents see** (`clean` vs `noisy_prompt`) and **how work is scheduled** (`single` vs `parallel_grounded`), while holding the verifier and answer keys fixed. That isolates whether orchestration plus canonical checking holds up when plausible wrong documents are in context.

## Run the experiment

No API keys required. The default path uses **mock agent profiles** (no LLM calls) and is the primary route for local dev, CI, and the committed GitHub baseline.

```powershell
pip install -e ".[dev]"
python -m benchmark.run_experiment
python -m benchmark.run_ablations
python -m pytest tests/ -q
python scripts/check_baseline.py   # local CI parity: regenerate + diff check
```

Output goes to [`experiments/mock_baseline/`](experiments/mock_baseline/) and [`experiments/ablations/`](experiments/ablations/) — each with `results.json`, `REPORT.md`, and `manifest.json`. Commit those files so reviewers can see expected metric patterns without re-running.

CI (`.github/workflows/ci.yml`) runs pytest, answer-key validation, mock baseline regeneration, and fails if `experiments/mock_baseline/` drifts. More flags: [`experimentDocs/EXPERIMENT.md`](experimentDocs/EXPERIMENT.md).

### What one run does

For each cell in the experiment matrix, the runner:

1. **Parses** the MSA into a canonical SoT and builds a **noise bundle** (signed contract + programmatic decoys), seeded per run.
2. **Assembles a prompt** under the chosen condition — `clean` shows only the signed contract; `noisy_prompt` adds 1–2 decoy versions (`draft_missing_section`, `outdated_wrong_terms`, `bad_parse_extra_clause`, `bad_parse_wrong_ids`).
3. **Runs orchestration** — parallel **extract** and **playbook** tasks (or a single model for both under `single` strategy).
4. **Verifies claims** against the canonical store only (clause IDs, quotes, decoy detection).
5. **Scores tasks** against per-document answer YAML and aggregates run metrics.

Mock profiles swap in simulated agent responses at step 3; live LLM clients use the same pipeline (optional, needs API keys).

### Experiment matrix (default baseline)

| Axis | Values | Role |
|------|--------|------|
| **Documents** | Edgemode, NuScale, Chime MSAs | Real SEC EDGAR EX-10 fixtures in [`fixtures/contracts/public/`](fixtures/contracts/public/) |
| **Conditions** | `clean`, `noisy_prompt` | Whether decoy SoT versions appear in the agent prompt |
| **Strategies** | `single`, `parallel_grounded` | One model for all tasks vs separate extract/playbook models in parallel |
| **Mock profiles** | `canonical`, `decoy_anchored` | Simulated agent that cites truth vs one anchored on decoy text |
| **Seeds** | Fixed (`DETERMINISTIC_SEEDS`) | Reproducible decoy selection and corruptions on any machine |

That yields **24 runs** (3 docs × 2 conditions × 2 strategies × 2 profiles). Override any axis:

```powershell
python -m benchmark.run_experiment `
  --documents edgar_edgemode_inc_ex10.1 `
  --conditions clean noisy_prompt `
  --profiles canonical
```

### Benchmark tasks and answer keys

Benchmarks are **not** a generic legal QA suite. Each document has hand-authored answers in [`benchmark/answers/{document_id}.yaml`](benchmark/answers/):

| Task type | What it measures | Examples (Edgemode MSA) |
|-----------|------------------|-------------------------|
| **Playbook** | Pass/fail rules with required quotes from canonical clauses | ICC arbitration present? Mutual indemnity? |
| **Extract** | Factual answers tied to acceptable clause IDs | Minimum annual fee indexation percentage |

Answers are validated against the canonical parse before each run. Task accuracy requires **grounded** claims that match expected verdicts and substrings — citing a decoy that happens to contain similar text still fails verification.

### Metrics

| Metric | Meaning |
|--------|---------|
| **Grounding rate** | Share of claims with valid `clause_id` + quote in the **signed** contract |
| **Decoy citation rate** | Share of claims matching decoy text or a non-canonical `sot_label` |
| **Task accuracy** | Share of playbook/extract tasks scored correct against the answer key |

Expected pattern in the committed baseline: `canonical` stays near 100% under both conditions; `decoy_anchored` drops grounding and accuracy under `noisy_prompt` — proving the verifier and metrics distinguish truth from noise.

### Mock profiles

Mock profiles simulate agent behavior without calling an LLM. Same orchestrator, verifier, and answer keys — only the returned claims change.

| Profile | What it simulates |
|---------|-------------------|
| `canonical` | Agent always cites `signed_contract` with answer-aligned quotes. |
| `decoy_anchored` | Agent faithfully cites decoy text from the prompt (`outdated_wrong_terms`, etc.). |

### Committed experiment suites

**Live Gemini tests** (what we ran with the API): **[`experimentDocs/EXPERIMENTS.md`](experimentDocs/EXPERIMENTS.md)** — 4 runs on real SEC MSAs, task-by-task outcomes, real-world scenarios.

**Mock/CI tests** (no API): **[`experimentDocs/MOCK_EXPERIMENTS.md`](experimentDocs/MOCK_EXPERIMENTS.md)** — 24-run baseline + 6 ablations for verifier regression.

| Suite | Runs | Command |
|-------|------|---------|
| **Live Gemini** | 4 | `python -m benchmark.run_live_experiment --provider gemini` |
| Mock baseline | 24 | `python -m benchmark.run_experiment` |
| Ablations | 6 | `python -m benchmark.run_ablations` |

Interpretation: [`experimentDocs/FINDINGS.md`](experimentDocs/FINDINGS.md).

#### Live Gemini highlights

Uses **orchestrated subtasks** (`parallel_grounded`): extract and playbook run as **parallel Gemini API calls**, then merge at the verifier.

- **4 MSAs** by default (Edgemode, NuScale, Aspira, Pulmatrix); Chime optional via `--include-chime`
- **8 runs** (4 docs × clean/noisy); prior committed baseline is 4 runs (Edgemode + NuScale)
- **NuScale under noise:** decoy citation when `outdated_wrong_terms` in prompt


```
SEC EDGAR MSA (.txt)
    → docProcessing/  parse + bundle (signed_contract + decoys)
    → orchestrator/   extract + playbook tasks
    → grounding/      verify claims against canonical only
    → benchmark/      answer keys, metrics, experiment matrix
```

## Contract data

Fixtures are real MSAs from SEC EDGAR EX-10 in [`fixtures/contracts/public/`](fixtures/contracts/public/). Decoys are programmatic corruptions of each canonical parse — not separate synthetic contracts.

```powershell
python -m benchmark.fetch_contracts --limit 3
```

## Repo layout

```
docProcessing/    Parse contracts, build decoy bundles, format prompt blocks
orchestrator/     Task prompts, parallel runner
grounding/        Verifier + decoy detection
models/           Mock client + optional Gemini live client
benchmark/        Answer keys, mock profiles, experiment runners
fixtures/         SEC EDGAR contract fixtures
experiments/      Committed baselines (mock, ablations, live Gemini)
experimentDocs/   Experiment write-ups, findings, run commands
scripts/          Local CI helpers
context/          Design docs (STORE.md, phase specs)
tests/
.github/workflows/  CI: pytest + answer validation + baseline regression
```

## Documentation

- [`experimentDocs/EXPERIMENTS.md`](experimentDocs/EXPERIMENTS.md) — **live Gemini tests** (real MSAs, task outcomes, real-world scenarios)
- [`experimentDocs/MOCK_EXPERIMENTS.md`](experimentDocs/MOCK_EXPERIMENTS.md) — mock baseline + ablations (CI, no API)
- [`experimentDocs/FINDINGS.md`](experimentDocs/FINDINGS.md) — live Gemini interpretation
- [`experimentDocs/HYPOTHESIS.md`](experimentDocs/HYPOTHESIS.md) — research question, falsification criteria
- [`experimentDocs/EXPERIMENT.md`](experimentDocs/EXPERIMENT.md) — run commands and flags
- [`benchmark/answers/README.md`](benchmark/answers/README.md) — benchmark answer keys (task scoring)
- [`context/STORE.md`](context/STORE.md) — architecture, data model, decisions
- [`context/phases/DOCUMENTS.md`](context/phases/DOCUMENTS.md) — contract parsing and bundle spec
- [`context/phases/ORCHESTRATION.md`](context/phases/ORCHESTRATION.md) — orchestration spec

## Live LLM runs (optional)

The mock baseline is complete on its own. Run a small live matrix with **Gemini** (Google AI Studio):

```powershell
pip install -e ".[llm]"

# Gemini (default model: gemini-2.5-pro)
$env:GEMINI_API_KEY = "your-key-from-aistudio"
python -m benchmark.run_live_experiment --provider gemini
```

Get a Gemini API key at [Google AI Studio](https://aistudio.google.com/apikey). Results land in `experiments/live_gemini/`.

## License

MIT — see [`LICENSE`](LICENSE).
