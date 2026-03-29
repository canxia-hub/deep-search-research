from __future__ import annotations

import urllib.parse

from http_utils import canonicalize_url, normalize_whitespace, sanitize_extracted_text, stable_hash, http_get_json, keyword_overlap_score
from query_understanding import build_platform_queries
from source_adapter import NormalizedDocument, SourceAdapter, SourceCapability

FIELDS = "title,abstract,url,authors,year,citationCount,publicationDate,publicationVenue"


class SemanticScholarAdapter(SourceAdapter):
    capability = SourceCapability(
        platform="semantic-scholar",
        supports_api=True,
        supports_site_search=True,
        supports_browser_crawl=False,
        supports_comments=False,
        requires_auth=False,
        risk_level="low",
        preferred_mode="federated",
    )

    def search(self, query: str, limit: int = 5) -> list[NormalizedDocument]:
        queries = build_platform_queries(query, "semantic-scholar")
        seen: set[str] = set()
        documents: list[NormalizedDocument] = []
        for candidate_query in queries:
            encoded_query = urllib.parse.quote(candidate_query)
            url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={encoded_query}&limit={limit}&fields={FIELDS}"
            payload = http_get_json(
                url,
                ttl_seconds=21600,
                retries=1,
                backoff_seconds=3.0,
            )
            items = payload.get("data", [])
            for item in items:
                title = sanitize_extracted_text(item.get("title") or "", max_length=300)
                abstract = sanitize_extracted_text(item.get("abstract") or "", max_length=700)
                paper_url = item.get("url") or ""
                authors = [normalize_whitespace((author or {}).get("name") or "") for author in item.get("authors", [])]
                body = normalize_whitespace(f"{title} {abstract}")
                doc = NormalizedDocument(
                    doc_id=f"semantic-scholar:{stable_hash(paper_url or title)[:16]}",
                    platform="semantic-scholar",
                    source_type="academic",
                    title=title or "Untitled Semantic Scholar Paper",
                    url=paper_url,
                    canonical_url=canonicalize_url(paper_url) if paper_url else paper_url,
                    body=body,
                    snippet=abstract[:400],
                    author=", ".join([name for name in authors if name]),
                    published_at=item.get("publicationDate") or str(item.get("year") or ""),
                    language="en",
                    engagement={"citations": item.get("citationCount", 0)},
                    credibility_hints=["academic_paper", "citation_indexed"],
                    content_hash=stable_hash(body or paper_url or title),
                    metadata={
                        "authors": authors,
                        "venue": ((item.get("publicationVenue") or {}).get("name") or ""),
                        "query": candidate_query,
                    },
                )
                overlap = keyword_overlap_score(query, f"{doc.title} {doc.snippet} {doc.body}")
                if overlap < 0.04:
                    continue
                key = doc.canonical_url or doc.doc_id
                if key in seen:
                    continue
                seen.add(key)
                documents.append(doc)
                if len(documents) >= limit:
                    return documents
        return documents
