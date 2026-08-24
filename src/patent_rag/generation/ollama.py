from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from patent_rag.retrieval.hybrid import SearchHit

CITATION_PATTERN = re.compile(r"\[S(\d+)]")
PROMPT_TEMPLATE_VERSION = "jp-patent-grounded-structured-v6"
SYSTEM_PROMPT = (
    "あなたは日本特許の技術調査アナリストです。検索根拠以外を使わず、"
    "原文にない課題・効果・欠点を追加してはいけません。"
    "指定されたJSON schemaに従い、各項目に使用したsource IDを返します。"
)
GENERATION_OPTIONS: dict[str, int | float] = {
    "temperature": 0.1,
    "top_p": 0.8,
    "num_ctx": 8192,
    "num_predict": 280,
    "seed": 2379,
}


@dataclass(frozen=True, slots=True)
class GeneratedAnswer:
    text: str
    cited_source_ids: list[str]
    grounded: bool
    mode: str
    model: str
    system_prompt: str | None
    user_prompt: str | None
    generation_options: dict[str, int | float] | None
    raw_model_output: str | None
    citation_validation_passed: bool


def build_evidence_prompt(query: str, hits: list[SearchHit], answer_language: str) -> str:
    language_instruction = {
        "ja": "日本語",
        "ko": "한국어",
        "en": "English",
    }.get(answer_language, "日本語")
    evidence_blocks = []
    for hit in hits:
        chunk = hit.chunk
        evidence_blocks.append(
            "\n".join(
                [
                    f"[S{hit.rank}]",
                    f"公開番号: JP {chunk['document_id']}",
                    f"公開年: {chunk['year']}",
                    f"セクション: {chunk['section']}",
                    f"本文: {chunk['text']}",
                ]
            )
        )
    evidence = "\n\n".join(evidence_blocks)
    return f"""質問: {query}

以下の検索根拠だけを使用して、{language_instruction}で回答してください。

厳守事項:
1. 根拠にない課題、効果、欠点、発明者、出願人、法的状態、数値を追加しない。
2. 各項目のsource_idsには、実際に使用した検索根拠だけを指定する。
3. 複数文献を混同せず、公開番号と技術的差異を明示する。
4. 根拠が不足する場合は「提供された根拠だけでは判断できません」と明記する。
5. 法的助言や法的状態の評価を行わない。
6. 同じ公開番号の異なるセクションを、別々の発明として扱わない。
7. 検索根拠に記載がないことを、特許文献全体に存在しないと断定しない。
8. problemとsolutionをそれぞれ簡潔な1文にし、前置きや繰り返しを避ける。
9. JSON以外の文章やMarkdownを出力しない。

検索根拠:
{evidence}
"""


def validate_citations(
    text: str,
    allowed_sources: int | set[int],
) -> tuple[list[str], bool]:
    cited_numbers = [int(number) for number in CITATION_PATTERN.findall(text)]
    unique_ids = list(dict.fromkeys(f"S{number}" for number in cited_numbers))
    allowed_numbers = (
        set(range(1, allowed_sources + 1)) if isinstance(allowed_sources, int) else allowed_sources
    )
    valid = bool(cited_numbers) and all(number in allowed_numbers for number in cited_numbers)
    return unique_ids, valid


def build_response_schema(hits: list[SearchHit]) -> dict[str, Any]:
    allowed_ids = [f"S{hit.rank}" for hit in hits]
    evidence_field = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "minLength": 1, "maxLength": 500},
            "source_ids": {
                "type": "array",
                "items": {"type": "string", "enum": allowed_ids},
                "minItems": 1,
                "uniqueItems": True,
            },
        },
        "required": ["text", "source_ids"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "problem": evidence_field,
            "solution": evidence_field,
        },
        "required": ["problem", "solution"],
        "additionalProperties": False,
    }


def render_structured_answer(
    raw_output: str,
    hits: list[SearchHit],
    answer_language: str,
) -> tuple[str, list[str]] | None:
    try:
        value = json.loads(raw_output)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(value, dict):
        return None
    allowed_ids = {f"S{hit.rank}" for hit in hits}
    rendered: dict[str, tuple[str, list[str]]] = {}
    all_citations: list[str] = []
    for key in ("problem", "solution"):
        field = value.get(key)
        if not isinstance(field, dict):
            return None
        field_text = field.get("text")
        source_ids = field.get("source_ids")
        if not isinstance(field_text, str) or not field_text.strip():
            return None
        if not isinstance(source_ids, list) or not source_ids:
            return None
        if not all(
            isinstance(source_id, str) and source_id in allowed_ids for source_id in source_ids
        ):
            return None
        unique_source_ids = list(dict.fromkeys(source_ids))
        rendered[key] = (field_text.strip(), unique_source_ids)
        all_citations.extend(unique_source_ids)

    labels = {
        "ja": ("結論", "課題", "解決手段", "根拠の限界"),
        "ko": ("결론", "과제", "해결수단", "근거의 한계"),
        "en": ("Conclusion", "Problem", "Solution", "Evidence limit"),
    }.get(answer_language, ("結論", "課題", "解決手段", "根拠の限界"))
    sections = list(dict.fromkeys(str(hit.chunk["section"]) for hit in hits))
    document_ids = list(dict.fromkeys(str(hit.chunk["document_id"]) for hit in hits))
    section_names = {
        "ja": {"abstract": "要約", "claim_11": "請求項11"},
        "ko": {"abstract": "요약", "claim_11": "청구항11"},
        "en": {"abstract": "abstract", "claim_11": "claim 11"},
    }.get(answer_language, {})
    joined_sections = ", ".join(section_names.get(section, section) for section in sections)
    joined_document_ids = ", ".join(document_ids)
    limitation_text = {
        "ja": (
            f"検索されたJP {joined_document_ids}の{joined_sections}だけに基づく"
            "技術要約であり、法的助言ではありません。"
        ),
        "ko": (
            f"검색된 JP {joined_document_ids}의 {joined_sections} 구역만을 근거로 한 "
            "기술 요약이며 법률 자문이 아닙니다."
        ),
        "en": (
            f"This technical summary uses only the retrieved {joined_sections} sections from "
            f"JP {joined_document_ids} and is not legal advice."
        ),
    }.get(answer_language, "検索された根拠だけに基づく技術要約です。")

    problem_text, problem_sources = rendered["problem"]
    solution_text, solution_sources = rendered["solution"]
    conclusion_text = {
        "ja": f"「{problem_text}」という課題に対し、{solution_text}",
        "ko": f"'{problem_text}'라는 과제에 대해 {solution_text}",
        "en": f"The patent addresses '{problem_text}' by {solution_text}",
    }.get(answer_language, f"{problem_text}に対し、{solution_text}")
    conclusion_sources = list(dict.fromkeys([*problem_sources, *solution_sources]))
    conclusion_citations = "".join(f"[{source_id}]" for source_id in conclusion_sources)
    lines = [f"{labels[0]}: {conclusion_text} {conclusion_citations}"]
    for label, key in zip(labels[1:3], ("problem", "solution"), strict=True):
        field_text, source_ids = rendered[key]
        citations = "".join(f"[{source_id}]" for source_id in source_ids)
        lines.append(f"{label}: {field_text} {citations}")
    limitation_citations = "".join(f"[{source_id}]" for source_id in dict.fromkeys(all_citations))
    lines.append(f"{labels[3]}: {limitation_text} {limitation_citations}")
    return "\n".join(lines), list(dict.fromkeys(all_citations))


def extractive_fallback(
    hits: list[SearchHit],
    answer_language: str,
    *,
    system_prompt: str | None = None,
    user_prompt: str | None = None,
) -> GeneratedAnswer:
    if not hits:
        messages = {
            "ja": "関連する根拠を検索できませんでした。質問をより具体的にしてください。",
            "ko": "관련 근거를 검색하지 못했습니다. 질문을 더 구체화해 주세요.",
            "en": "No relevant evidence was retrieved. Please make the question more specific.",
        }
        return GeneratedAnswer(
            text=messages.get(answer_language, messages["ja"]),
            cited_source_ids=[],
            grounded=False,
            mode="abstain",
            model="none",
            system_prompt=None,
            user_prompt=None,
            generation_options=None,
            raw_model_output=None,
            citation_validation_passed=False,
        )

    headers = {
        "ja": "ローカル生成モデルを利用できないため、上位の検索根拠を提示します。",
        "ko": "로컬 생성 모델을 사용할 수 없어 상위 검색 근거를 제시합니다.",
        "en": "The local generator is unavailable, so the strongest retrieved evidence is shown.",
    }
    lines = [headers.get(answer_language, headers["ja"])]
    source_ids: list[str] = []
    for hit in hits[:3]:
        source_id = f"S{hit.rank}"
        source_ids.append(source_id)
        compact = " ".join(str(hit.chunk["text"]).split())[:300]
        lines.append(
            f"- JP {hit.chunk['document_id']} ({hit.chunk['year']}, "
            f"{hit.chunk['section']}): {compact} [{source_id}]"
        )
    return GeneratedAnswer(
        text="\n".join(lines),
        cited_source_ids=source_ids,
        grounded=True,
        mode="extractive_fallback",
        model="none",
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        generation_options=GENERATION_OPTIONS if user_prompt else None,
        raw_model_output=None,
        citation_validation_passed=False,
    )


class OllamaGenerator:
    def __init__(self, base_url: str, model: str, timeout_seconds: float = 180.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                version_response = await client.get(f"{self.base_url}/api/version")
                version_response.raise_for_status()
                tags_response = await client.get(f"{self.base_url}/api/tags")
                tags_response.raise_for_status()
            models = [item.get("name", "") for item in tags_response.json().get("models", [])]
            return {
                "reachable": True,
                "version": version_response.json().get("version"),
                "model_ready": self.model in models,
                "models": models,
            }
        except (httpx.HTTPError, ValueError):
            return {"reachable": False, "version": None, "model_ready": False, "models": []}

    async def generate(
        self,
        query: str,
        hits: list[SearchHit],
        answer_language: str = "ja",
    ) -> GeneratedAnswer:
        if not hits:
            return extractive_fallback([], answer_language)
        prompt = build_evidence_prompt(query, hits, answer_language)
        payload = {
            "model": self.model,
            "stream": False,
            "think": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "format": build_response_schema(hits),
            "options": GENERATION_OPTIONS,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
            raw_output = response.json()["message"]["content"].strip()
            structured = render_structured_answer(raw_output, hits, answer_language)
            if structured is None:
                fallback = extractive_fallback(
                    hits,
                    answer_language,
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=prompt,
                )
                validation_notes = {
                    "ja": "生成回答の引用を検証できなかったため、検索根拠に切り替えました。",
                    "ko": "생성 답변의 인용을 검증할 수 없어 검색 근거로 대체했습니다.",
                    "en": "Citation validation failed; showing retrieved evidence instead.",
                }
                validation_note = validation_notes.get(answer_language, validation_notes["ja"])
                return GeneratedAnswer(
                    text=f"{fallback.text}\n\n[{validation_note}]",
                    cited_source_ids=fallback.cited_source_ids,
                    grounded=True,
                    mode="citation_guard_fallback",
                    model=self.model,
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=prompt,
                    generation_options=GENERATION_OPTIONS,
                    raw_model_output=raw_output,
                    citation_validation_passed=False,
                )
            text, cited_ids = structured
            return GeneratedAnswer(
                text=text,
                cited_source_ids=cited_ids,
                grounded=True,
                mode="ollama_structured",
                model=self.model,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
                generation_options=GENERATION_OPTIONS,
                raw_model_output=raw_output,
                citation_validation_passed=True,
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return extractive_fallback(
                hits,
                answer_language,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
            )
