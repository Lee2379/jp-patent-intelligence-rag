# Build log and screenshot checkpoints

This log records reproducible commands, observed outputs, and the exact screenshot to capture.
Generated files stay local; concise evidence snapshots under `docs/evidence/` are committed.

## 2026-08-24 — Stage 0: zero-cost architecture

Decision:

- Required runtime is local-only and free.
- No AWS, hosted vector database, paid LLM API, account, API key, or telemetry.
- Docker Ollama for generation; NumPy/SciPy files for the local indexes.
- `OLLAMA_NO_CLOUD=true` explicitly disables Ollama cloud inference.

Recorded configuration: `.env.example`, `compose.yaml`, `docs/COST_AND_PRIVACY.md`.

Screenshot status: **documentation only**; no screenshot needed for this stage.

## 2026-08-24 — Stage 1: source record and patent parsing

Command:

```powershell
uv run patent-rag prepare
```

Observed result:

- Input records: 46,794
- Written records: 46,794
- Invalid JSON: 0
- Empty text: 0
- Years: 2004, 2007, 2011, 2014, 2017, 2020
- AI/search-domain selected patents: 505
- Section-aware evidence chunks: 31,270
- Abstract extracted: 46,789
- Claims extracted: 46,785

Evidence: `data/processed/data_quality.json` locally and
`docs/evidence/DATA_PIPELINE_SNAPSHOT.md` in Git.

Screenshot checkpoint A — raw source:

- Open `docs/sample_record_ai_2020151725.txt` in VS Code.
- Capture source year, publication kind, document ID, abstract, and first claim.
- Recommended filename: `docs/screenshots/02-raw-patent-record.png`.

Screenshot checkpoint B — pipeline report:

```powershell
uv run patent-rag report
Start-Process .\artifacts\reports\data_quality.html
```

- Capture the four KPI cards, year distribution, and section coverage.
- Recommended filename: `docs/screenshots/03-data-quality.png`.

## 2026-08-24 — Stage 2: Docker Ollama

Commands:

```powershell
docker compose up -d ollama
docker compose --profile setup run --rm model-init
docker compose --profile setup run --rm embedding-init
docker exec jp-patent-ollama ollama list
```

Observed result:

- Ollama container version: 0.32.15
- Production model: `qwen3:1.7b`
- Model size: approximately 1.4 GB
- Reported parameters: 2.0B
- Quantization: Q4_K_M
- Dedicated endpoint: `127.0.0.1:11435`
- Model persisted in the Compose `ollama-data` named volume
- Local-only control confirmed in log: `Ollama cloud disabled: true`
- Host GPU: RTX 3060 Laptop 6 GB
- Current execution: CPU fallback because driver 546.30 is below Ollama's reported 550 minimum

Evidence: `docs/evidence/DOCKER_OLLAMA_SNAPSHOT.md`.

Screenshot checkpoint C — capture after the API container also runs:

```powershell
docker compose ps
docker exec jp-patent-ollama ollama list
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

- Do not use the driver warning as a representative portfolio screenshot.
- Recommended filename: `docs/screenshots/07-docker-health.png`.

## 2026-08-24 — Stage 3: hybrid index

Command started:

```powershell
uv run patent-rag build-index
```

Baseline scope: the earlier 23,335 evidence chunks, Sudachi BM25, and 384-dimensional
multilingual MiniLM.

Status: **stopped by the quality gate after approximately 60 minutes**. BM25 completed, but the
dense phase was intentionally not accepted or published after the tokenizer audit showed that
79.1% of the sampled production chunks exceeded the model's 128-token input limit. No retrieval
metric from this incomplete baseline is reported as a project result.

Quality gate discovered during the baseline build:

- The baseline MiniLM model accepts at most 128 tokens.
- A deterministic tokenizer audit on the actual patent chunks found that roughly 79% of a
  1,000-chunk sample exceeded that limit at the current 900-character chunk size.
- Therefore this run is retained as a measured baseline, not silently presented as the final
  dense-retrieval design.
- The final candidate is `intfloat/multilingual-e5-small`: 384 dimensions, 512-token context,
  explicit `query:`/`passage:` prefixes, and an MIT-licensed local ONNX runtime.

Portfolio note: this quality gate is a useful design-decision story, but it is a documentation
artifact rather than a separate screenshot. The final evaluation comparison is the screenshot.

Final preprocessing and embedding-context acceptance:

```powershell
uv run patent-rag prepare
uv run patent-rag report
uv run patent-rag audit-embedding
```

- Final section-aware chunks: 31,270
- Character cap: 600; overlap: 80
- E5 tokens: median 311, p95 390, p99 417, maximum 491
- Chunks above the 512-token model limit: 0
- Accepted: `true`
- Input SHA-256: `b8d6e54138e65eb81466717c053ceaa0e0de9c04ddf566a28cfc8db696e2da44`

Screenshot-ready local reports:

- `artifacts/reports/data_quality.html` — visually verified; shows 46,794 documents,
  505 AI documents, 31,270 evidence chunks, year distribution, and section coverage.
- `artifacts/reports/embedding_context_audit.html` — visually verified; shows context limit 512,
  maximum 491, over-limit 0, and `PASS`.
- Optional screenshot filename: `docs/screenshots/04a-embedding-context-audit.png`.

### Stage 3B — accepted E5 index

Command started after the full-corpus context gate passed:

```powershell
uv run patent-rag build-index --batch-size 64 --embedding-threads 8
```

Scope: all 31,270 accepted evidence chunks, Sudachi BM25, and 384-dimensional multilingual
E5-small with required asymmetric prefixes. Status: **complete and hash-verified**.

- Total build: 4,436.734 seconds
- BM25 phase: 44.207 seconds
- Dense phase: 4,390.739 seconds
- Documents / chunks: 505 / 31,270
- Dense array: 48,030,848 bytes
- Chunk metadata: 47,870,266 bytes
- `bm25_matrix.npz`: `33b379a392206206330378f124d5d97441bf0599f8965794d5b6868536e3add8`
- `bm25_vectorizer.joblib`: `2e24aad2c68f6ce465d569def229237de9b7868572c21765ef1fa486859e76a0`
- `dense_embeddings.npy`: `7a44f8912dac9f12bb48f4a05bc5a109d09647deff5fc67b14f93df174b81dd1`
- `chunks.jsonl`: `2171eddb4fe53737e9a83a261d35dd53419ed2d0071caf59142ea360c9fd1dcb`

All four hashes were independently recalculated and matched the manifest.

Planned screenshot checkpoint D:

- Run a CLI search that shows document ID, year, section, BM25 score, dense score, and RRF score.
- Use the laser-processing machine-learning query.
- Save as an optional engineering-detail screenshot.

## 2026-08-24 — Stage 4: audit trail and human review controls

Implemented while the final index was computing:

- Local append-only SQLite event store at `artifacts/audit/audit.sqlite3`
- `search_performed`, `answer_generated`, and `review_decision` events
- Exact prompt, actor label, session, filters, evidence text/scores, answer, citations, model, and
  timings retained locally
- SHA-256 chain over canonical event JSON with full-chain verification endpoint
- Answer state begins as `pending`; separate `approved`, `needs_revision`, or `rejected` events
- No API route for deleting audit records
- SQLite triggers reject `UPDATE` and `DELETE` on audit events
- Exact system prompt, evidence-expanded prompt, and generation parameters retained per answer
- Reviewer and answer-author labels must differ (label-level four-eyes check)
- A failed chain degrades health and fails search/generation/review closed with HTTP 503
- Dedicated local audit console at `http://127.0.0.1:8000/audit`
- Identity boundary disclosed: operator labels are not authenticated user identities

Automated checks at the final checkpoint: ruff passed, strict mypy passed, and 30 tests passed,
including mutation rejection, payload-tampering detection, fail-closed API behavior, and
API-level human approval.

Screenshot checkpoints:

- `docs/screenshots/05b-human-review-approved.png`
- `docs/screenshots/08-audit-trail.png`

Final visual checkpoint completed against the production audit database: the audit console
rendered a valid 21-event chain at browser-verification time with `ANSWER_GENERATED` and
`REVIEW_DECISION`, separate actor/reviewer labels, local timestamps, prompt summaries, and hashes.

## 2026-08-24 — Stage 5: retrieval evaluation

Japanese abstract-derived silver benchmark, 30 queries:

| Method | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|---|---:|---:|---:|---:|
| BM25 | 100.0% | 100.0% | 100.0% | 1.000 |
| Dense | 93.3% | 96.7% | 100.0% | 0.956 |
| Hybrid | 100.0% | 100.0% | 100.0% | 1.000 |

Six-query manually curated Korean/English smoke check:

| Method | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|---|---:|---:|---:|---:|
| BM25 + Korean term expansion | 50.0% | 66.7% | 66.7% | 0.542 |
| Dense | 66.7% | 83.3% | 83.3% | 0.722 |
| Hybrid | 50.0% | 100.0% | 100.0% | 0.700 |

The small multilingual set is a regression smoke check, not a statistically powered claim.
The Korean laser-processing target improved from hybrid rank 20 to rank 1 after transparent
Korean-to-Japanese patent-term expansion.

## 2026-08-24 — Stage 6: grounded generation, review, and audit

- Evidence gate calibrated at dense score 0.81 with 36 relevant and 10 out-of-domain challenge
  questions, plus an exact-publication-ID path
- Out-of-domain Korean travel question correctly abstained at dense score 0.762 with no technical cue
- Production generator: `qwen3:1.7b`, local CPU, JSON-schema problem/solution output
- Conclusion, source citations, and evidence-scope limitation rendered deterministically by the API
- Final Docker E2E: top document `JP2020151725`, `ollama_structured`, citation `S1`
- Cold-container E2E: generation 29,897 ms; total 29,931 ms
- Warmed native E2E: generation 8,237 ms; total 8,264 ms
- Separate human approval event recorded and complete audit chain verified
- Full system/model prompt, raw model JSON, evidence, output, and review retained locally

## 2026-08-24 — Stage 7: final runtime verification

- Ruff: passed
- Strict mypy: passed
- Pytest: 30 passed
- JavaScript syntax: passed for `app.js` and `audit.js`
- Docker Compose configuration: passed
- `ollama` container: healthy
- FastAPI app container: healthy and running as non-root UID/GID 999
- Final Docker audit chain after E2E: 24 events, valid
- Browser: free-form input, citations, source dialog, review controls, and audit console verified

GitHub Actions is configured but cannot be claimed as passed until this repository is pushed and
the remote workflow runs.

See `docs/SCREENSHOT_GUIDE.md` for framing and captions. Every numeric claim in the final README
must come from a recorded JSON manifest or this build log.
