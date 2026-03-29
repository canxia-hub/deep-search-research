from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone

PLATFORM_HINTS = {
    "github": ["开源", "代码", "repo", "仓库", "issue", "pull request", "工程", "产品", "工作流", "agent"],
    "arxiv": ["论文", "学术", "research", "paper", "arxiv", "benchmark"],
    "semantic-scholar": ["citation", "学术", "论文", "研究", "比较", "对比"],
    "hackernews": ["社区", "讨论", "趋势", "launch", "hn", "产品", "对比", "比较", "产品形态", "workflow"],
    "telegram": ["频道", "群组", "telegram", "社群"],
}


def infer_platforms(text: str) -> list[str]:
    lower = text.lower()
    matches: list[str] = []
    for platform, keywords in PLATFORM_HINTS.items():
        if any(keyword.lower() in lower for keyword in keywords):
            matches.append(platform)

    if _is_comparison_goal(text):
        matches.extend(["hackernews", "github", "semantic-scholar"])
    if "开源" in text or "repo" in lower or "仓库" in text:
        matches.append("github")

    deduped = list(dict.fromkeys(matches))
    return deduped or ["github", "arxiv", "semantic-scholar", "hackernews"]


def _is_comparison_goal(goal: str) -> bool:
    lowered = goal.lower()
    markers = ["对比", "比较", "vs", "versus", "产品形态", "product", "comparison", "compare"]
    return any(marker in lowered for marker in markers)


def split_questions(goal: str) -> list[str]:
    base = goal.strip().rstrip("。.!?？")
    questions = [
        f"这个主题的核心对象、范围与定义是什么？",
        f"{base} 的代表性案例、项目或证据有哪些？",
    ]
    if _is_comparison_goal(base):
        questions.append(f"{base} 在工作流、来源策略、交付形态上有哪些关键差异？")
    questions.extend(
        [
            f"{base} 在近两年有哪些关键变化与趋势？",
            f"围绕 {base} 的主要争议、限制与风险是什么？",
        ]
    )
    return questions


def infer_strategy(platform: str) -> str:
    if platform in {"github", "arxiv", "semantic-scholar", "hackernews"}:
        return "federated"
    if platform in {"telegram"}:
        return "hybrid"
    return "indexed"


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
    return text.strip("-")[:48] or "research-plan"


def build_plan(goal: str, mode: str, include_domains: list[str], exclude_domains: list[str]) -> dict:
    platforms = infer_platforms(goal)
    questions = split_questions(goal)
    steps = []
    for idx, question in enumerate(questions, start=1):
        step_platforms = platforms[:]
        strategy = "hybrid" if idx == len(questions) else infer_strategy(step_platforms[0])
        steps.append(
            {
                "id": f"step-{idx}",
                "question": question,
                "platformHints": step_platforms,
                "strategy": strategy,
                "priority": "high" if idx < 3 else "medium",
            }
        )
    now = datetime.now(timezone.utc).isoformat()
    return {
        "planId": f"plan-{slugify(goal)}",
        "goal": goal,
        "mode": mode,
        "includeDomains": include_domains,
        "excludeDomains": exclude_domains,
        "platforms": platforms,
        "steps": steps,
        "createdAt": now,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a deterministic research plan skeleton for deep-search-research skill.")
    parser.add_argument("goal", help="Research goal in natural language")
    parser.add_argument("--mode", default="compliant", choices=["compliant", "standard", "aggressive"])
    parser.add_argument("--include-domain", action="append", default=[])
    parser.add_argument("--exclude-domain", action="append", default=[])
    parser.add_argument("--output", help="Optional output path for JSON plan")
    args = parser.parse_args()

    plan = build_plan(args.goal, args.mode, args.include_domain, args.exclude_domain)
    payload = json.dumps(plan, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.write("\n")
    else:
        sys.stdout.write(payload)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())