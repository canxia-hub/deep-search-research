from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_STUB_DIMS = 64
OPENCLAW_CONFIG_PATH = Path(os.getenv("OPENCLAW_CONFIG_PATH") or str(Path.home() / ".openclaw" / "openclaw.json"))


@dataclass
class EmbeddingConfig:
    provider: str
    model: str = ""
    base_url: str = ""
    api_key: str = ""
    dimensions: int | None = None
    timeout_seconds: int = 30
    source: str = "env"

    @classmethod
    def from_env(cls) -> "EmbeddingConfig":
        provider = (os.getenv("DEEP_SEARCH_EMBEDDING_PROVIDER") or "").strip().lower()
        model = (os.getenv("DEEP_SEARCH_EMBEDDING_MODEL") or "").strip()
        base_url = (os.getenv("DEEP_SEARCH_EMBEDDING_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "").strip()
        api_key = (os.getenv("DEEP_SEARCH_EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
        dimensions_raw = (os.getenv("DEEP_SEARCH_EMBEDDING_DIMENSIONS") or "").strip()
        dimensions = int(dimensions_raw) if dimensions_raw.isdigit() else None
        timeout_raw = (os.getenv("DEEP_SEARCH_EMBEDDING_TIMEOUT") or "30").strip()
        timeout_seconds = int(timeout_raw) if timeout_raw.isdigit() else 30

        if provider or model or base_url or api_key:
            if not provider:
                provider = "openai-compatible" if model and api_key and base_url else "stub"
            return cls(
                provider=provider,
                model=model,
                base_url=base_url.rstrip("/"),
                api_key=api_key,
                dimensions=dimensions,
                timeout_seconds=timeout_seconds,
                source="env",
            )

        fallback = _load_lancedb_embedding_config()
        if fallback:
            return fallback

        return cls(provider="stub", dimensions=dimensions, timeout_seconds=timeout_seconds, source="stub")

    @property
    def is_real(self) -> bool:
        return self.provider not in {"", "stub", "hash", "deterministic"}


def _load_openclaw_json() -> dict[str, Any]:
    if not OPENCLAW_CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(OPENCLAW_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_lancedb_embedding_config() -> EmbeddingConfig | None:
    payload = _load_openclaw_json()
    embedding = (
        ((payload.get("plugins") or {}).get("entries") or {}).get("memory-lancedb-pro") or {}
    ).get("config", {}).get("embedding", {})
    if not embedding:
        return None

    provider = str(embedding.get("provider") or "").strip().lower()
    model = str(embedding.get("model") or "").strip()
    base_url = str(embedding.get("baseURL") or embedding.get("baseUrl") or "").strip().rstrip("/")
    api_key = str(embedding.get("apiKey") or "").strip()
    dimensions_raw = embedding.get("dimensions")
    try:
        dimensions = int(dimensions_raw) if dimensions_raw is not None else None
    except Exception:
        dimensions = None

    if not provider:
        provider = "openai-compatible" if model and api_key and base_url else "stub"

    return EmbeddingConfig(
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
        dimensions=dimensions,
        timeout_seconds=30,
        source="openclaw.plugins.memory-lancedb-pro.embedding",
    )


def get_embedding_config() -> EmbeddingConfig:
    return EmbeddingConfig.from_env()


def embedding_backend_name() -> str:
    config = get_embedding_config()
    return config.provider or "stub"


def embedding_backend_details() -> dict[str, Any]:
    config = get_embedding_config()
    return {
        "provider": config.provider or "stub",
        "model": config.model,
        "dimensions": config.dimensions,
        "source": config.source,
        "real": config.is_real,
    }


def has_real_embedding_provider() -> bool:
    return get_embedding_config().is_real


def _stub_embedding(text: str, dims: int) -> list[float]:
    digest = hashlib.sha256((text or "").encode("utf-8")).digest()
    values = list(digest) * ((dims // len(digest)) + 1)
    sliced = values[:dims]
    return [round((value / 255.0) * 2 - 1, 6) for value in sliced]


def _request_openai_embeddings(texts: list[str], config: EmbeddingConfig, dims: int | None) -> list[list[float]]:
    if not config.base_url:
        raise RuntimeError("Embedding base URL is not configured")
    if not config.api_key:
        raise RuntimeError("Embedding API key is not configured")
    if not config.model:
        raise RuntimeError("Embedding model is not configured")

    if config.model in {"qwen3-vl-embedding", "qwen-vl-embedding"}:
        endpoint = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding"
        vectors: list[list[float]] = []
        for text in texts:
            payload = {
                "model": config.model,
                "input": {
                    "contents": [{"text": text}],
                },
            }
            request = urllib.request.Request(
                endpoint,
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
                raise RuntimeError(f"Embedding request failed: HTTP {exc.code} {detail}") from exc
            except urllib.error.URLError as exc:
                raise RuntimeError(f"Embedding connection failed: {exc.reason}") from exc

            response_payload = json.loads(body)
            embeddings = (((response_payload.get("output") or {}).get("embeddings")) or [])
            if not embeddings:
                raise RuntimeError(f"Embedding response missing output.embeddings: {body}")
            embedding = embeddings[0].get("embedding") or []
            vectors.append([float(value) for value in embedding])
        return vectors

    payload: dict[str, Any] = {
        "model": config.model,
        "input": texts,
    }
    requested_dims = dims or config.dimensions
    if requested_dims:
        payload["dimensions"] = requested_dims

    request = urllib.request.Request(
        f"{config.base_url}/embeddings",
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
        raise RuntimeError(f"Embedding request failed: HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Embedding connection failed: {exc.reason}") from exc

    response_payload = json.loads(body)
    data = response_payload.get("data") or []
    if len(data) != len(texts):
        raise RuntimeError(f"Embedding response size mismatch: expected {len(texts)}, got {len(data)}")
    vectors: list[list[float]] = []
    for item in sorted(data, key=lambda row: int(row.get("index", 0))):
        embedding = item.get("embedding") or []
        vectors.append([float(value) for value in embedding])
    return vectors


def embed_texts(texts: list[str], dims: int | None = None, require_real_provider: bool = False) -> list[list[float]]:
    config = get_embedding_config()
    if require_real_provider and not config.is_real:
        return []
    if not texts:
        return []

    if config.provider == "openai-compatible":
        try:
            return _request_openai_embeddings(texts, config, dims=dims)
        except Exception:
            if require_real_provider:
                return []

    stub_dims = dims or config.dimensions or DEFAULT_STUB_DIMS
    return [_stub_embedding(text, stub_dims) for text in texts]


def embed_text(text: str, dims: int = DEFAULT_STUB_DIMS, require_real_provider: bool = False) -> list[float]:
    vectors = embed_texts([text], dims=dims, require_real_provider=require_real_provider)
    return vectors[0] if vectors else []


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = sum(a * a for a in left) ** 0.5
    right_norm = sum(b * b for b in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
