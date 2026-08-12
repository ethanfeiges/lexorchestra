# LexOrchestra

LexOrchestra is a research benchmark for legal document orchestration. It runs parallel Gemini subtasks on real SEC EDGAR master service agreements, keeps a parsed canonical source of truth, and verifies that every model claim is grounded in that document rather than in plausible decoy versions that appear in the prompt.

**Research question:** When plausible wrong document versions sit next to the real contract, does orchestration plus canonical verification still produce grounded answers?

---

## How the project works

LexOrchestra separates three concerns that are often conflated in LLM pipelines: what the document actually says, what the models claim it says, and whether those claims are correct.

### The pipeline

Each benchmark run follows the same four-stage flow:

```
Real MSA (SEC EDGAR EX-10)
    → Parse into clause store (canonical SoT)
    → Build prompt bundle (signed contract + decoys)
    → Orchestrate parallel subtasks via Gemini (extract + playbook)
    → Verify claims against canonical store
    → Score against gold answer keys
```

**1. Parse and store.** Each real contract file in `legalDocs/contracts/public/` is read and split into numbered chunks called **clauses**, each tagged with a stable ID like `c-012`. Together, those chunks form the project's ground truth for that document.

**What "canonical" means:** *Canonical* is just the official reference copy—the parsed text of the real filed contract, broken into addressable pieces.

**2. Build a noisy prompt bundle.** The system creates several labeled document versions from the same canonical parse. One version, `signed_contract`, is an exact copy of the canonical text. The others are programmatic corruptions—missing clauses, altered terms, wrong IDs, or extra boilerplate. Gemini sees one or more of these versions in its prompt depending on the experimental condition.

**3. Orchestrate subtasks.** Two legal subtasks run on the prompt bundle through the Gemini API:

- **Extract** — Answer factual questions with structured claims (statement, `clause_id`, quote, `sot_label`).
- **Playbook** — Evaluate pass/fail rules from a legal checklist (for example, "Does the contract require ICC arbitration?").

Tasks can run **sequentially** with one model (`single`) or **in parallel** (`parallel_grounded`). In every case, output is structured JSON claims, not free-form prose.

**4. Verify and score.** The grounding verifier checks every claim against the canonical clause store. A claim is grounded only if its `clause_id` exists in the canonical parse and its quote is an exact substring of that clause's text. Claims that match decoy text or cite the wrong `sot_label` are flagged even when they look plausible. Task accuracy is scored separately against pre-authored answer keys in `benchmark/answers/{document_id}.yaml`.

### Source of truth is fixed before any LLM call

The model does not choose which document version is authoritative. The pipeline fixes truth deterministically:


| Layer                       | What it is                                     | Who sees it                       |
| --------------------------- | ---------------------------------------------- | --------------------------------- |
| Raw file                    | Executed MSA text from SEC EDGAR               | Parser only                       |
| Canonical clauses           | Parsed, ID'd chunks from that file             | Verifier and answer-key authoring |
| `signed_contract` candidate | Exact copy of canonical, labeled in the prompt | Gemini                            |
| Decoy candidates            | Corruptions of the same canonical parse        | Gemini (as distractions)          |


Answer keys are authored once per document from the canonical parse. They do not change when different decoys appear in a run.

### Experimental axes

The benchmark varies conditions and strategies while keeping the verifier and answer keys fixed:


| Axis          | Values                        | What it tests                                                  |
| ------------- | ----------------------------- | -------------------------------------------------------------- |
| **Condition** | `clean`, `noisy_prompt`       | Whether Gemini stays grounded when decoys appear in the prompt |
| **Strategy**  | `single`, `parallel_grounded` | Whether parallel scheduling changes grounding behavior         |


The default matrix runs 8 configurations (4 documents × 2 conditions) using `gemini-2.0-flash`.

### Metrics


| Metric                  | What it measures                                                                    |
| ----------------------- | ----------------------------------------------------------------------------------- |
| **Grounding rate**      | Share of claims with a valid `clause_id` and quote in the signed canonical contract |
| **Decoy citation rate** | Share of claims that match decoy text or cite a wrong `sot_label`                   |
| **Task accuracy**       | Share of playbook and extract answers that match the gold answer key                |


---

## Local setup

These steps get LexOrchestra running on your machine from a fresh clone. You need a Gemini API key to run experiments.

### Prerequisites

- **Python 3.11 or newer.** Check with `python --version`.
- **Git** to clone the repository.
- A **Gemini API key** from [Google AI Studio](https://aistudio.google.com/apikey).
- A terminal. The examples below use PowerShell on Windows; the same commands work in bash with minor syntax differences.

### 1. Clone the repository

```powershell
git clone https://github.com/your-org/lexorchestra.git
cd lexorchestra
```

Replace the URL with your fork or the canonical remote if it differs.

### 2. Create and activate a virtual environment

Using a virtual environment keeps project dependencies isolated from your system Python.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux, activate with `source .venv/bin/activate` instead.

### 3. Install the package

Install LexOrchestra in editable mode with development dependencies:

```powershell
pip install -e ".[dev]"
```

This installs the core packages (`docProcessing`, `orchestrator`, `grounding`, `benchmark`, `models`) and the `google-genai` client used for all experiment runs.

Optional extras:

```powershell
pip install -e ".[pdf]"    # PDF parsing support
pip install -e ".[docx]"   # DOCX parsing support
```

### 4. Configure your API key

Copy the example environment file and add your key:

```powershell
copy .env.example .env
```

Edit `.env` and set `GEMINI_API_KEY`. Do not commit `.env` to version control.

Alternatively, set the key in your shell session:

```powershell
$env:GEMINI_API_KEY = "your-key"
```

### 5. Verify the installation

Run the test suite to confirm everything is wired correctly:

```powershell
python -m pytest tests/ -q
```

All tests should pass. Unit tests exercise parsing, bundle construction, orchestration, and verification without calling the Gemini API.

### 6. Run the experiment

Run the default Gemini matrix (4 MSAs × 2 conditions):

```powershell
python -m benchmark.run_experiment --provider gemini
```

This writes results to `experiments/live_gemini/`:

- `results.json` — one row per run with metrics and task scores
- `REPORT.md` — aggregated summary tables
- `manifest.json` — configuration snapshot for reproducibility

Open `experiments/live_gemini/REPORT.md` to inspect grounding rates, decoy citation rates, and task accuracy.

For a smaller smoke test on one document:

```powershell
python -m benchmark.run_experiment --provider gemini `
  --documents edgar_edgemode_inc_ex10.1 `
  --conditions clean
```

---

## Quick reference

```powershell
pip install -e ".[dev]"
$env:GEMINI_API_KEY = "your-key"
python -m benchmark.run_experiment --provider gemini
python -m pytest tests/ -q
python scripts/sync_experiment_docs.py --check
```

More flags and customization options are documented in `[experimentDocs/EXPERIMENT.md](experimentDocs/EXPERIMENT.md)`.

---

## Default matrix


| Axis       | Values                                    |
| ---------- | ----------------------------------------- |
| Model      | `gemini-2.0-flash`                        |
| Documents  | Edgemode, NuScale, Aspira, Pulmatrix MSAs |
| Conditions | `clean`, `noisy_prompt`                   |
| Strategy   | `parallel_grounded` (default)             |


8 runs (4 × 2). Override document or condition selection:

```powershell
python -m benchmark.run_experiment `
  --provider gemini `
  --documents edgar_edgemode_inc_ex10.1 `
  --conditions clean noisy_prompt `
  --strategy single
```

### Tasks

Per-document answer keys live in `benchmark/answers/{document_id}.yaml`:

- **Playbook** — Pass/fail rules with required quotes (for example, "Is ICC arbitration present?").
- **Extract** — Factual answers tied to clause IDs (for example, "What is the fee indexation percentage?").

Task accuracy requires grounded claims that match the key. Decoy text that happens to look similar still fails verification.

---

## Contract data

Real MSAs come from SEC EDGAR EX-10 filings in `[legalDocs/contracts/public/](legalDocs/contracts/public/)`. Decoys are corruptions of each parse, not separate synthetic documents.

To fetch additional contracts from EDGAR:

```powershell
python -m benchmark.fetch_contracts --limit 3
```

---

## Repository layout

```
docProcessing/    Parse contracts, build bundles, format prompts
orchestrator/     Task definitions and parallel runner
grounding/        Verifier and decoy detection
models/           Gemini client and test stubs
benchmark/        Answer keys, experiment runner, metrics
legalDocs/        SEC EDGAR contract fixtures
experiments/      Committed Gemini baseline results
experimentDocs/   Run write-ups and findings
context/          Design docs and architecture decisions
tests/            Unit and integration tests
scripts/          Doc sync utilities
```

---

## Documentation

- `[experimentDocs/EXPERIMENTS.md](experimentDocs/EXPERIMENTS.md)` — Gemini runs and real-world task outcomes
- `[experimentDocs/FINDINGS.md](experimentDocs/FINDINGS.md)` — Interpretation of results
- `[experimentDocs/HYPOTHESIS.md](experimentDocs/HYPOTHESIS.md)` — Research question and predictions
- `[context/STORE.md](context/STORE.md)` — Architecture and decision log

---

## License

MIT — see `[LICENSE](LICENSE)`.