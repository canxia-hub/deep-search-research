from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class QuestionProfile:
    question: str
    question_type: str
    intent_tags: list[str]
    preferred_platforms: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


QUESTION_RULES = [
    ("risk", ["风险", "争议", "限制", "问题", "缺点"], ["hackernews", "semantic-scholar", "github"], 1.35),
    ("trend", ["趋势", "变化", "近两年", "发展", "演进"], ["hackernews", "github", "semantic-scholar"], 1.25),
    ("examples", ["案例", "项目", "证据", "代表性", "仓库"], ["github", "hackernews", "semantic-scholar", "arxiv"], 1.15),
    ("definition", ["定义", "范围", "核心对象", "是什么", "边界"], ["arxiv", "semantic-scholar", "github"], 1.2),
    ("product-comparison", ["对比", "比较", "产品形态", "工作流", "交付形态", "关键差异", "workflow", "comparison", "compare", "deep research"], ["hackernews", "semantic-scholar", "github", "arxiv"], 1.0),
]


def classify_question(question: str) -> QuestionProfile:
    lowered = question.lower()
    best_match: tuple[str, list[str], list[str], float] | None = None
    for question_type, keywords, platforms, weight in QUESTION_RULES:
        matched = [keyword for keyword in keywords if keyword.lower() in lowered]
        score = len(matched) * weight
        if score == 0:
            continue
        if best_match is None or score > best_match[3]:
            best_match = (question_type, matched, platforms, score)
    if best_match:
        question_type, matched, platforms, _ = best_match
        return QuestionProfile(
            question=question,
            question_type=question_type,
            intent_tags=matched,
            preferred_platforms=platforms,
        )
    return QuestionProfile(
        question=question,
        question_type="generic-research",
        intent_tags=[],
        preferred_platforms=["github", "hackernews", "semantic-scholar", "arxiv"],
    )
