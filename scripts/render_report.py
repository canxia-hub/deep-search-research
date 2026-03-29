from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def render_markdown(report: dict) -> str:
    title = report.get("title", "Untitled Research Report")
    summary = report.get("summary", "")
    sections = report.get("sections", [])
    sources = report.get("sources", [])
    limitations = report.get("limitations", [])
    next_questions = report.get("nextQuestions", [])

    lines: list[str] = [f"# {title}", ""]
    if summary:
        lines.extend(["## 执行摘要", "", summary, ""])

    for section in sections:
        lines.extend([f"## {section.get('title', '未命名章节')}", ""])
        for finding in section.get("findings", []):
            lines.append(f"- {finding}")
        citations = section.get("citations", [])
        if citations:
            lines.extend(["", f"引用: {', '.join(citations)}"])
        lines.append("")

    if limitations:
        lines.extend(["## 限制与边界", ""])
        for item in limitations:
            lines.append(f"- {item}")
        lines.append("")

    if next_questions:
        lines.extend(["## 后续研究问题", ""])
        for item in next_questions:
            lines.append(f"- {item}")
        lines.append("")

    if sources:
        lines.extend(["## 来源列表", ""])
        for index, item in enumerate(sources, start=1):
            if isinstance(item, dict):
                title = item.get("title") or item.get("id") or f"source-{index}"
                url = item.get("url", "")
                lines.append(f"{index}. {title} - {url}".rstrip(" -"))
            else:
                lines.append(f"{index}. {item}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a markdown research report from JSON.")
    parser.add_argument("input", help="Path to report JSON")
    parser.add_argument("--output", help="Optional output markdown path")
    args = parser.parse_args()

    report = load_json(args.input)
    markdown = render_markdown(report)

    if args.output:
        Path(args.output).write_text(markdown, encoding="utf-8")
    else:
        sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())