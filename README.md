# Japanese Patent Intelligence RAG

[![CI](https://github.com/Lee2379/jp-patent-intelligence-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/Lee2379/jp-patent-intelligence-rag/actions/workflows/ci.yml)
![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-local_API-009688?logo=fastapi&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-qwen3%3A1.7b-black)
![Cost](https://img.shields.io/badge/required_cost-%240-success)
![License](https://img.shields.io/badge/code-Apache--2.0-blue)

[日本語](README_ja.md) · **English**

A fully local, multilingual technical prior-art exploration assistant for Japanese AI patents.
It combines patent-aware parsing, Japanese lexical retrieval, multilingual embeddings,
grounded local generation, citation-level source inspection, human review, and a
tamper-evident audit trail.

> **Technical prior-art exploration assistant — not legal advice.** No cloud account, API key,
> paid API, or metered service is required.

## Data provenance and preparation

The development corpus is the `ja_patent` subset of **LLM-jp Corpus v4**, published by the
LLM-jp Corpus Building Working Group (NII) and mirrored on Hugging Face. The repository does
not redistribute the corpus; it contains manifests, validation evidence, and reproducible
processing code only.

![Japanese patent corpus on Hugging Face](docs/screenshots/01-dataset-source-huggingface.png)

*Figure 1. Japanese patent corpus used as the initial development dataset. The corpus contains
approximately 4.68 million documents and is distributed under CC BY 4.0.*

![Reproducible sampling manifest](docs/screenshots/02-sampling-manifest.png)

*Figure 2. Reproducible sampling manifest. A deterministic year-stratified sample of 46,794
documents was created from an estimated 4,679,385 source records; each curated shard records
its SHA-256 checksum.*

![Corpus integrity validation](docs/screenshots/03-corpus-validation.png)

*Figure 3. Corpus integrity validation. All 46,794 records passed gzip, UTF-8, and JSON
validation, with zero missing patent-text records.*

![Raw Japanese patent record](docs/screenshots/04-raw-japanese-patent-record.png)

*Figure 4. Raw Japanese patent record containing a machine-learning abstract, independent
claim, publication metadata, and traceable source path.*

| Data contract | Value |
|---|---:|
| Upstream estimate | 4,679,385 Japanese patent records |
| Reproducible sample | 46,794 records (1.000003%) |
| Coverage | 2004, 2007, 2011, 2014, 2017, 2020 |
| Publication kind | `A` — public patent applications |
| Valid / invalid / empty | 46,794 / 0 / 0 |
| Indexed AI-domain documents | 505 |

See [DATASET_README.md](DATASET_README.md), [DATASET_MANIFEST.json](DATASET_MANIFEST.json),
and the [local dataset card](docs/sources/LLM_JP_DATASET_CARD.md) for provenance and attribution.

## Development process and verification trail

This repository preserves the completed build sequence, not only the final interface. Every
stage has an explicit output, acceptance gate, and durable evidence file. Generated corpora,
indexes, model weights, and audit databases remain local; manifests, measurements, source code,
and reproducible commands are versioned here.

| Stage | Engineering work | Acceptance gate | Evidence |
|---|---|---|---|
| **0 · Architecture** | Defined a laptop-only trust boundary, `$0` required-service policy, Docker topology, and evaluation contract | No cloud account, paid API, or external model endpoint required | [Architecture](docs/ARCHITECTURE.md) · [Cost & privacy](docs/COST_AND_PRIVACY.md) |
| **1 · Acquisition & sampling** | Mirrored the LLM-jp Japanese patent shards and created a deterministic SHA-256-ranked, year-stratified 1% sample | **46,794** selected records; source shard counts and hashes recorded | [Dataset manifest](DATASET_MANIFEST.json) · [Dataset guide](DATASET_README.md) |
| **2 · Validation & parsing** | Validated gzip/UTF-8/JSON, normalized NFKC text, extracted publication IDs, and separated patent sections | **0** invalid JSON, **0** empty text; abstract coverage **99.99%**, claim coverage **99.98%** | [Pipeline snapshot](docs/evidence/DATA_PIPELINE_SNAPSHOT.md) · [`japanese_patent.py`](src/patent_rag/parsing/japanese_patent.py) |
| **3 · Chunking & indexing** | Built bounded section chunks, Sudachi BM25, and 384-dimensional multilingual E5-small embeddings | **31,270** chunks; all persisted chunks fit the 512-token model limit; artifact hashes matched | [Embedding audit](docs/evidence/EMBEDDING_CONTEXT_AUDIT.md) · [Index snapshot](docs/evidence/FINAL_INDEX_AND_EVALUATION.md) |
| **4 · Retrieval evaluation** | Compared sparse, dense, and RRF hybrid retrieval on Japanese and KO/EN regression sets | Japanese hybrid Recall@5 **1.000**; KO/EN hybrid Recall@5 **1.000** | [Evaluation protocol](docs/EVALUATION.md) · [Measured results](docs/evidence/FINAL_INDEX_AND_EVALUATION.md) |
| **5 · Grounded generation** | Added evidence gating, bounded Ollama prompts, structured output, citation allow-listing, fallback, and abstention | Every accepted answer cites retrieved `[S#]` IDs; unsupported citations cannot pass validation | [`ollama.py`](src/patent_rag/generation/ollama.py) · [Model card](docs/MODEL_CARD.md) |
| **6 · API, UI & governance** | Implemented typed FastAPI endpoints, source dialogs, independent review decisions, and canonical JSON hash-linked audit events | Drafts start `pending`; review appends rather than overwrites; chain verification returns valid | [Audit & HITL design](docs/AUDIT_AND_HITL.md) · [E2E evidence](docs/evidence/AUDIT_HITL_E2E_SNAPSHOT.md) |
| **7 · Runtime verification** | Ran the Docker workflow from retrieval through local generation, review, audit verification, and CI quality gates | Top result `JP2020151725`; non-root app; valid 24-event chain; Ruff, strict mypy, **30 tests** | [Docker evidence](docs/evidence/DOCKER_OLLAMA_SNAPSHOT.md) · [Build log](docs/BUILD_LOG.md) · [CI](https://github.com/Lee2379/jp-patent-intelligence-rag/actions) |

The full chronological record—including commands, measured timings, artifact hashes, failures,
and accepted replacements—is retained in the [build log](docs/BUILD_LOG.md). This makes the
portfolio auditable without committing the licensed corpus or machine-specific runtime state.

## Product overview

![Local Japanese Patent Intelligence RAG](docs/screenshots/white-ui-desktop.png)

*Local Japanese Patent Intelligence RAG — hybrid retrieval, multilingual answers, and fully
local inference.*

The interface is an analyst workspace rather than a generic chat demo. It exposes corpus scope,
filters, retrieval mode, model state, evidence policy, source passages, reviewer decisions, and
audit receipts in one workflow.

## What this project demonstrates

- **Japanese patent NLP:** Unicode normalization and section-aware extraction of abstracts,
  individual claims, technical fields, backgrounds, and detailed descriptions.
- **Hybrid information retrieval:** Sudachi-tokenized BM25 and multilingual E5-small dense
  retrieval, fused through Reciprocal Rank Fusion instead of mixing incompatible raw scores.
- **Multilingual search:** Japanese answers plus Korean/English query support, with transparent
  Korean-to-Japanese patent-term expansion on the lexical branch.
- **Grounded local generation:** Ollama `qwen3:1.7b`, bounded evidence prompts, allow-listed
  `[S#]` citations, evidence gating, and extractive fallback or abstention on failure.
- **Operational AI controls:** independent human approve/revise/reject decisions and append-only
  SHA-256-linked events for prompts, passages, outputs, timings, and reviews.
- **Engineering discipline:** typed FastAPI contracts, Docker Compose, deterministic tests,
  retrieval evaluation, Ruff, strict mypy, CI, runbooks, model card, and threat boundaries.

## End-to-end architecture

![End-to-end local RAG architecture](docs/screenshots/white-ui-pipeline.png)

*End-to-end local RAG architecture — Japanese patent ingestion, section-aware parsing, hybrid
retrieval, grounded generation, and governance.*

<img src="docs/architecture.svg" width="100%" alt="Japanese Patent Intelligence RAG system architecture">

<details>
<summary><strong>View the Mermaid implementation</strong></summary>

```mermaid
flowchart TB
    subgraph ROW1[" "]
        direction LR
        subgraph DATA["1 · DATA FOUNDATION"]
            direction TB
            A["Japanese patent<br/>JSONL"] --> B["Validation<br/>+ NFKC"]
            B --> C["Patent section<br/>parser"]
            C --> D["Section-aware<br/>chunks"]
        end

        subgraph SEARCH["2 · HYBRID RETRIEVAL"]
            direction TB
            E["BM25<br/>+ Sudachi"] --> G["Reciprocal Rank<br/>Fusion"]
            F["Multilingual<br/>E5-small"] --> G
            G --> H["Evidence<br/>gate"]
        end
    end

    subgraph ROW2[" "]
        direction LR
        subgraph GENERATE["3 · GROUNDED GENERATION"]
            direction TB
            I["Ollama<br/>Qwen3 1.7B"] --> J["Citation<br/>validator"]
            J --> K["FastAPI<br/>draft"]
        end

        subgraph GOVERN["4 · REVIEW & GOVERNANCE"]
            direction TB
            L["Analyst<br/>UI"] --> M["Human<br/>review"]
            M --> N["Append-only<br/>audit"]
            N --> O["SHA-256 chain<br/>verification"]
        end
    end

    D --> E
    D --> F
    H --> I
    K --> L
    K -. generated event .-> N

    classDef default fill:#ffffff,stroke:#6d5dfc,stroke-width:1.5px,color:#17152b,font-size:16px;
    style DATA fill:#f7f7ff,stroke:#c9c4ff,stroke-width:1px
    style SEARCH fill:#f7f7ff,stroke:#c9c4ff,stroke-width:1px
    style GENERATE fill:#f7f7ff,stroke:#c9c4ff,stroke-width:1px
    style GOVERN fill:#f7f7ff,stroke:#c9c4ff,stroke-width:1px
    style ROW1 fill:transparent,stroke:transparent
    style ROW2 fill:transparent,stroke:transparent
```

</details>

The local model receives only retrieved passages that pass the configured evidence threshold.
It has no browser, shell, tools, or write access. API text is escaped before UI rendering, and
Docker ports bind to `127.0.0.1`.

## Grounded answer and citation traceability

<details>
<summary><strong>View a Japanese answer with evidence scores and [S1]/[S2] citations</strong></summary>

![Japanese grounded answer](docs/screenshots/white-ui-result.png)

*Grounded generation — the analyst sees evidence status, model, latency, Japanese answer,
inline citations, and ranked source passages.*

</details>

Every answer citation is interactive and opens the exact patent section used to support the
claim.

<details>
<summary><strong>View citation-level source inspection</strong></summary>

![Citation-level source traceability](docs/screenshots/white-ui-source-traceability.png)

*Citation-level traceability — each generated claim opens the exact supporting passage from
the original Japanese patent, including publication number, year, section, and local source
path.*

</details>

## Human-in-the-loop review

![Human-in-the-loop review](docs/screenshots/white-ui-hitl.png)

*Human-in-the-loop review gate — every generated answer requires an independently recorded
approval, revision, or rejection decision.*

Answers begin in `pending`. The reviewer label must differ from the analyst label, and a new
decision event is recorded without overwriting the generated draft. These labels are workflow
identifiers for this local portfolio build, not authenticated identities.

## Tamper-evident audit trail

![Tamper-evident audit trail](docs/screenshots/white-ui-audit.png)

*Tamper-evident audit trail — prompts, retrieval evidence, model outputs, and human decisions
are linked through an append-only SHA-256 chain.*

Each canonical JSON event stores the preceding event hash. Verification recomputes the chain
and reports the checked event count, current head hash, and validity. This makes silent edits
detectable; production deployment would additionally require authenticated users, access
control, remote immutable storage, retention policy, and external timestamps.

## Evaluation

| Check | Result | Interpretation |
|---|---:|---|
| Japanese silver benchmark, 30 queries | Recall@5 **1.000**, MRR@10 **1.000** | Deterministic retrieval regression test |
| Korean/English smoke set, 6 queries | Recall@5 **1.000**, MRR@10 **0.700** | Cross-lingual path smoke check |
| Citation invariants | Enforced | Only retrieved source IDs may be cited |
| Quality gates | Ruff, strict mypy, **30 tests** | Local and CI verification |
| Docker E2E | Retrieval → Ollama → review → valid audit chain | Full workflow check |

These results are engineering regression checks, not a statistically powered relevance study
or expert patentability opinion. The Japanese benchmark is abstract-derived, and the multilingual
set is intentionally small. See [Evaluation](docs/EVALUATION.md) and the
[Model Card](docs/MODEL_CARD.md) for methodology and limitations.

## Quick start

Prerequisites: Docker Desktop and Python 3.11. An NVIDIA GPU is optional; CPU inference works.
Source data and generated indexes are intentionally excluded from Git.

```powershell
git clone https://github.com/Lee2379/jp-patent-intelligence-rag.git
cd jp-patent-intelligence-rag
Copy-Item .env.example .env
uv sync --dev

docker compose up -d ollama
docker compose --profile setup run --rm model-init
docker compose --profile setup run --rm embedding-init

uv run patent-rag prepare
uv run patent-rag report
uv run patent-rag build-index
uv run patent-rag evaluate
docker compose --profile app up -d --build
```

Open `http://127.0.0.1:8000`; the audit console is at
`http://127.0.0.1:8000/audit`. The corpus must first be placed under the paths documented in
[DATASET_README.md](DATASET_README.md). For native execution, CPU Compose overrides, health
checks, and troubleshooting, use the [Runbook](docs/RUNBOOK.md).

## Repository map

```text
apps/web/                 responsive analyst and audit interfaces
src/patent_rag/parsing/   Japanese patent section parser
src/patent_rag/pipeline/  validation, normalization, chunking, reports
src/patent_rag/retrieval/ BM25, dense retrieval, RRF, evaluation
src/patent_rag/generation/ Ollama prompting and citation guard
src/patent_rag/api/       FastAPI application and typed contracts
src/patent_rag/audit.py   append-only SQLite events and hash-chain verification
tests/                    deterministic unit and API tests
docs/                     architecture, evidence, evaluation, runbook, model card
```

## Design decisions and limitations

- In-memory dense search is appropriate for this 505-document AI subset; full-corpus scaling
  should use a disk-backed ANN index and incremental ingestion.
- The corpus does not include complete live legal status, applicant, CPC/FI, or citation-network
  metadata. Those fields require an authorized, current JPO source.
- A valid hash chain detects local mutation but does not provide identity, authorization, or
  external timestamp guarantees.
- Generated text is always a reviewable technical-search draft. It must not be used as a
  patentability, infringement, validity, FTO, ownership, or legal-status determination.

Read the detailed [Architecture](docs/ARCHITECTURE.md),
[Audit and HITL design](docs/AUDIT_AND_HITL.md),
[Cost and privacy notes](docs/COST_AND_PRIVACY.md), and [Security policy](SECURITY.md).

## License and attribution

Application code is licensed under [Apache-2.0](LICENSE). The Japanese patent corpus is
distributed separately under **CC BY 4.0**; attribution belongs to the LLM-jp Corpus Building
Working Group (NII) and the original data providers identified by the upstream corpus.
Model and third-party dependency licenses remain their own.
