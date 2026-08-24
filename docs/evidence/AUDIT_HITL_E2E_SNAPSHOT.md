# Audit and human-review E2E evidence

Final Docker Compose run observed on 2026-08-24.

| Check | Observed value |
|---|---|
| Query | `機械学習を用いたレーザ加工技術の課題と解決手段を比較してください` |
| Top document | `JP2020151725` / abstract |
| Generation | `ollama_structured` / `qwen3:1.7b` |
| Citation allow-list | Passed (`S1`) |
| Review | `approved` by a separate reviewer label |
| Docker generation latency | 29,897 ms cold-container run |
| Docker total answer latency | 29,931 ms |
| Audit events after Docker E2E | 24 |
| Audit chain | Valid |
| App identity | non-root UID/GID 999 |
| Required service cost | `$0 local-only` |

The audit answer event retains the analyst label, exact user query, system prompt, complete
evidence-expanded model prompt, generation parameters, retrieved source texts and scores, raw
model JSON, rendered draft, timings, prompt version, model, and index manifest. The human decision
is a new linked event; the original answer event is not overwritten.

The chain is tamper-evident rather than externally immutable. Actor and reviewer IDs are local
operator labels, not authenticated identities. These boundaries are visible in the UI and are
documented in `docs/AUDIT_AND_HITL.md`.
