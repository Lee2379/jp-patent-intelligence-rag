# Portfolio artifact index

This is the single checklist for portfolio evidence. Generated reports stay under
`artifacts/reports/`; durable explanations and snapshots stay under `docs/`; the user's final
PNG captures go under `docs/screenshots/`.

| Stage | Local artifact | Screenshot filename | Status | What it proves |
|---|---|---|---|---|
| Data source | `docs/sources/LLM_JP_DATASET_CARD.md` | `01-dataset-source-huggingface.png` | Ready | Japanese patent source and CC BY 4.0 attribution |
| Raw record | `docs/sample_record_ai_2020151725.txt` | `04-raw-japanese-patent-record.png` | Ready | Real abstract, claim, identity, and local provenance |
| Data quality | `docs/evidence/DATA_PIPELINE_SNAPSHOT.md` | `03-corpus-validation.png` | Ready / measured | 46,794 valid records and section coverage |
| Sampling | `DATASET_MANIFEST.json` | `02-sampling-manifest.png` | Ready / hashed | Deterministic year-stratified sample and SHA-256 checksums |
| Context gate | `docs/evidence/EMBEDDING_CONTEXT_AUDIT.md` | Not used in README | Ready / measured | All 31,270 chunks fit E5's 512-token window |
| Retrieval evaluation | `docs/evidence/FINAL_INDEX_AND_EVALUATION.md` | Not used in README | Ready / measured | BM25 vs dense vs hybrid Recall@K and MRR@10 |
| RAG answer | `http://127.0.0.1:8000` | `white-ui-result.png` | Ready / browser verified | Local multilingual answer with verified citations |
| Human review | Review panel in the local UI | `white-ui-hitl.png` | Ready / browser + E2E verified | Pending draft changed by an appended human decision |
| Source trace | Source dialog in the local UI | `white-ui-source-traceability.png` | Ready / browser verified | Citation to exact Japanese passage and path |
| Runtime | Docker Compose + `/api/health` | `white-ui-desktop.png` | Ready / both containers healthy | Local model, retrieval readiness, and zero-cost runtime |
| Audit trail | `http://127.0.0.1:8000/audit` | `white-ui-audit.png` | Ready / browser + chain verified | Actor, prompt/event, review, hashes, and valid event chain |

## Recording rule

Do not capture a pending artifact. When a stage is accepted, append its measured metrics and file
hash to `docs/BUILD_LOG.md`, update the status above, then take the screenshot using
`docs/SCREENSHOT_GUIDE.md`.

Never include `.env`, tokens, a full user-home path, or a failed terminal in a portfolio image.
