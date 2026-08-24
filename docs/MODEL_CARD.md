# System model card

## Intended use

Technical exploration and comparison of Japanese AI-related public patent applications for a
portfolio demonstration. Questions may be written in Japanese, Korean, or English.

## Not intended for

- Patentability, infringement, freedom-to-operate, validity, or legal-status opinions
- Exhaustive prior-art search
- Applicant, inventor, family, citation, or status analysis not present in the source records
- Automated legal decisions

## Components

- Retrieval embedding: `intfloat/multilingual-e5-small`, 384 dimensions, 512-token context
- Embedding input contract: `query:` for questions and `passage:` for indexed patent text
- Generator: `qwen3:1.7b` (reported 2.0B parameters), Q4_K_M, served locally by Ollama
- Sparse retrieval: BM25 over Sudachi mode-C normalized tokens
- Fusion: reciprocal rank fusion with rank constant 60

## Known limitations

- The curated corpus is a year-stratified 1% sample, not all Japanese patent publications.
- Only public application kind `A` is included in the portfolio corpus.
- AI-domain selection is deterministic keyword scoring and may include false positives or miss
  unusual terminology.
- Dense embeddings can blur legally important wording differences.
- The 600-character chunk cap is conservative for the measured Japanese corpus, but unusual
  symbol-heavy passages may still tokenize differently and are covered by the context audit.
- Small local language models can summarize incorrectly; citations reduce but do not eliminate risk.
- Source records do not provide a live legal-status database.
- Local actor/reviewer labels are self-declared and do not establish authenticated identity.
- The hash chain detects changes inside the retained database but is not an externally anchored,
  immutable compliance ledger.

## Mitigations

Source text is always visible. The generator must return problem and solution fields under a
JSON schema with allow-listed source IDs; the API deterministically renders the conclusion,
citations, and evidence-scope statement. Invalid output falls back to extracts, every draft
requires human review, and the UI shows a legal-use disclaimer.
