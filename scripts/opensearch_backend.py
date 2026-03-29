from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class OpenSearchConfig:
    base_url: str
    index_name: str = "deep-search-mvp"
    username: str | None = None
    password: str | None = None
    vector_dims: int = 1024
    verify_tls: bool = True

    @classmethod
    def from_env(cls) -> "OpenSearchConfig | None":
        base_url = os.getenv("OPENSEARCH_URL")
        if not base_url:
            return None
        return cls(
            base_url=base_url,
            index_name=os.getenv("OPENSEARCH_INDEX", "deep-search-mvp"),
            username=os.getenv("OPENSEARCH_USERNAME"),
            password=os.getenv("OPENSEARCH_PASSWORD"),
            vector_dims=int(os.getenv("OPENSEARCH_VECTOR_DIMS", "1024")),
            verify_tls=os.getenv("OPENSEARCH_VERIFY_TLS", "true").lower() not in {"0", "false", "no"},
        )


def build_index_mapping(vector_dims: int = 1024) -> dict[str, Any]:
    return {
        "settings": {
            "index": {"knn": True},
            "analysis": {"analyzer": {"default": {"type": "standard"}}},
        },
        "mappings": {
            "properties": {
                "doc_id": {"type": "keyword"},
                "platform": {"type": "keyword"},
                "source_type": {"type": "keyword"},
                "title": {"type": "text"},
                "url": {"type": "keyword"},
                "canonical_url": {"type": "keyword"},
                "body": {"type": "text"},
                "snippet": {"type": "text"},
                "author": {"type": "text"},
                "published_at": {"type": "date", "ignore_malformed": True},
                "language": {"type": "keyword"},
                "credibility_hints": {"type": "keyword"},
                "content_hash": {"type": "keyword"},
                "engagement": {"type": "object", "enabled": True},
                "metadata": {"type": "object", "enabled": True},
                "quality": {"type": "object", "enabled": True},
                "rerank": {"type": "object", "enabled": True},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": vector_dims,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "lucene",
                    },
                },
            }
        },
    }


def build_text_query(query: str, size: int = 10) -> dict[str, Any]:
    return {
        "size": size,
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title^4", "snippet^2", "body", "author", "metadata.topics^2"],
                "operator": "or",
                "minimum_should_match": "30%",
            }
        },
        "sort": [{"_score": {"order": "desc"}}, {"published_at": {"order": "desc", "unmapped_type": "date"}}],
    }


def build_hybrid_query(query: str, vector: list[float] | None = None, size: int = 10) -> dict[str, Any]:
    if not vector:
        return build_text_query(query, size=size)
    queries: list[dict[str, Any]] = [
        {
            "multi_match": {
                "query": query,
                "fields": ["title^4", "snippet^2", "body", "metadata.topics^2"],
                "operator": "or",
                "minimum_should_match": "30%",
            }
        },
        {
            "knn": {
                "embedding": {
                    "vector": vector,
                    "k": max(size * 8, 80),
                }
            }
        },
    ]
    return {
        "size": size,
        "query": {
            "hybrid": {
                "queries": queries,
            }
        },
    }


def prepare_document_for_indexing(document: dict[str, Any], embedding: list[float] | None = None) -> dict[str, Any]:
    payload = dict(document)
    if embedding:
        payload["embedding"] = embedding
    elif "embedding" in payload and not payload.get("embedding"):
        payload.pop("embedding", None)
    return payload


class OpenSearchClient:
    def __init__(self, config: OpenSearchConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")

    def _headers(self, content_type: str = "application/json") -> dict[str, str]:
        headers = {"Content-Type": content_type, "Accept": "application/json"}
        if self.config.username and self.config.password:
            token = base64.b64encode(f"{self.config.username}:{self.config.password}".encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {token}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        body: bytes | None = None,
        content_type: str = "application/json",
        parse_json: bool = True,
    ) -> Any:
        url = f"{self.base_url}{path}"
        request = urllib.request.Request(url, data=body, method=method, headers=self._headers(content_type))
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read()
                if not parse_json:
                    return payload.decode("utf-8")
                return json.loads(payload.decode("utf-8")) if payload else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenSearch {method} {path} failed: HTTP {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenSearch connection failed for {url}: {exc.reason}") from exc

    def ping(self) -> dict[str, Any]:
        return self._request("GET", "/")

    def index_exists(self, index_name: str | None = None) -> bool:
        target = urllib.parse.quote(index_name or self.config.index_name)
        try:
            self._request("HEAD", f"/{target}", parse_json=False)
            return True
        except RuntimeError as exc:
            if "HTTP 404" in str(exc):
                return False
            raise

    def get_index_mapping(self, index_name: str | None = None) -> dict[str, Any]:
        target = urllib.parse.quote(index_name or self.config.index_name)
        return self._request("GET", f"/{target}/_mapping")

    def get_embedding_dims(self, index_name: str | None = None) -> int | None:
        mapping = self.get_index_mapping(index_name)
        payload = mapping.get(index_name or self.config.index_name) or next(iter(mapping.values()), {})
        properties = (((payload.get("mappings") or {}).get("properties")) or {})
        embedding = properties.get("embedding") or {}
        dims = embedding.get("dimension")
        try:
            return int(dims) if dims is not None else None
        except Exception:
            return None

    def get_vector_engine(self, index_name: str | None = None) -> str | None:
        mapping = self.get_index_mapping(index_name)
        payload = mapping.get(index_name or self.config.index_name) or next(iter(mapping.values()), {})
        properties = (((payload.get("mappings") or {}).get("properties")) or {})
        embedding = properties.get("embedding") or {}
        method = embedding.get("method") or {}
        engine = method.get("engine")
        return str(engine) if engine else None

    def resolve_index_for_vector_dims(self, vector_dims: int | None = None, index_name: str | None = None) -> tuple[str, int | None, str | None, bool]:
        target = index_name or self.config.index_name
        preferred_engine = "lucene"
        if not vector_dims:
            return target, None, None, False
        if not self.index_exists(target):
            return target, None, None, False
        existing_dims = self.get_embedding_dims(target)
        existing_engine = self.get_vector_engine(target)
        if (existing_dims is None or existing_dims == vector_dims) and (existing_engine in {None, preferred_engine}):
            return target, existing_dims, existing_engine, False
        suffix = f"d{vector_dims}"
        if existing_engine and existing_engine != preferred_engine:
            suffix += f"-{preferred_engine}"
        rewritten = f"{target}-{suffix}"
        return rewritten, existing_dims, existing_engine, True

    def create_index(self, index_name: str | None = None, vector_dims: int | None = None) -> dict[str, Any]:
        target = urllib.parse.quote(index_name or self.config.index_name)
        mapping = build_index_mapping(vector_dims or self.config.vector_dims)
        return self._request("PUT", f"/{target}", body=json.dumps(mapping).encode("utf-8"))

    def ensure_index(self, index_name: str | None = None, vector_dims: int | None = None) -> dict[str, Any]:
        target = index_name or self.config.index_name
        if self.index_exists(target):
            return {"acknowledged": True, "exists": True, "index": target}
        return self.create_index(target, vector_dims=vector_dims)

    def bulk_index(self, documents: list[dict[str, Any]], index_name: str | None = None, refresh: bool = True) -> dict[str, Any]:
        target = urllib.parse.quote(index_name or self.config.index_name)
        lines: list[str] = []
        for doc in documents:
            doc_id = doc.get("doc_id") or doc.get("docId")
            lines.append(json.dumps({"index": {"_index": urllib.parse.unquote(target), "_id": doc_id}}, ensure_ascii=False))
            lines.append(json.dumps(doc, ensure_ascii=False))
        body = ("\n".join(lines) + "\n").encode("utf-8")
        suffix = "?refresh=true" if refresh else ""
        return self._request("POST", f"/_bulk{suffix}", body=body, content_type="application/x-ndjson")

    def search(self, query: str, size: int = 10, vector: list[float] | None = None, index_name: str | None = None) -> dict[str, Any]:
        target = urllib.parse.quote(index_name or self.config.index_name)
        payload = build_hybrid_query(query, vector=vector, size=size)
        return self._request("POST", f"/{target}/_search", body=json.dumps(payload).encode("utf-8"))

    def extract_documents(self, search_response: dict[str, Any]) -> list[dict[str, Any]]:
        hits = (((search_response or {}).get("hits") or {}).get("hits") or [])
        documents: list[dict[str, Any]] = []
        for hit in hits:
            source = dict(hit.get("_source") or {})
            source["score"] = hit.get("_score")
            source["index_id"] = hit.get("_id")
            documents.append(source)
        return documents


def dump_mapping(path: str, vector_dims: int = 1024) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(build_index_mapping(vector_dims), fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def _load_json_file(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenSearch integration helper for the deep-search-research MVP.")
    parser.add_argument("--url", help="OpenSearch base URL, e.g. http://localhost:9200")
    parser.add_argument("--index", default=os.getenv("OPENSEARCH_INDEX", "deep-search-mvp"))
    parser.add_argument("--username", default=os.getenv("OPENSEARCH_USERNAME"))
    parser.add_argument("--password", default=os.getenv("OPENSEARCH_PASSWORD"))
    parser.add_argument("--dims", type=int, default=int(os.getenv("OPENSEARCH_VECTOR_DIMS", "1024")))

    subparsers = parser.add_subparsers(dest="command", required=True)

    mapping_parser = subparsers.add_parser("mapping", help="Write mapping JSON to disk")
    mapping_parser.add_argument("--output", required=True)

    subparsers.add_parser("ping", help="Ping the OpenSearch cluster")
    subparsers.add_parser("ensure-index", help="Create index if it does not exist")

    bulk_parser = subparsers.add_parser("bulk-index", help="Bulk index documents from a JSON file")
    bulk_parser.add_argument("--input", required=True, help="Path to a JSON array of documents")

    search_parser = subparsers.add_parser("search", help="Run a text or hybrid search")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--size", type=int, default=5)

    args = parser.parse_args()

    if args.command == "mapping":
        dump_mapping(args.output, vector_dims=args.dims)
        return 0

    config = OpenSearchConfig(
        base_url=args.url or os.getenv("OPENSEARCH_URL", ""),
        index_name=args.index,
        username=args.username,
        password=args.password,
        vector_dims=args.dims,
    )
    if not config.base_url:
        raise SystemExit("OpenSearch URL is required. Pass --url or set OPENSEARCH_URL.")

    client = OpenSearchClient(config)

    if args.command == "ping":
        print(json.dumps(client.ping(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "ensure-index":
        print(json.dumps(client.ensure_index(), ensure_ascii=False, indent=2))
        return 0
    if args.command == "bulk-index":
        documents = _load_json_file(args.input)
        print(json.dumps(client.bulk_index(documents), ensure_ascii=False, indent=2))
        return 0
    if args.command == "search":
        response = client.search(args.query, size=args.size)
        print(json.dumps({
            "raw": response,
            "documents": client.extract_documents(response),
        }, ensure_ascii=False, indent=2))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
