# Contract fixtures

Real contract inputs from public SEC EDGAR EX-10 filings across **five document types**. There are no synthetic contract fixtures.

## Document types

| Type | Primary fixture | Description |
|------|-----------------|-------------|
| MSA | `edgar_edgemode_inc_ex10.1` | EdgeMode ↔ Cudo Ventures MSA |
| Software license | `edgar_amd_ex10.79` | AMD ↔ Broadcom core license |
| NDA | `edgar_hg_holdings_inc_ex10.2` | HG Holdings confidentiality agreement |
| Employment | `edgar_emerald_holding_inc_ex10.43` | Emerald executive employment agreement |
| Credit | `edgar_enviri_corp_ex10.1` | Enviri credit agreement amendment |

Additional MSAs (NuScale, Aspira, Pulmatrix, Chime) are tagged `document_type: msa` with `primary_fixture: false`.

## Location

```
legalDocs/contracts/
├── manifest.json          # source URLs, document_type, primary_fixture
└── public/                # real contract plain-text files
```

## SoT bundles and noise

Canonical clauses and decoy candidates are generated **from these real filings only** via `build_bundle_from_file()`. Corruption targets vary by `document_type` (liability clauses for MSAs, license grants for software licenses, etc.).

```python
from pathlib import Path
from docProcessing.io import build_bundle_from_file

bundle = build_bundle_from_file(
    Path("legalDocs/contracts/public/edgar_edgemode_inc_ex10.1.txt"),
    seed=42,
)
```

## Fetch more contracts

```powershell
python -m benchmark.fetch_contracts --limit 3 --user-agent "YourName you@email.com"
```

See [`context/phases/MULTI_TYPE.md`](../context/phases/MULTI_TYPE.md) for the multi-type design.
