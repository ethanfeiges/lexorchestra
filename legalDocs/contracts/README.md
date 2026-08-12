# Contract fixtures

All contract inputs are **real Master Services Agreements** from public SEC EDGAR EX-10 filings. There are no synthetic contract fixtures.

## Location

```
fixtures/contracts/
├── manifest.json          # source URLs, companies, filing metadata
└── public/                # real MSA plain-text files
    ├── edgar_edgemode_inc_ex10.1.txt
    ├── edgar_nuscale_power_corp_ex10.15.txt
    └── edgar_chime_financial_inc_ex10.1.txt
```

| File | Company | Description |
|------|---------|-------------|
| `public/edgar_edgemode_inc_ex10.1.txt` | Edgemode, Inc. | Master Services Agreement with Cudo Ventures |
| `public/edgar_nuscale_power_corp_ex10.15.txt` | NuScale Power Corp | Amended MSA with Fluor |
| `public/edgar_chime_financial_inc_ex10.1.txt` | Chime Financial, Inc. | Master Services Agreement with Bancorp Bank |

## SoT bundles and noise

Canonical clauses and all decoy candidates (`draft_missing_section`, `outdated_wrong_terms`, etc.) are generated **from these real MSAs only** via `build_bundle_from_file()`.

```python
from pathlib import Path
from docProcessing.io import build_bundle_from_file

bundle = build_bundle_from_file(
    Path("fixtures/contracts/public/edgar_edgemode_inc_ex10.1.txt"),
    seed=42,
)
```

## Fetch more MSAs

```powershell
python -m benchmark.fetch_contracts --limit 3 --user-agent "YourName you@email.com"
```

Updates `public/` and `manifest.json`.
