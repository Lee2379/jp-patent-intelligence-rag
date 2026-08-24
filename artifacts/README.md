# Local generated artifacts

All runtime and screenshot-ready outputs stay inside this project directory.

| Directory | Contents | Git policy |
|---|---|---|
| `reports/` | Data quality, context audit, retrieval evaluation, E2E JSON | generated / ignored |
| `index/` | BM25 matrix, E5 vectors, chunk metadata, manifest and hashes | generated / ignored |
| `cache/` | Downloaded local ONNX embedding models | generated / ignored |
| `audit/` | Prompt, answer, evidence, and human-review SQLite event chain | private / ignored |
| `pilot/` | Disposable local smoke-test data | generated / ignored |

Durable evidence summaries are copied to `docs/evidence/`. Final user-captured PNG files belong in
`docs/screenshots/`; use `docs/PORTFOLIO_ARTIFACTS.md` as the checklist.
