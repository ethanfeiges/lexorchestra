# Live Gemini baseline

Committed output of:

```powershell
python -m benchmark.run_live_experiment --provider gemini --model gemini-2.5-flash
```

**4 runs:** Edgemode + NuScale × `clean` + `noisy_prompt`, strategy `single`, seeds `11001`–`11004`.

| Condition | Grounding | Decoy rate | Task accuracy |
|-----------|-----------|------------|---------------|
| clean | 83% | 0% | 67% |
| noisy_prompt | 67% | 17% | 50% |

Re-run (requires `GEMINI_API_KEY` in `.env`):

```powershell
pip install -e ".[llm]"
python -m benchmark.run_live_experiment --provider gemini
```

Full test write-up: [`experimentDocs/EXPERIMENTS.md`](../../experimentDocs/EXPERIMENTS.md).
