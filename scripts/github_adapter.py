from __future__ import annotations

import urllib.parse

from http_utils import canonicalize_url, normalize_whitespace, sanitize_extracted_text, stable_hash, http_get_json, keyword_overlap_score
from query_understanding import build_platform_queries
from source_adapter import NormalizedDocument, SourceAdapter, SourceCapability


class GitHubAdapter(SourceAdapter):
    capability = SourceCapability(
        platform="github",
        supports_api=True,
        supports_site_search=True,
        supports_browser_crawl=False,
        supports_comments=True,
        requires_auth=False,
        risk_level="low",
        preferred_mode="federated",
    )

    def search(self, query: str, limit: int = 5) -> list[NormalizedDocument]:
        queries = build_platform_queries(query, "github")
        seen: set[str] = set()
        documents: list[NormalizedDocument] = []
        for candidate_query in queries:
            encoded_query = urllib.parse.quote(candidate_query)
            url = f"https://api.github.com/search/repositories?q={encoded_query}&sort=stars&order=desc&per_page={limit}"
            payload = http_get_json(
                url,
                headers={"Accept": "application/vnd.github+json"},
                ttl_seconds=1800,
                retries=2,
                backoff_seconds=1.2,
            )
            items = payload.get("items", [])
            for item in items:
                description = sanitize_extracted_text(item.get("description") or "", max_length=400)
                canonical_url = canonicalize_url(item.get("html_url", ""))
                body = normalize_whitespace(
                    f"{item.get('full_name', '')} {description} primary language {item.get('language') or ''} stars {item.get('stargazers_count') or 0} topics {' '.join(item.get('topics', []))}"
                )
                doc = NormalizedDocument(
                    doc_id=f"github:{item.get('full_name', '')}",
                    platform="github",
                    source_type="community",
                    title=item.get("full_name", "Untitled GitHub Repository"),
                    url=item.get("html_url", ""),
                    canonical_url=canonical_url,
                    body=body,
                    snippet=description,
                    author=(item.get("owner") or {}).get("login", ""),
                    published_at=item.get("updated_at", ""),
                    language="en",
                    engagement={
                        "stars": item.get("stargazers_count", 0),
                        "forks": item.get("forks_count", 0),
                        "watchers": item.get("watchers_count", 0),
                    },
                    credibility_hints=["github_repo"],
                    content_hash=stable_hash(body or canonical_url),
                    metadata={
                        "topics": item.get("topics", []),
                        "license": ((item.get("license") or {}).get("spdx_id") or ""),
                        "query": candidate_query,
                    },
                )
                overlap = keyword_overlap_score(query, f"{doc.title} {doc.snippet} {doc.body}")
                if overlap < 0.06:
                    continue
                key = doc.canonical_url or doc.doc_id
                if key in seen:
                    continue
                seen.add(key)
                documents.append(doc)
                if len(documents) >= limit:
                    return documents
        return documents
