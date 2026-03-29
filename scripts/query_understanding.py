from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

PLATFORM_LANGUAGE_POLICY = {
    "github": "en",
    "hackernews": "en",
    "arxiv": "en",
    "semantic-scholar": "en",
    "zhihu": "zh",
    "bilibili": "zh",
    "xiaohongshu": "zh",
    "douyin": "zh",
}

COMPOSITE_ALIAS_RULES = [
    (["开源", "ai", "编码助手"], ["open source ai coding assistant ecosystem", "ai coding assistant", "open source ai agents", "coding agent"]),
    (["开源", "代码助手"], ["open source ai code assistant ecosystem", "code assistant", "open source ai agents", "coding agent"]),
    (["deep", "research", "产品形态"], ["deep research product comparison", "deep research product patterns", "research agent product"]),
    (["deep", "research", "对比"], ["deep research comparison", "research agent comparison", "research assistant comparison"]),
    (["产品形态"], ["product patterns", "product design", "workflow patterns"]),
    (["趋势"], ["trends", "recent developments"]),
    (["争议", "风险"], ["controversies", "risks", "limitations"]),
]

TERM_ALIAS_MAP = {
    "开源": "open source",
    "生态": "ecosystem",
    "编码助手": "coding assistant",
    "代码助手": "code assistant",
    "编程助手": "programming assistant",
    "copilot": "copilot",
    "代理": "agent",
    "智能体": "agent",
    "趋势": "trends",
    "争议": "controversies",
    "限制": "limitations",
    "风险": "risks",
    "论文": "research papers",
    "研究": "research",
    "对比": "comparison",
    "比较": "comparison",
    "主流": "mainstream",
    "产品形态": "product patterns",
    "交付形态": "delivery pattern",
    "工作流": "workflow",
    "来源策略": "source strategy",
    "案例": "cases",
    "项目": "projects",
    "证据": "evidence",
}

REGION_ALIAS_MAP = {
    "中国": ["China", "Chinese"],
    "国内": ["China", "Chinese"],
    "美国": ["United States", "US", "American"],
    "欧洲": ["Europe", "European"],
    "日本": ["Japan", "Japanese"],
    "德国": ["Germany", "German"],
    "全球": ["global", "worldwide"],
    "国际": ["global", "international"],
}


@dataclass
class QueryProfile:
    original: str
    detected_languages: list[str]
    region_hints: list[str]
    english_terms: list[str]
    ascii_terms: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def detect_languages(text: str) -> list[str]:
    langs: list[str] = []
    if re.search(r"[\u4e00-\u9fff]", text):
        langs.append("zh")
    if re.search(r"[A-Za-z]", text):
        langs.append("en")
    return langs or ["unknown"]


def extract_region_hints(text: str) -> list[str]:
    hints: list[str] = []
    for key, aliases in REGION_ALIAS_MAP.items():
        if key in text:
            hints.extend(aliases)
    return list(dict.fromkeys(hints))


def extract_english_terms(text: str) -> list[str]:
    lowered = text.lower()
    terms: list[str] = []
    for required_terms, expansions in COMPOSITE_ALIAS_RULES:
        if all(term.lower() in lowered for term in required_terms):
            terms.extend(expansions)
    for term, alias in TERM_ALIAS_MAP.items():
        if term.lower() in lowered:
            terms.append(alias)
    return list(dict.fromkeys(terms))


def build_query_profile(text: str) -> QueryProfile:
    return QueryProfile(
        original=text,
        detected_languages=detect_languages(text),
        region_hints=extract_region_hints(text),
        english_terms=extract_english_terms(text),
        ascii_terms=re.findall(r"[A-Za-z0-9][A-Za-z0-9\-+/]*", text),
    )


def _phrase_priority(phrase: str) -> tuple[int, int]:
    lowered = phrase.lower()
    keywords = ["ai", "assistant", "coding", "code", "agent", "research", "deep"]
    hit_score = sum(1 for keyword in keywords if keyword in lowered)
    return hit_score, -len(phrase.split())


def build_platform_query(text: str, platform: str) -> str:
    profile = build_query_profile(text)
    policy = PLATFORM_LANGUAGE_POLICY.get(platform, "en")
    if policy == "zh":
        return text

    phrases = [term for term in profile.english_terms if " " in term]
    single_terms = [term for term in profile.english_terms if " " not in term]
    region_terms = profile.region_hints[:2]
    ascii_terms = [term for term in profile.ascii_terms if len(term) > 1][:3]

    if platform == "github":
        if phrases:
            selected = [max(phrases, key=_phrase_priority)]
        else:
            selected = [*single_terms[:2], *region_terms[:1], *ascii_terms[:1]]
    elif platform == "hackernews":
        if phrases:
            selected = [phrases[0]]
        else:
            selected = [*single_terms[:2], *region_terms[:1], *ascii_terms[:1]]
    elif platform in {"arxiv", "semantic-scholar"}:
        selected = [*phrases[:2], *single_terms[:3], *region_terms[:2], *ascii_terms[:2]]
    else:
        selected = [*phrases[:2], *single_terms[:3], *region_terms[:2], *ascii_terms[:2]]

    selected = list(dict.fromkeys([part.strip() for part in selected if part.strip()]))
    return " ".join(selected).strip() or text


def build_platform_queries(text: str, platform: str) -> list[str]:
    base_query = build_platform_query(text, platform)
    profile = build_query_profile(text)
    variants: list[str] = [base_query]

    lowered = text.lower()
    if "deep research" in lowered or "产品形态" in text or "comparison" in lowered or "对比" in text or "比较" in text:
        variants.extend([
            "deep research",
            "research agent",
            "research assistant",
            "deep research product",
        ])
    if "编码助手" in text or "代码助手" in text or "coding assistant" in lowered or "code assistant" in lowered:
        variants.extend([
            "ai coding assistant",
            "code assistant",
            "coding agent",
            "open source ai coding assistant",
        ])

    variants.extend(term for term in profile.english_terms if len(term.split()) <= 4)
    variants.extend(term for term in profile.ascii_terms if len(term) > 2)

    cleaned = [variant.strip() for variant in variants if variant and variant.strip()]
    deduped = list(dict.fromkeys(cleaned))

    if platform == "github":
        return deduped[:5]
    if platform == "hackernews":
        return deduped[:5]
    if platform in {"arxiv", "semantic-scholar"}:
        return deduped[:4]
    return deduped[:4]
