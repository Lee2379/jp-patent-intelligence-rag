# Data pipeline evidence snapshot

Generated from `data/processed/data_quality.json` on 2026-08-24.

| Measure | Observed value |
|---|---:|
| Source records seen | 46,794 |
| Normalized documents written | 46,794 |
| Invalid JSON records | 0 |
| Empty-text records | 0 |
| AI/search-domain documents | 505 |
| Section-aware chunks | 31,270 |
| Abstract coverage | 46,789 / 46,794 (99.99%) |
| Claim coverage | 46,785 / 46,794 (99.98%) |
| Technical-field coverage | 46,143 / 46,794 (98.61%) |
| Background coverage | 46,155 / 46,794 (98.63%) |

## Year distribution

| Year | Documents |
|---:|---:|
| 2004 | 9,803 |
| 2007 | 9,803 |
| 2011 | 8,656 |
| 2014 | 9,803 |
| 2017 | 4,312 |
| 2020 | 4,417 |

## Reproduction

```powershell
uv run patent-rag prepare
uv run patent-rag report
```

Local artifacts:

- `data/processed/patents.jsonl.gz` — 385,226,339 bytes at snapshot time
- `data/processed/chunks_ai.jsonl.gz` — 6,999,816 bytes at snapshot time
- `artifacts/reports/data_quality.html` — portfolio-ready report

The raw and processed datasets are intentionally ignored by Git. Their acquisition hashes and
sampling method remain in `DATASET_MANIFEST.json`.
