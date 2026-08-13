# Stub matrix experiments

Full 32-run matrix using **canonical stub clients** (no Gemini API). Validates parse → bundle → orchestrate → verify → score for every strategy.

```powershell
python scripts/run_stub_matrix.py
```

Outputs: `results.json`, `REPORT.md`, `manifest.json`.

For live Gemini runs see [`../live_gemini/`](../live_gemini/).
