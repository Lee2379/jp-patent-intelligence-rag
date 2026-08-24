# Embedding context audit

Observed on 2026-08-24 before accepting the first dense index as final.

## Baseline configuration

```text
Model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
Embedding dimensions: 384
Model maximum sequence length: 128 tokens
Patent chunk maximum: 900 Japanese characters
Sample: 1,000 deterministic chunks from data/processed/chunks_ai.jsonl.gz
```

## Observed tokenizer fit

| Character cap | Median tokens | p95 tokens | Above 128 tokens |
|---:|---:|---:|---:|
| 120 | 74 | 90 | 0.0% |
| 150 | 91 | 109 | 0.4% |
| 180 | 109 | 129 | 5.1% |
| 200 | 120 | 142 | 28.6% |
| 220 | 131 | — | 53.0% |
| current chunks (up to 900) | 458.5 | 580 | 79.1% |

## Decision

The 128-token MiniLM run is recorded as a baseline. It is not sufficient as the final dense
retrieval configuration because most long Japanese evidence chunks are truncated. The final
candidate is `intfloat/multilingual-e5-small`, which retains 384-dimensional vectors while
increasing the supported context to 512 tokens. The implementation must also use the E5-required
`query:` and `passage:` prefixes.

Final-model token coverage and retrieval metrics are appended only after a clean rebuild.

## Candidate tokenizer check

`intfloat/multilingual-e5-small` was tested on the same first 1,000 actual chunks with the
required `passage:` prefix and without tokenizer truncation:

| Character cap | Median tokens | p95 tokens | Above 512 tokens | Maximum |
|---:|---:|---:|---:|---:|
| 500 | 256.5 | 330 | 0.0% | 372 |
| 600 | 298.5 | 391 | 0.0% | 448 |
| 700 | 341.5 | 453 | 0.2% | 523 |
| 900 | 368.5 | 551.05 | 11.8% | 648 |

Selected default: 600 characters with an 80-character overlap.

## Final full-corpus acceptance result

Command:

```powershell
uv run patent-rag audit-embedding
```

Observed on all persisted final chunks:

```text
Chunks: 31,270
Median: 311 tokens
p95: 390 tokens
p99: 417 tokens
Maximum: 491 tokens
Above 512 tokens: 0 (0.0%)
Accepted: true
Chunks SHA-256: b8d6e54138e65eb81466717c053ceaa0e0de9c04ddf566a28cfc8db696e2da44
```

This full-corpus result, rather than the initial sample, is the final acceptance evidence.
