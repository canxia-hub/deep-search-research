from __future__ import annotations

import urllib.parse

from http_utils import canonicalize_url, normalize_whitespace, stable_hash, strip_html, http_get_json, keyword_overlap_score, sanitize_extracted_text
from query_understanding import build_platform_queries
from source_adapter import NormalizedDocument, SourceAdapter, SourceCapability


class HackerNewsAdapter(SourceAdapter):
    capability = SourceCapability(
        platform="hackernews",
        supports_api=True,
        supports_site_search=True,
        supports_browser_crawl=False,
        supports_comments=True,
        requires_auth=False,
        risk_level="low",
        preferred_mode="federated",
    )

    def search(self, query: str, limit: int = 5) -> list[NormalizedDocument]:
        queries = build_platform_queries(query, "hackernews")
        seen: set[str] = set()
        documents: list[NormalizedDocument] = []
        for candidate_query in queries:
            encoded_query = urllib.parse.quote(candidate_query)
            url = f"https://hn.algolia.com/api/v1/search?query={encoded_query}&hitsPerPage={limit}"
            payload = http_get_json(url, ttl_seconds=900, retries=2, backoff_seconds=1.0)
            hits = payload.get("hits", [])
            for item in hits:
                story_url = item.get("url") or f"https://news.ycombinator.com/item?id={item.get('objectID')}"
                canonical_url = canonicalize_url(story_url)
                text = sanitize_extracted_text(strip_html(item.get("story_text") or item.get("comment_text") or ""), max_length=500)
                title = item.get("title") or item.get("story_title") or "Untitled Hacker News Item"
                body = normalize_whitespace(f"{title} {text}")
                doc = NormalizedDocument(
                    doc_id=f"hackernews:{item.get('objectID')}",
                    platform="hackernews",
                    source_type="community",
                    title=title,
                    url=story_url,
                    canonical_url=canonical_url,
                    body=body,
                    snippet=text[:300],
                    author=item.get("author", ""),
                    published_at=item.get("created_at", ""),
                    language="en",
                    engagement={
                        "points": item.get("points", 0),
                        "comments": item.get("num_comments", 0),
                    },
                    credibility_hints=["hn_discussion"],
                    content_hash=stable_hash(body or canonical_url),
                    metadata={"hn_id": item.get("objectID"), "query": candidate_query},
                )
                overlap = keyword_overlap_score(query, f"{doc.title} {doc.snippet} {doc.body}")
                if overlap < 0.05:
                    continue
                key = doc.canonical_url or doc.doc_id
                if key in seen:
                    continue
                seen.add(key)
                documents.append(doc)
                if len(documents) >= limit:
                    return documents
        return documents
