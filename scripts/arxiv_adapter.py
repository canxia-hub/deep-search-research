from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET

from http_utils import canonicalize_url, normalize_whitespace, sanitize_extracted_text, stable_hash, http_get_text, keyword_overlap_score
from query_understanding import build_platform_queries
from source_adapter import NormalizedDocument, SourceAdapter, SourceCapability

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivAdapter(SourceAdapter):
    capability = SourceCapability(
        platform="arxiv",
        supports_api=True,
        supports_site_search=True,
        supports_browser_crawl=False,
        supports_comments=False,
        requires_auth=False,
        risk_level="low",
        preferred_mode="federated",
    )

    def search(self, query: str, limit: int = 5) -> list[NormalizedDocument]:
        queries = build_platform_queries(query, "arxiv")
        seen: set[str] = set()
        documents: list[NormalizedDocument] = []
        for candidate_query in queries:
            encoded_query = urllib.parse.quote(candidate_query)
            url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_query}&start=0&max_results={limit}"
            xml_text = http_get_text(
                url,
                headers={"Accept": "application/atom+xml"},
                ttl_seconds=7200,
                retries=1,
                backoff_seconds=1.5,
                allow_insecure_ssl=True,
            )
            root = ET.fromstring(xml_text)
            for entry in root.findall("atom:entry", ATOM_NS):
                title = sanitize_extracted_text(entry.findtext("atom:title", default="", namespaces=ATOM_NS), max_length=300)
                summary = sanitize_extracted_text(entry.findtext("atom:summary", default="", namespaces=ATOM_NS), max_length=700)
                entry_id = normalize_whitespace(entry.findtext("atom:id", default="", namespaces=ATOM_NS))
                authors = [normalize_whitespace(author.findtext("atom:name", default="", namespaces=ATOM_NS)) for author in entry.findall("atom:author", ATOM_NS)]
                body = normalize_whitespace(f"{title} {summary}")
                doc = NormalizedDocument(
                    doc_id=f"arxiv:{entry_id.rsplit('/', 1)[-1]}",
                    platform="arxiv",
                    source_type="academic",
                    title=title,
                    url=entry_id,
                    canonical_url=canonicalize_url(entry_id),
                    body=body,
                    snippet=summary[:400],
                    author=", ".join([name for name in authors if name]),
                    published_at=normalize_whitespace(entry.findtext("atom:published", default="", namespaces=ATOM_NS)),
                    language="en",
                    engagement={},
                    credibility_hints=["academic_paper", "arxiv_preprint"],
                    content_hash=stable_hash(body or entry_id),
                    metadata={"authors": authors, "query": candidate_query},
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
