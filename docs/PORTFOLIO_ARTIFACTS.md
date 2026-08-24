# Portfolio artifact index

This is the single checklist for portfolio evidence. Generated reports stay under
`artifacts/reports/`; durable explanations and snapshots stay under `docs/`; the user's final
PNG captures go under `docs/screenshots/`.

| Stage | Local artifact | Screenshot filename | Status | What it proves |
|---|---|---|---|---|
| Data source | `docs/sources/LLM_JP_DATASET_CARD.md` | `01-dataset-source.png` | Ready | Japanese patent source and CC BY 4.0 attribution |
| Raw record | `docs/sample_record_ai_2020151725.txt` | `02-raw-patent-record.png` | Ready | Real abstract, claim, identity, and local provenance |
| Data quality | `artifacts/reports/data_quality.html` | `03-data-quality.png` | Ready / visually verified | 46,794 valid records and section coverage |
| Context gate | `artifacts/reports/embedding_context_audit.html` | `04a-embedding-context-audit.png` | Ready / visually verified | All 31,270 chunks fit E5's 512-token window |
| Retrieval evaluation | `artifacts/reports/retrieval_evaluation.html` | `04-retrieval-evaluation.png` | Ready / measured | BM25 vs dense vs hybrid Recall@K and MRR@10 |
| RAG answer | `http://127.0.0.1:8000` | `05-grounded-rag-answer.png` | Ready / browser verified | Local multilingual answer with verified citations |
| Human review | Review panel in the local UI | `05b-human-review-approved.png` | Ready / browser + E2E verified | Pending draft changed by an appended human decision |
| Source trace | Source dialog in the local UI | `06-source-traceability.png` | Ready / browser verified | Citation to exact Japanese passage and path |
| Runtime | Docker Compose + `/api/health` | `07-docker-health.png` | Ready / both containers healthy | Reproducible containers, local models, retrieval readiness |
| Audit trail | `http://127.0.0.1:8000/audit` | `08-audit-trail.png` | Ready / browser + chain verified | Actor, prompt/event, review, hashes, and valid event chain |

## Recording rule

Do not capture a pending artifact. When a stage is accepted, append its measured metrics and file
hash to `docs/BUILD_LOG.md`, update the status above, then take the screenshot using
`docs/SCREENSHOT_GUIDE.md`.

Never include `.env`, tokens, a full user-home path, or a failed terminal in a portfolio image.
