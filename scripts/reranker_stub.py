from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from embedding_stub import cosine_similarity, embed_texts, has_real_embedding_provider

OPENCLAW_CONFIG_PATH = Path(os.getenv("OPENCLAW_CONFIG_PATH") or r"C:\Users\Administrator\.openclaw\openclaw.json")


@dataclass
class RerankerConfig:
    provider: str
    model: str = ""
    url: str = ""
    api_key: str = ""
    timeout_seconds: int = 30
    source: str = "env"

    @classmethod
    def from_env(cls) -> "RerankerConfig":
        provider = (os.getenv("DEEP_SEARCH_RERANKER_PROVIDER") or "").strip().lower()
        model = (os.getenv("DEEP_SEARCH_RERANKER_MODEL") or "").strip()
        url = (os.getenv("DEEP_SEARCH_RERANKER_URL") or "").strip().rstrip("/")
        api_key = (os.getenv("DEEP_SEARCH_RERANKER_API_KEY") or os.getenv("JINA_API_KEY") or "").strip()
        timeout_raw = (os.getenv("DEEP_SEARCH_RERANKER_TIMEOUT") or "30").strip()
        timeout_seconds = int(timeout_raw) if timeout_raw.isdigit() else 30

        if provider or model or url or api_key:
            if not provider:
                if url:
                    provider = "http-json"
                elif api_key:
                    provider = "jina"
                elif has_real_embedding_provider():
                    provider = "embedding-sim"
                else:
                    provider = "stub"
            return cls(provider=provider, model=model, url=url, api_key=api_key, timeout_seconds=timeout_seconds, source="env")

        fallback = _load_lancedb_reranker_config()
        if fallback:
            return fallback

        provider = "embedding-sim" if has_real_embedding_provider() else "stub"
        return cls(provider=provider, timeout_seconds=timeout_seconds, source="fallback")


def _load_openclaw_json() -> dict[str, Any]:
    if not OPENCLAW_CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(OPENCLAW_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_lancedb_reranker_config() -> RerankerConfig | None:
    payload = _load_openclaw_json()
    retrieval = (
        ((payload.get("plugins") or {}).get("entries") or {}).get("memory-lancedb-pro") or {}
    ).get("config", {}).get("retrieval", {})
    if not retrieval:
        return None

    rerank_provider = str(retrieval.get("rerankProvider") or "").strip().lower()
    rerank_endpoint = str(retrieval.get("rerankEndpoint") or "").strip().rstrip("/")
    rerank_api_key = str(retrieval.get("rerankApiKey") or "").strip()
    rerank_model = str(retrieval.get("rerankModel") or "").strip()

    provider = "http-json" if rerank_endpoint else ("embedding-sim" if has_real_embedding_provider() else "stub")
    if rerank_provider == "dashscope" and rerank_endpoint:
        provider = "http-json"

    return RerankerConfig(
        provider=provider,
        model=rerank_model,
        url=rerank_endpoint,
        api_key=rerank_api_key,
        timeout_seconds=30,
        source="openclaw.plugins.memory-lancedb-pro.retrieval",
    )


def _candidate_text(candidate: dict[str, Any]) -> str:
    parts = [
        candidate.get("title") or "",
        candidate.get("snippet") or "",
        candidate.get("body") or "",
    ]
    return " ".join(part.strip() for part in parts if str(part).strip())[:4000]


def _annotate_candidate(candidate: dict[str, Any], provider: str, raw_score: float, blended_score: float, rank: int) -> dict[str, Any]:
    payload = dict(candidate)
    quality = dict(payload.get("quality") or {})
    quality["rerankScore"] = round(raw_score, 4)
    quality["rerankBlended"] = round(blended_score, 4)
    payload["quality"] = quality
    payload["rerank"] = {
        "provider": provider,
        "score": round(raw_score, 4),
        "blended": round(blended_score, 4),
        "rank": rank,
    }
    return payload


def _embedding_similarity_rerank(query: str, candidates: list[dict[str, Any]], top_n: int | None = None) -> list[dict[str, Any]]:
    if not candidates:
        return []
    texts = [query, *[_candidate_text(candidate) for candidate in candidates]]
    vectors = embed_texts(texts, require_real_provider=True)
    if len(vectors) != len(texts):
        return candidates[:top_n] if top_n else candidates

    query_vector = vectors[0]
    ranked_rows: list[tuple[float, float, dict[str, Any]]] = []
    for candidate, vector in zip(candidates, vectors[1:], strict=False):
        semantic = max(0.0, cosine_similarity(query_vector, vector))
        base = float(((candidate.get("quality") or {}).get("combined") or 0.0))
        blended = semantic * 0.62 + base * 0.38
        ranked_rows.append((blended, semantic, candidate))

    ranked_rows.sort(key=lambda row: row[0], reverse=True)
    reranked = [
        _annotate_candidate(candidate, "embedding-sim", semantic, blended, rank=index)
        for index, (blended, semantic, candidate) in enumerate(ranked_rows, start=1)
    ]
    return reranked[:top_n] if top_n else reranked


def _request_jina_rerank(query: str, candidates: list[dict[str, Any]], config: RerankerConfig, top_n: int | None = None) -> list[dict[str, Any]]:
    if not config.api_key:
        raise RuntimeError("Jina API key is not configured")
    model = config.model or "jina-reranker-v2-base-multilingual"
    documents = [_candidate_text(candidate) for candidate in candidates]
    payload = {
        "model": model,
        "query": query,
        "documents": documents,
        "top_n": top_n or len(documents),
    }
    request = urllib.request.Request(
        "https://api.jina.ai/v1/rerank",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Jina rerank failed: HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Jina rerank connection failed: {exc.reason}") from exc

    payload = json.loads(body)
    results = payload.get("results") or []
    reranked: list[dict[str, Any]] = []
    for rank, item in enumerate(results, start=1):
        index = int(item.get("index", -1))
        if index < 0 or index >= len(candidates):
            continue
        raw_score = float(item.get("relevance_score") or 0.0)
        candidate = candidates[index]
        base = float(((candidate.get("quality") or {}).get("combined") or 0.0))
        blended = raw_score * 0.7 + base * 0.3
        reranked.append(_annotate_candidate(candidate, "jina", raw_score, blended, rank=rank))
    return reranked


def _build_http_json_request(query: str, candidates: list[dict[str, Any]], config: RerankerConfig, top_n: int) -> tuple[dict[str, str], dict[str, Any]]:
    documents = [_candidate_text(candidate) for candidate in candidates]
    provider = config.provider or "http-json"
    if config.source == "openclaw.plugins.memory-lancedb-pro.retrieval" and provider == "http-json":
        provider = "dashscope"

    if provider == "dashscope":
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        payload = {
            "model": config.model,
            "input": {
                "query": {"text": query},
                "documents": [{"text": text} for text in documents],
            },
            "parameters": {
                "top_n": top_n,
                "return_documents": False,
            },
        }
        return headers, payload

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    payload = {
        "model": config.model,
        "query": query,
        "documents": documents,
        "top_n": top_n,
    }
    return headers, payload


def _parse_http_json_results(response_payload: dict[str, Any]) -> list[dict[str, Any]]:
    for container in [((response_payload.get("output") or {}).get("results")), response_payload.get("results"), response_payload.get("data")]:
        if isinstance(container, list):
            parsed: list[dict[str, Any]] = []
            for item in container:
                if not isinstance(item, dict):
                    continue
                index = int(item.get("index", -1))
                if index < 0:
                    continue
                score_value = item.get("score")
                if score_value is None:
                    score_value = item.get("relevance_score")
                try:
                    score = float(score_value)
                except Exception:
                    continue
                parsed.append({"index": index, "score": score})
            if parsed:
                return parsed
    return []


def _request_http_json_rerank(query: str, candidates: list[dict[str, Any]], config: RerankerConfig, top_n: int | None = None) -> list[dict[str, Any]]:
    if not config.url:
        raise RuntimeError("Reranker URL is not configured")
    request_top_n = top_n or len(candidates)
    headers, payload = _build_http_json_request(query, candidates, config, request_top_n)
    request = urllib.request.Request(
        config.url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP rerank failed: HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"HTTP rerank connection failed: {exc.reason}") from exc

    response_payload = json.loads(body)
    results = _parse_http_json_results(response_payload)
    reranked: list[dict[str, Any]] = []
    provider_name = config.provider or "http-json"
    if config.source == "openclaw.plugins.memory-lancedb-pro.retrieval" and provider_name == "http-json":
        provider_name = "dashscope"
    for rank, item in enumerate(results, start=1):
        index = int(item.get("index", -1))
        if index < 0 or index >= len(candidates):
            continue
        raw_score = float(item.get("score") or 0.0)
        candidate = candidates[index]
        base = float(((candidate.get("quality") or {}).get("combined") or 0.0))
        blended = raw_score * 0.7 + base * 0.3
        reranked.append(_annotate_candidate(candidate, provider_name, raw_score, blended, rank=rank))
    return reranked


def rerank_candidates(query: str, candidates: list[dict[str, Any]], top_n: int | None = None) -> list[dict[str, Any]]:
    config = RerankerConfig.from_env()
    if not candidates:
        return []

    try:
        if config.provider == "jina":
            reranked = _request_jina_rerank(query, candidates, config, top_n=top_n)
            if reranked:
                return reranked
        elif config.provider == "http-json":
            reranked = _request_http_json_rerank(query, candidates, config, top_n=top_n)
            if reranked:
                return reranked
        elif config.provider == "embedding-sim":
            reranked = _embedding_similarity_rerank(query, candidates, top_n=top_n)
            if reranked:
                return reranked
    except Exception:
        pass

    passthrough = [_annotate_candidate(candidate, "stub", 0.0, float(((candidate.get("quality") or {}).get("combined") or 0.0)), rank=index) for index, candidate in enumerate(candidates, start=1)]
    return passthrough[:top_n] if top_n else passthrough
