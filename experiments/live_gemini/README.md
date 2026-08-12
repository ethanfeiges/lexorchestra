# Live Gemini experiments

Results from `python -m benchmark.run_experiment --provider gemini`.

Default model: **`gemini-flash-latest`** (alias to current Flash; replaces retired `gemini-2.0-flash`).

Default matrix: **5 document types × 2 conditions = 10 runs**.

```powershell
python -m benchmark.run_experiment --provider gemini --model gemini-flash-latest
```

If the API quota is exhausted mid-run, the runner saves completed rows incrementally and sets `manifest.json` status to `partial`. Re-run when quota resets to fill remaining cells.
