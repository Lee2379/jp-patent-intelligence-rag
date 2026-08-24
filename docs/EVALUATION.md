# Evaluation protocol

## Retrieval benchmark

`patent-rag evaluate` builds a deterministic silver benchmark from AI-patent abstracts. For
each selected document, the text under `【課題】` becomes a search question and that patent's
publication ID is the document-level target.

Reported metrics:

- Recall@1, Recall@5, Recall@10
- Mean Reciprocal Rank at 10 (MRR@10)
- Separate BM25, dense, and hybrid results

For Korean input, the reported BM25 and hybrid paths include the versioned deterministic
Korean-to-Japanese patent-term expansion used in production. Dense retrieval always embeds the
original query unchanged, so the comparison remains interpretable.

This benchmark catches broken tokenization, row misalignment, embedding failures, and harmful
fusion changes. It is not a substitute for an expert's legal relevance judgment because the
queries originate in the target abstracts and equivalent documents are not exhaustively labeled.

## Multilingual regression check

`config/multilingual_evaluation_queries.json` contains six manually written Korean and English
queries over three source documents whose technical content was inspected. The same BM25, dense,
and hybrid metrics are reported separately. This small set checks whether multilingual dense
retrieval provides the intended bridge when Japanese keyword overlap is weak; it is not presented
as a statistically powered benchmark.

## Generation checks

The application enforces these invariants:

1. Every accepted generative answer contains one or more `[S#]` citations.
2. Every cited ID belongs to the supplied evidence list.
3. A failed citation check produces an extractive evidence response.
4. No evidence produces an explicit abstention.

Before generation, a conservative evidence gate requires either an exact retrieved publication-ID
match or both a supported technical-domain cue and a top dense similarity of at least `0.81`.
That threshold was selected from this portfolio corpus using 36 relevant regression queries and
10 deliberately out-of-domain challenge queries. It is a transparent heuristic, not a calibrated
probability; the human-review requirement remains in force.

## Manual review set

Before publishing screenshots, run at least these three questions:

1. `機械学習を用いたレーザ加工技術の課題と解決手段を比較してください`
2. `ニューラルネットワークを利用する画像認識発明にはどのような特徴がありますか`
3. `予知保全における特徴量と学習モデルの利用方法を整理してください`

Review citation correctness, source-section labels, technical overclaiming, and latency. Do not
claim patentability, freedom to operate, ownership, or live legal status from this corpus.
