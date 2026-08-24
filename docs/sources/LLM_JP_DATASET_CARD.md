---
license: cc-by-4.0
language:
- ja
task_categories:
- text-generation
tags:
- pretraining
- japanese
- llm-jp
size_categories:
- n>1T
---

# llm-jp-corpus-v4 — `ja_patent`

Mirror of the `ja/ja_patent` sub-corpus of [LLM-jp Corpus v4](https://gitlab.llm-jp.nii.ac.jp/datasets/llm-jp-corpus-v4),
built by the LLM-jp Corpus Building WG (NII).

- **Source**: https://gitlab.llm-jp.nii.ac.jp/datasets/llm-jp-corpus-v4
- **Sub-corpus**: `ja_patent`
- **Files**: 621 × `jsonl.gz` (58.2 GB compressed)
- **Format**: one JSON object per line, with a `text` key and a `meta` key
  (document id, URL, and other provenance fields).

Directory layout mirrors the upstream repository.

## License

**CC BY 4.0** — inherited from the upstream sub-corpus. Attribution goes to
the [LLM-jp](https://llm-jp.nii.ac.jp/) Corpus Building WG and to the original data providers listed
in the [upstream README](https://gitlab.llm-jp.nii.ac.jp/datasets/llm-jp-corpus-v4/-/blob/main/README.md), which remains the
authoritative statement of terms for this data.
