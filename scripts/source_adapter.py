from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SourceCapability:
    platform: str
    supports_api: bool = True
    supports_site_search: bool = True
    supports_browser_crawl: bool = False
    supports_comments: bool = False
    requires_auth: bool = False
    risk_level: str = "low"
    preferred_mode: str = "federated"


@dataclass
class NormalizedDocument:
    doc_id: str
    platform: str
    source_type: str
    title: str
    url: str
    canonical_url: str
    body: str = ""
    snippet: str = ""
    author: str = ""
    published_at: str = ""
    language: str = ""
    engagement: dict[str, Any] = field(default_factory=dict)
    parent_id: str | None = None
    credibility_hints: list[str] = field(default_factory=list)
    content_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NormalizedDocument":
        return cls(
            doc_id=payload.get("doc_id") or payload.get("docId") or "",
            platform=payload.get("platform") or "",
            source_type=payload.get("source_type") or payload.get("sourceType") or "community",
            title=payload.get("title") or "",
            url=payload.get("url") or "",
            canonical_url=payload.get("canonical_url") or payload.get("canonicalUrl") or payload.get("url") or "",
            body=payload.get("body") or "",
            snippet=payload.get("snippet") or "",
            author=payload.get("author") or "",
            published_at=payload.get("published_at") or payload.get("publishedAt") or "",
            language=payload.get("language") or "",
            engagement=dict(payload.get("engagement") or {}),
            parent_id=payload.get("parent_id") or payload.get("parentId"),
            credibility_hints=list(payload.get("credibility_hints") or payload.get("credibilityHints") or []),
            content_hash=payload.get("content_hash") or payload.get("contentHash") or "",
            metadata=dict(payload.get("metadata") or {}),
        )


class SourceAdapter:
    capability: SourceCapability

    def search(self, query: str, limit: int = 5) -> list[NormalizedDocument]:
        raise NotImplementedError
