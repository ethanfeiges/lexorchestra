# Orchestration Phase — Implementation Design

> **Use this file as a Cursor prompt** to implement the orchestration layer for LexOrchestra.
>
> **Live Gemini experiments:** [`experimentDocs/EXPERIMENTS.md`](../experimentDocs/EXPERIMENTS.md). **Mock/CI:** [`experimentDocs/MOCK_EXPERIMENTS.md`](../experimentDocs/MOCK_EXPERIMENTS.md).
>
> Before starting, read [`context/STORE.md`](../STORE.md) and confirm the documents layer is complete (`context/phases/DOCUMENTS.md`).

---

## Your role

You are implementing **Phase 2: Orchestration** (plus the grounding verifier and benchmark hooks that orchestration depends on). This phase runs parallel LLM subtasks on MSAs, feeds agents a **noisy prompt bundle**, and evaluates whether outputs are correct **only if the agent used the canonical SoT**, not a decoy.

**Do not re-implement SoT parsing or bundle corruption logic** — call the existing `docProcessing/` API.

---

## The core research question

> When subagents receive multiple plausible document versions (one true, several corrupted), can orchestration + canonical verification produce correct legal subtask answers — and can we **measure** whether agents anchored on noise?

This is **not** a test of whether models memorized which fixture file is "the real MSA." It is a test of **in-run discrimination**: given fresh noise every run, does the pipeline still ground answers in `signed_contract`?

---

## How SoT is determined (ground truth chain)

SoT is **not** chosen by the model and **not** inferred at runtime. It is fixed by a deterministic pipeline before any LLM call:

```
Real MSA file (SEC EDGAR EX-10)
    → parse_document()           → canonical clauses (list[Clause])
    → build_bundle(seed=...)      → SoTBundle
         ├── canonical            ← VERIFIER TRUTH (always)
         └── candidates[]
               ├── signed_contract      valid=True   ← same text as canonical
               ├── draft_missing_section   valid=False
               ├── outdated_wrong_terms      valid=False
               ├── bad_parse_extra_clause      valid=False
               └── bad_parse_wrong_ids         valid=False
```

### What "canonical" means

| Layer | What it is | Who sees it |
|-------|------------|-------------|
| **Raw file** | `fixtures/contracts/public/edgar_*.txt` — the executed MSA text | Parser only |
| **Canonical clauses** | `SoTBundle.canonical` — parsed, ID'd chunks from that file | Verifier, answer-key authoring, never written by agents |
| **signed_contract candidate** | One entry in `bundle.candidates` with `valid=True`; clause text **must equal** canonical (enforced by Pydantic validator) | Agents (in prompt, labeled) |
| **Decoy candidates** | Programmatic corruptions of canonical (`missing_clause`, `altered_text`, etc.) | Agents (in prompt, labeled) |

**Invariant:** Exactly one candidate has `valid=True` and label `signed_contract`. The grounding verifier **always** checks claims against `bundle.canonical` via `SoTStore` — never against decoys.

### Why this is authoritative

1. **Source of truth is extrinsic** — a real filed contract, not model output.
2. **Truth is structural** — parse → store; agents cannot redefine it.
3. **Decoys are derived** — every fake version is a corruption of the same canonical parse, so comparisons are controlled.
4. **Labels are honest in prompts** — agents are told `signed_contract` is the executed copy; the experiment tests whether they **follow** that instruction under distraction.

### Answer keys (task correctness)

Task accuracy is judged against **canonical-derived answers**, not model opinion:

| Answer source | How it is produced |
|-------------|-------------------|
| **Playbook pass/fail** | Rule engine or one-time human/script annotation over canonical clauses (YAML rules → expected answer + supporting `clause_id`) |
| **Extract answers** | Expected statement + `clause_id` + quote substring from canonical |
| **Grounding** | Mechanical: `clause_id` exists in canonical AND quote matches clause text |

Answer keys are authored **once per document** from canonical and stored in `benchmark/answers/{document_id}.yaml`. They do not depend on which decoys appear in a given run.

---

## Per-run fresh noise (anti-memorization design)

### The concern

If every benchmark run uses `seed=42` on the same three MSAs with the same decoys, a model might **cache** "for Edgemode, ignore outdated_wrong_terms" rather than reading the prompt. That would invalidate the experiment.

### Principle: separate **document identity** from **run identity**

| Concept | Stable across runs | Varies per run |
|---------|-------------------|----------------|
| Which MSA | Yes — fixture set from SEC | No |
| Canonical parse | Yes — deterministic parser | No |
| Gold labels | Yes — from canonical | No |
| **Decoy instances** | No | **Yes — new seed each run** |
| **Which decoys shown** | No | **Yes — sampled per run** |
| **Decoy parameters** | No | **Yes — which clause altered, which substitution** |

### Run manifest

Each orchestration run creates a `RunManifest`:

```python
run_id: str                    # uuid
document_id: str               # e.g. edgar_edgemode_inc_ex10.1
seed: int                      # os.urandom or secrets — NOT fixed 42 in eval
decoys_in_prompt: list[str]    # e.g. ["outdated_wrong_terms", "draft_missing_section"]
condition: str                 # clean | noisy_prompt | noisy_task
strategy: str                  # single | parallel_grounded
models: dict[str, list[str]]   # task → model ids
created_at: str
```

Build flow:

```python
seed = secrets.randbelow(2**31)  # fresh every run
bundle = build_bundle_from_file(path, seed=seed)
prompt_block = format_candidates_for_prompt(
    bundle.candidates,
    labels=["signed_contract"] + run_manifest.decoys_in_prompt,
)
```

### What changes with a new seed

Even with the same four corruption **types**, a new seed changes:

| Corruption | Seed-sensitive behavior |
|------------|-------------------------|
| `altered_text` | Which substitution applies; which numeric phrase is halved |
| `missing_clause` | Target clause if multiple match "liability" (future: extend to random eligible clause) |
| `reordered` | Shuffle order of clauses |
| `extra_clause` | Currently static template — **extend** to pick among N boilerplate templates via `rng` |

### Prompt composition varies per run

Do not always show the same decoy pair. Sample 1–2 decoys from the four types:

```python
rng = random.Random(run_seed)
decoy_labels = rng.sample(
    ["draft_missing_section", "outdated_wrong_terms", "bad_parse_extra_clause", "bad_parse_wrong_ids"],
    k=rng.randint(1, 2),
)
```

Optionally shuffle candidate order in the prompt (signed_contract not always first) — **but** keep the header instruction: *cite from signed_contract only*.

### Conditions (experimental arms)

| Condition | Prompt contents | Purpose |
|-----------|-----------------|---------|
| `clean` | `signed_contract` only | Upper bound baseline |
| `noisy_prompt` | `signed_contract` + 1–2 random decoys | Primary discrimination test |
| `noisy_task` | Same as noisy_prompt + playbook rules that **flip** if a decoy is used | Task accuracy drops when agent anchors on wrong version |

### Anti-caching checklist

- [ ] Eval runs use **random seeds**, not `seed=42`
- [ ] Decoy subset and order vary per run
- [ ] Rotate across **multiple real MSAs** (3+ fixtures, fetch more over time)
- [ ] Never train or few-shot on "which label is correct" — instruct behavior, don't leak eval structure
- [ ] Log `run_id` + `seed` + `decoys_in_prompt` for reproducibility **after the fact**, not predictability before
- [ ] Unit tests keep `seed=42` for determinism; **benchmark eval does not**

---

## Why tasks must require SoT (not noise)

A task is well-designed for this experiment if:

> **A subagent that faithfully cites the wrong decoy will fail** task accuracy and/or canonical grounding — even if the answer is internally consistent with that decoy.

### Task types (v1)

| Task | Input | Output | SoT-dependent because… |
|------|-------|--------|------------------------|
| **extract** | Question about a clause topic | Claim: statement + `clause_id` + quote | Decoys alter/remove/shuffle clauses; correct quote exists only in canonical |
| **playbook** | Firm rule (YAML) | Claim: pass/fail + justification cite | Rules keyed to canonical facts (e.g. liability cap amount, term length) |

### Example: liability cap (discriminating)

Canonical (signed_contract):

```
[c-017] ... liability cap ... $10,000,000 in the aggregate ...
```

Decoy `outdated_wrong_terms` (same clause id, wrong text):

```
[c-017] ... liability cap ... $5,000,000 in the aggregate ...
```

Playbook rule:

```yaml
- id: liability_cap_10m
  question: "Is aggregate liability capped at exactly $10,000,000?"
  expected: fail  # if cap is absent OR different amount
  canonical_clause_ids: [c-017]
```

| Agent behavior | Task result | Grounding result |
|----------------|-------------|------------------|
| Cites canonical, $10M quote | **Correct** | grounded |
| Cites decoy, $5M quote | **Wrong** (answer key expects canonical fact) | ungrounded vs canonical |
| Cites decoy clause_id with canonical quote | **Wrong** | text_mismatch |
| Hallucinates clause | **Wrong** | missing_clause |

The agent **cannot** pass by using `outdated_wrong_terms` — the answer key and verifier both reference canonical only.

### Example: missing section (discriminating)

Decoy `draft_missing_section` removes the liability clause entirely.

Playbook rule `limitation_of_liability_present`:

- Gold on canonical: **pass** (clause exists)
- Agent using decoy: likely **fail** ("no limitation clause") → task wrong

Extract task "What is the aggregate liability cap?":

- Canonical: answer with quote containing `$10,000,000`
- Decoy-only agent: "No limitation of liability section" → task wrong

### Example: extra clause (discriminating)

Decoy `bad_parse_extra_clause` adds arbitration boilerplate not in the real MSA.

Playbook rule `binding_arbitration_required`:

- Gold on canonical: **fail** (NuScale MSA has mediation/arbitration in §19 but not the injected boilerplate text)
- Agent citing fake clause: may **pass incorrectly** on task → caught because quote doesn't match **canonical** clause set

Design playbook rules to reference **canonical-only** facts where decoys diverge.

### Tasks to avoid (non-discriminating)

| Bad task | Why |
|----------|-----|
| "Which document version is the signed contract?" | Trivial label read, not legal reasoning |
| "List all clause IDs" | Same IDs across reordered decoy (different text mapping) — confusing but not legal |
| Rules satisfied by text identical in all candidates | No discrimination |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        RunOrchestrator                          │
│  1. Load MSA path + playbook + run config                       │
│  2. seed ← fresh random                                         │
│  3. bundle ← build_bundle_from_file(path, seed)                 │
│  4. store ← SoTStore(bundle.canonical)   ← verifier truth       │
│  5. answers ← load_answers(document_id)  ← task truth           │
│  6. prompt_ctx ← sample decoys + format_candidates_for_prompt   │
│  7. spawn tasks in parallel (asyncio)                           │
│  8. parse responses → Claim[]                                   │
│  9. verify each claim vs store (canonical only)                 │
│ 10. score vs answers → RunResult + metrics                       │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
   docProcessing/ (existing)    models/ clients     grounding/ verifier
```

### Layer boundaries (critical)

| Component | Reads canonical | Reads decoys | Writes truth |
|-----------|-----------------|--------------|--------------|
| `docProcessing/build_bundle` | Yes (creates) | Yes (creates) | Yes (defines) |
| Prompt builder | Yes | Yes (for display) | No |
| Subagents (LLMs) | Yes (in prompt) | Yes (in prompt) | No |
| Grounding verifier | **Yes only** | **Never** | No |
| Gold / scoring | **Yes only** | **Never** | No |

---

## Subagent design

### One prompt per (task × model)

Each subagent receives:

1. **System**: You are a contract analyst. Cite only from `signed_contract`. Output JSON claims.
2. **Document block**: `format_candidates_for_prompt(...)` — signed + sampled decoys
3. **Task block**: extract question OR playbook rules
4. **Schema**: response format

Subagents do **not** receive:

- Which decoys are fake (beyond label names that imply status)
- Gold labels
- Verifier logic
- Other models' outputs (v1 — no cross-agent debate)

### Claim schema

```python
class Claim(BaseModel):
    statement: str
    clause_id: str
    quote: str
    sot_label: str | None = None   # optional: which prompt label agent believes it used
    rule_id: str | None = None     # playbook only
    verdict: str | None = None     # playbook: pass | fail
```

`sot_label` powers the **decoy citation rate** metric: if `sot_label != "signed_contract"` but quote matches a decoy, that's explicit anchoring failure.

### Parallelism

```python
# parallel_grounded: all (task, model) pairs concurrently
tasks = [
    run_extract(model="gpt-4o", ...),
    run_extract(model="claude-sonnet", ...),
    run_playbook(model="gpt-4o", ...),
    run_playbook(model="claude-sonnet", ...),
]
results = await asyncio.gather(*tasks)
```

`single` strategy: one model, extract then playbook sequentially — same prompts, same verifier.

---

## Grounding verifier

For each claim, against **canonical store only**:

1. `clause_id in store` → else `ungrounded(missing_clause)`
2. `store.quote_matches(clause_id, quote)` → else `ungrounded(text_mismatch)`
3. Else `grounded`

Optional enhancement for decoy metric:

4. If quote matches decoy candidate but not canonical → tag `decoy_match: {label}`

Do **not** accept a claim as grounded because it matches a decoy.

---

## Scoring (how we know subagents succeeded)

### Per-claim metrics

| Metric | Definition |
|--------|------------|
| **Grounding rate** | grounded claims / total claims |
| **Decoy citation rate** | claims where quote matches decoy but not canonical, OR `sot_label != signed_contract` |
| **Task accuracy** | playbook verdict matches answer key AND extract statement matches answer key |

### Per-run aggregation

```python
class RunResult(BaseModel):
    run_id: str
    document_id: str
    condition: str
    strategy: str
    seed: int
    decoys_in_prompt: list[str]
    verified_claims: list[VerifiedClaim]
    task_scores: dict[str, bool]   # rule_id or extract_q → correct?
    metrics: RunMetrics
```

### Task correctness logic

**Playbook:**

```python
def score_playbook(claim, rule) -> bool:
    if not claim.grounded:
        return False
    return claim.verdict == rule.expected
    # optional: clause_id in rule.canonical_clause_ids
```

**Extract:**

```python
def score_extract(claim, answers) -> bool:
    if not claim.grounded:
        return False
    return (
        claim.clause_id in answers.acceptable_clause_ids
        and answers.required_substrings in normalize(claim.quote)
    )
```

A subagent **passes** the experiment only if it produces **grounded, task-correct** claims — which requires canonical SoT for discriminating tasks.

---

## Repository layout (create this)

```
orchestrator/
├── __init__.py
├── models.py          # Claim, VerifiedClaim, RunManifest, RunResult
├── tasks.py           # extract + playbook prompt templates
├── runner.py          # asyncio parallel execution
└── run.py             # high-level run_benchmark_case()

grounding/
├── __init__.py
├── verifier.py        # verify_claims(store, claims) → VerifiedClaim[]
└── decoy_detect.py    # optional: match quote against decoy candidates

models/
├── __init__.py
├── base.py            # ModelClient protocol
├── mock_client.py     # deterministic mock responses
└── gemini_client.py   # live Gemini API adapter

benchmark/
├── answers/           # per-document YAML answer keys
├── conditions.py      # clean | noisy_prompt | noisy_task
├── metrics.py         # aggregate decoy rate, accuracy, etc.
├── run_experiment.py  # mock baseline matrix
├── run_ablations.py   # verifier ablations
└── run_live_experiment.py  # Gemini live matrix

tests/
├── orchestrator/
├── grounding/
└── benchmark/
```

---

## Playbook format (answer-aligned)

```yaml
document_id: edgar_nuscale_power_corp_ex10.15
rules:
  - id: liability_cap_10m
    question: "Is Fluor's aggregate liability capped at $10,000,000?"
    expected: pass
    canonical_clause_ids: ["c-017"]
    required_substrings: ["$10,000,000"]

  - id: mutual_indemnity
    question: "Is indemnification mutual (both parties)?"
    expected: fail
    canonical_clause_ids: ["c-017"]
    notes: "Fluor indemnifies NuScale; not mutual"

extract_questions:
  - id: agreement_term
    question: "What is the term of the agreement?"
    acceptable_clause_ids: ["c-007"]
    required_substrings: ["twenty (20) years"]
```

Gold files are authored once from canonical review (agent-assisted OK), then frozen for eval.

---

## Implementation phases (suggested order)

### Step 1 — Grounding verifier (no LLM)

- Implement `grounding/verifier.py` against `SoTStore`
- Unit tests with **injected claims** (including quotes copied from decoys)
- Expect decoy quotes → `ungrounded`

### Step 2 — Orchestrator skeleton (mock LLM)

- `RunManifest`, task prompt assembly, parallel runner
- Mock model returns canned JSON claims
- End-to-end test: bundle → prompt → mock → verify → score

### Step 3 — Gold labels + metrics

- One answer YAML per fixture MSA
- `benchmark/metrics.py` computes decoy rate, accuracy
- Deterministic tests with fixed seed

### Step 4 — Real model clients

- OpenAI + Anthropic adapters behind `ModelClient` protocol
- Env-var API keys; skip integration tests in CI without keys

### Step 5 — Eval harness

- `run_experiment.py`: for each MSA × condition × strategy, fresh seed, N repetitions
- Output CSV/JSON for resume charts

---

## End-to-end run example

**Input:** `edgar_nuscale_power_corp_ex10.15.txt`, condition=`noisy_prompt`, strategy=`parallel_grounded`, seed=`1847293012`

1. **Build bundle** with seed → decoys differ from last run's altered amounts
2. **Sample decoys:** `["outdated_wrong_terms", "bad_parse_wrong_ids"]`
3. **Prompt** includes signed + 2 fakes (~80 clauses × 3 versions in context)
4. **Parallel calls:** GPT/Claude × extract/playbook
5. **Claude playbook** returns: `{ verdict: pass, clause_id: c-017, quote: "...$10,000,000...", sot_label: "signed_contract" }` → grounded → matches answer key → **correct**
6. **GPT playbook** returns quote from outdated_wrong_terms (`$5,000,000`) → **ungrounded** vs canonical → **incorrect**
7. **Metrics:** grounding_rate=0.75, decoy_rate=0.25, task_accuracy=0.50

---

## FAQ (design decisions)

### Q: How is SoT determined to begin with?

**A:** The real SEC-filed MSA is parsed into canonical clauses. That parse is the sole truth. Decoys are algorithmically derived corruptions. The verifier and answer keys never consult decoys.

### Q: How do we prevent models from caching real vs fake?

**A:** Fresh seed and decoy sampling every eval run; multiple MSAs; discriminating tasks where decoy-faithful answers fail; unit tests use fixed seeds but live eval does not.

### Q: Should we hide decoy labels in prompts?

**A:** No for v1. Real deal rooms label documents ("Draft", "Executed"). The instruction is "cite signed_contract only" — the hardness comes from **conflicting text**, not hidden metadata. Optional v2: neutral labels (`version_a`, `version_b`) with one mapping logged in manifest only.

### Q: Does the orchestrator pick which candidate is truth?

**A:** No. Truth is fixed at bundle creation. Orchestrator only chooses **which candidates to show**, not which is valid.

### Q: What if all models fail under noise?

**A:** That is a valid experimental outcome — report decoy rate and compare `single` vs `parallel_grounded` and `clean` vs `noisy_prompt`. The spread is the story.

---

## Deliverables checklist

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | `orchestrator/models.py` | Claim, RunManifest, RunResult |
| 2 | `orchestrator/tasks.py` | Prompt templates for extract + playbook |
| 3 | `orchestrator/runner.py` | Async parallel task execution |
| 4 | `grounding/verifier.py` | Canonical-only claim verification |
| 5 | `models/base.py` | Pluggable LLM client |
| 6 | `benchmark/answers/*.yaml` | Answer keys per fixture MSA |
| 7 | `benchmark/metrics.py` | Decoy rate, task accuracy, grounding rate |
| 8 | `benchmark/conditions.py` | clean / noisy_prompt / noisy_task |
| 9 | `tests/` | Verifier, orchestrator (mock LLM), metrics |
| 10 | Update `context/STORE.md` | Implementation status |

---

## Success criteria

- [ ] Eval run with fresh seed produces different decoy text than previous run
- [ ] Claims grounded in decoy text are always rejected
- [ ] Task accuracy under `clean` ≈ high; under `noisy_prompt` lower with measurable decoy rate
- [ ] Same verifier and answer keys for all strategies — only scheduling differs
- [ ] `python -m pytest tests/ -q` passes

---

## Open questions (resolve during implementation)

1. **Gold authoring:** Script-assisted pass over canonical to draft YAML, then human spot-check?
2. **Decoys per prompt:** Start with 1 decoy + signed; increase to 2 if discrimination is weak.
3. **Prompt order:** Shuffle candidate blocks or always signed first?
4. **Extend `extra_clause` corruption** to seed-select among multiple templates (stronger fresh noise).
5. **Extend `altered_text`** to target random eligible clauses, not only liability.
