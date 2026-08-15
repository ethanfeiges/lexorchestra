# Live Gemini experiments

Results from `python -m benchmark.run_experiment --provider gemini`.

Default model: **`gemini-flash-latest`** (alias to current Flash; replaces retired `gemini-2.0-flash`).

Default matrix: **5 document types × 2 conditions = 10 runs**.

```powershell
python -m benchmark.run_experiment --provider gemini --model gemini-flash-latest
```

If the API quota is exhausted mid-run, the runner saves completed rows incrementally and sets `manifest.json` status to `partial`. Re-run when quota resets to fill remaining cells.

**Verified local SoT-selection evidence (2026-08-14):** `python -m pytest tests/orchestrator -q` → `9 passed in 0.48s`. This covers the decoy-anchoring checks that verify the canonical contract is used instead of invalid SoT candidates when subagents run.

Live Gemini benchmark runs remain a separate, quota-dependent activity. The repo does not treat the earlier partial live run as evidence for SoT-selection correctness when the unit orchestration suite is the source of truth for that behavior.
