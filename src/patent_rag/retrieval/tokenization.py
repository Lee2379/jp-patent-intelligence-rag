from __future__ import annotations

import re
from functools import lru_cache

from sudachipy import Dictionary, SplitMode, Tokenizer


@lru_cache(maxsize=1)
def _tokenizer() -> Tokenizer:
    return Dictionary(dict="core").create()


def sudachi_tokenize(text: str) -> list[str]:
    """Japanese lexical tokens for BM25, with punctuation and one-char noise removed."""
    normalized = text.lower().strip()
    tokens: list[str] = []
    for morpheme in _tokenizer().tokenize(normalized, SplitMode.C):
        pos = morpheme.part_of_speech()[0]
        surface = morpheme.normalized_form()
        if pos in {"空白", "補助記号", "助詞", "助動詞"}:
            continue
        if not re.search(r"[0-9a-z一-龯ぁ-んァ-ヶ]", surface):
            continue
        if len(surface) == 1 and pos not in {"名詞", "動詞", "形容詞"}:
            continue
        tokens.append(surface)
    return tokens
