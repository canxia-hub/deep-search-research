from __future__ import annotations

from collections import defaultdict
from typing import Any


def detect_theme(title: str, snippet: str) -> str:
    text = f"{title} {snippet}".lower()
    if any(keyword in text for keyword in ["assistant", "copilot", "agent", "coding"]):
        return "assistant-tools"
    if any(keyword in text for keyword in ["research", "deep research", "comparison", "workflow"]):
        return "research-workflow"
    if any(keyword in text for keyword in ["risk", "license", "security", "limitation", "controvers"]):
        return "risk-and-limits"
    if any(keyword in text for keyword in ["framework", "platform", "product"]):
        return "platform-product"
    return "general"


def build_evidence_clusters(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for doc in documents:
        source_type = doc.get("source_type") or doc.get("sourceType") or "unknown"
        theme = detect_theme(doc.get("title", ""), doc.get("snippet", ""))
        grouped[(source_type, theme)].append(doc)

    clusters: list[dict[str, Any]] = []
    for (source_type, theme), docs in grouped.items():
        docs = sorted(docs, key=lambda item: ((item.get("quality") or {}).get("combined") or 0), reverse=True)
        clusters.append(
            {
                "sourceType": source_type,
                "theme": theme,
                "count": len(docs),
                "topTitles": [doc.get("title", "Untitled") for doc in docs[:3]],
                "docs": docs[:3],
            }
        )
    clusters.sort(key=lambda item: item["count"], reverse=True)
    return clusters
