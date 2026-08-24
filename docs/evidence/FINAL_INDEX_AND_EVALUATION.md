# Final hybrid index and retrieval evidence

Observed on 2026-08-24 from `artifacts/index/index_manifest.json` and
`artifacts/reports/retrieval_evaluation.json`.

## Accepted index

| Measure | Value |
|---|---:|
| Documents | 505 |
| Section-aware chunks | 31,270 |
| Embedding dimensions | 384 |
| Embedding model | `intfloat/multilingual-e5-small` |
| Total build time | 4,436.734 s |
| BM25 phase | 44.207 s |
| Dense phase | 4,390.739 s |

The final source chunk SHA-256 is
`b8d6e54138e65eb81466717c053ceaa0e0de9c04ddf566a28cfc8db696e2da44`.
All four generated artifact hashes were independently recalculated and matched the manifest.

## Retrieval results

| Benchmark / method | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|---|---:|---:|---:|---:|
| Japanese silver / BM25 | 100.0% | 100.0% | 100.0% | 1.000 |
| Japanese silver / Dense | 93.3% | 96.7% | 100.0% | 0.956 |
| Japanese silver / Hybrid | 100.0% | 100.0% | 100.0% | 1.000 |
| KO/EN smoke / BM25 + expansion | 50.0% | 66.7% | 66.7% | 0.542 |
| KO/EN smoke / Dense | 66.7% | 83.3% | 83.3% | 0.722 |
| KO/EN smoke / Hybrid | 50.0% | 100.0% | 100.0% | 0.700 |

The Japanese benchmark has 30 abstract-derived silver queries. The Korean/English benchmark has
six manually curated regression queries over three inspected patents; it is a multilingual smoke
check, not a statistically powered legal-relevance benchmark.

Screenshot-ready report: `artifacts/reports/retrieval_evaluation.html`.
