# Japanese Patent RAG — downloaded dataset

## Use this dataset

The curated corpus for the next preprocessing step is:

```text
data/curated/stratified_1pct/
├── 2004.jsonl.gz   9,803 documents
├── 2007.jsonl.gz   9,803 documents
├── 2011.jsonl.gz   8,656 documents
├── 2014.jsonl.gz   9,803 documents
├── 2017.jsonl.gz   4,312 documents
└── 2020.jsonl.gz   4,417 documents
```

Total: **46,794 Japanese patent documents**, which is 1.000003% of the
upstream corpus estimate of 4,679,385 documents.

All selected documents are Japanese publication-of-patent-application (`A`)
records. The smaller 2017 and 2020 source shards were retained completely;
the larger source shards were sampled deterministically by SHA-256 of each
record's `meta.local_path`. This avoids selecting only consecutive publication
numbers and makes the sample reproducible.

## Source and license

- Dataset: `Podtech/llm-jp-corpus-v4-ja_patent`
- Upstream: LLM-jp Corpus v4, `ja/ja_patent`, built by the LLM-jp Corpus
  Building Working Group at NII
- Mirror: <https://huggingface.co/datasets/Podtech/llm-jp-corpus-v4-ja_patent>
- License: CC BY 4.0, subject to the upstream attribution and source notes
- Local copy of the dataset card: `docs/sources/LLM_JP_DATASET_CARD.md`

When publishing results, attribute both the LLM-jp Corpus Building Working
Group and the original providers identified by the upstream corpus. Do not
commit these compressed data files to the portfolio Git repository.

## Record format

Each gzip file contains UTF-8 JSON Lines. Each record has this shape:

```json
{
  "text": "Japanese patent text...",
  "meta": {
    "local_path": "dataset/2020/A/.../2020151139.xml.html.txt",
    "dedup_meta": {
      "minhash_cluster_id": -1,
      "minhash_cluster_size": 1
    }
  }
}
```

The publication year, publication kind and source document number can be
derived from `meta.local_path`. Rich metadata such as applicant, CPC/FI,
publication date and citation links is not included in this corpus and must be
added later from an authorized JPO source.

## Integrity check

- Valid JSON records: 46,794
- Invalid JSON records: 0
- Empty text records: 0
- Publication kind: `A` for all 46,794 records
- Simple AI-keyword candidates: 640 records

The AI-keyword count is only a preliminary diagnostic. The next step should
extract publication identifiers, parse patent sections, and build a broader
AI/NLP candidate filter before embeddings are generated.

## Other downloaded files

- `data/raw/llm_jp_ja_patent_strata/`: the six source shards used to produce
  the curated corpus.
- `data/raw/llm_jp_ja_patent/`: validation probes downloaded while locating
  representative years and publication kinds. Do not use this directory as
  the RAG ingestion input.
- `DATASET_MANIFEST.json`: counts, source shards, sampling quotas and SHA-256
  checksums for the curated files.
