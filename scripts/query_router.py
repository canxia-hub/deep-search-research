from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from adapter_registry import get_capability
from question_classifier import classify_question

RISK_MODE_ALLOWLIST = {
    "compliant": {"low", "medium"},
    "standard": {"low", "medium", "high"},
    "aggressive": {"low", "medium", "high"},
}


@dataclass
class RouteDecision:
    question: str
    platforms: list[str]
    strategy: str
    skipped: list[dict[str, str]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


TIER_DEFAULTS = {
    "federated": ["github", "hackernews", "arxiv", "semantic-scholar"],
    "indexed": ["github", "arxiv"],
    "hybrid": ["github", "arxiv", "semantic-scholar", "hackernews"],
}

PLATFORM_KEYWORDS = {
    "github": ["开源", "代码", "repo", "仓库", "项目", "编码助手", "代码助手", "agent", "framework", "案例", "代表性", "产品", "工作流", "交付形态", "compare", "comparison"],
    "hackernews": ["趋势", "讨论", "产品", "形态", "发布", "show hn", "ask hn", "deep research", "workflow", "风险", "争议", "限制", "对比", "比较"],
    "arxiv": ["论文", "学术", "benchmark", "方法", "研究", "citation", "model", "比较", "对比"],
    "semantic-scholar": ["论文", "学术", "citation", "研究", "paper", "model", "比较", "对比", "comparison"],
}


def platform_query_fit(question: str, platform: str) -> bool:
    lowered = question.lower()
    keywords = PLATFORM_KEYWORDS.get(platform, [])
    if not keywords:
        return True
    return any(keyword.lower() in lowered for keyword in keywords)


def route_step(step: dict[str, Any], goal: str = "", mode: str = "compliant") -> RouteDecision:
    requested = step.get("platformHints") or []
    question_profile = classify_question(step.get("question", ""))
    strategy_defaults = TIER_DEFAULTS.get(step.get("strategy", "hybrid"), [])
    merged_requested = list(dict.fromkeys([*requested, *question_profile.preferred_platforms, *strategy_defaults]))
    allowed_risks = RISK_MODE_ALLOWLIST.get(mode, {"low", "medium"})
    platforms: list[str] = []
    skipped: list[dict[str, str]] = []
    question = step.get("question", "")
    retrieval_text = f"{goal} {question}".strip()
    for platform in merged_requested:
        capability = get_capability(platform)
        if not capability:
            skipped.append({"platform": platform, "reason": "adapter_not_registered"})
            continue
        if capability.risk_level not in allowed_risks:
            skipped.append({"platform": platform, "reason": f"risk_blocked:{capability.risk_level}"})
            continue
        if platform not in requested and not platform_query_fit(retrieval_text, platform):
            skipped.append({"platform": platform, "reason": "low_query_fit"})
            continue
        platforms.append(platform)
    return RouteDecision(
        question=question,
        platforms=platforms,
        strategy=step.get("strategy", "hybrid"),
        skipped=skipped,
    )


def route_plan(plan: dict[str, Any]) -> list[RouteDecision]:
    mode = plan.get("mode", "compliant")
    goal = plan.get("goal", "")
    return [route_step(step, goal=goal, mode=mode) for step in plan.get("steps", [])]
