# Mock baseline (CI)

Committed output of `python -m benchmark.run_experiment` — **24 runs**.

## Matrix

3 documents × 2 conditions × 2 strategies × 2 mock profiles, seeds `11001`–`11024`.

| Axis | Values |
|------|--------|
| Documents | Edgemode, NuScale, Chime |
| Conditions | `clean`, `noisy_prompt` |
| Strategies | `single`, `parallel_grounded` |
| Profiles | `canonical`, `decoy_anchored` |

## CI

GitHub Actions regenerates this directory and fails if `git diff` is non-empty. Locally:

```powershell
python scripts/check_baseline.py
```

Full catalog: [`experimentDocs/MOCK_EXPERIMENTS.md`](../../experimentDocs/MOCK_EXPERIMENTS.md). Live Gemini: [`experimentDocs/EXPERIMENTS.md`](../../experimentDocs/EXPERIMENTS.md).
