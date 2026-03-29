from __future__ import annotations

import hashlib
import html
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_HEADERS = {
    "User-Agent": "OpenClaw-DeepSearchResearch/0.1 (+https://docs.openclaw.ai)",
    "Accept": "application/json, text/html, application/xml;q=0.9, */*;q=0.8",
}

CACHE_DIR = Path(os.getenv("DEEP_SEARCH_CACHE_DIR", str(Path.cwd() / "tmp" / "deep-search-cache")))
REQUEST_INTERVAL_SECONDS = float(os.getenv("DEEP_SEARCH_REQUEST_INTERVAL", "0.6"))
_LAST_REQUEST_TS = 0.0


class RetryableHttpError(RuntimeError):
    pass


def _cache_key(url: str, headers: dict[str, str] | None, suffix: str) -> str:
    raw = json.dumps({"url": url, "headers": headers or {}, "suffix": suffix}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{key}.json"


def _read_cache(key: str, ttl_seconds: int) -> Any | None:
    path = _cache_path(key)
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > ttl_seconds:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _write_cache(key: str, payload: Any) -> None:
    path = _cache_path(key)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _respect_rate_limit() -> None:
    global _LAST_REQUEST_TS
    now = time.time()
    wait_for = REQUEST_INTERVAL_SECONDS - (now - _LAST_REQUEST_TS)
    if wait_for > 0:
        time.sleep(wait_for)
    _LAST_REQUEST_TS = time.time()


def _open_url(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
    allow_insecure_ssl: bool = False,
):
    _respect_rate_limit()
    request = urllib.request.Request(url, headers={**DEFAULT_HEADERS, **(headers or {})})
    context = None
    if allow_insecure_ssl:
        context = ssl._create_unverified_context()  # noqa: SLF001
    return urllib.request.urlopen(request, timeout=timeout, context=context)


def _request_bytes(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
    retries: int = 2,
    backoff_seconds: float = 1.5,
    allow_insecure_ssl: bool = False,
) -> tuple[bytes, str]:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with _open_url(url, headers=headers, timeout=timeout, allow_insecure_ssl=allow_insecure_ssl) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read(), charset
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code in {429, 500, 502, 503, 504} and attempt < retries:
                retry_after = exc.headers.get("Retry-After")
                sleep_for = float(retry_after) if retry_after and retry_after.isdigit() else backoff_seconds * (attempt + 1)
                time.sleep(sleep_for)
                last_error = exc
                continue
            raise RetryableHttpError(f"HTTP Error {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            if attempt < retries:
                time.sleep(backoff_seconds * (attempt + 1))
                last_error = exc
                continue
            raise RetryableHttpError(f"URL Error: {exc.reason}") from exc
        except ssl.SSLError as exc:
            if allow_insecure_ssl and attempt < retries:
                time.sleep(backoff_seconds * (attempt + 1))
                last_error = exc
                continue
            raise RetryableHttpError(f"SSL Error: {exc}") from exc
    raise RetryableHttpError(str(last_error) if last_error else f"Failed to request {url}")


def http_get_json(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
    ttl_seconds: int = 3600,
    retries: int = 2,
    backoff_seconds: float = 1.5,
    allow_insecure_ssl: bool = False,
    bypass_cache: bool = False,
) -> Any:
    cache_key = _cache_key(url, headers, "json")
    if not bypass_cache and ttl_seconds > 0:
        cached = _read_cache(cache_key, ttl_seconds)
        if cached is not None:
            return cached
    raw, _ = _request_bytes(
        url,
        headers=headers,
        timeout=timeout,
        retries=retries,
        backoff_seconds=backoff_seconds,
        allow_insecure_ssl=allow_insecure_ssl,
    )
    payload = json.loads(raw.decode("utf-8"))
    if ttl_seconds > 0:
        _write_cache(cache_key, payload)
    return payload


def http_get_text(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
    ttl_seconds: int = 3600,
    retries: int = 2,
    backoff_seconds: float = 1.5,
    allow_insecure_ssl: bool = False,
    bypass_cache: bool = False,
) -> str:
    cache_key = _cache_key(url, headers, "text")
    if not bypass_cache and ttl_seconds > 0:
        cached = _read_cache(cache_key, ttl_seconds)
        if isinstance(cached, dict) and "text" in cached:
            return cached["text"]
    raw, charset = _request_bytes(
        url,
        headers=headers,
        timeout=timeout,
        retries=retries,
        backoff_seconds=backoff_seconds,
        allow_insecure_ssl=allow_insecure_ssl,
    )
    text = raw.decode(charset, errors="replace")
    if ttl_seconds > 0:
        _write_cache(cache_key, {"text": text})
    return text


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()


def sanitize_extracted_text(text: str, max_length: int = 1200) -> str:
    value = html.unescape(text or "")
    value = re.sub(r"\{[^{}]{400,}\}", " [structured content omitted] ", value, flags=re.DOTALL)
    value = re.sub(r"assistant_response_preferences|user_interaction_metadata|notable_past_conversation_topic_highlights", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", value)
    value = re.sub(r"([{}\[\]\"']){8,}", " ", value)
    value = normalize_whitespace(value)
    if len(value) > max_length:
        value = value[:max_length].rstrip() + "..."
    return value


def strip_html(text: str) -> str:
    return sanitize_extracted_text(re.sub(r"<[^>]+>", " ", text or ""))


def stable_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def canonicalize_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    filtered_query = [(k, v) for k, v in query if not k.lower().startswith("utm_")]
    normalized = parsed._replace(query=urllib.parse.urlencode(filtered_query), fragment="")
    return urllib.parse.urlunparse(normalized)


QUERY_ALIAS_MAP = {
    "开源": "open source",
    "生态": "ecosystem",
    "编码助手": "coding assistant",
    "代码助手": "code assistant",
    "编程助手": "programming assistant",
    "趋势": "trends",
    "争议": "controversies",
    "限制": "limitations",
    "风险": "risks",
    "论文": "research papers",
    "研究": "research",
    "对比": "comparison",
    "主流": "mainstream",
    "产品形态": "product patterns",
}


def rewrite_query_for_open_platform(query: str) -> str:
    from query_understanding import build_platform_query

    return build_platform_query(query, "github")


def keyword_overlap_score(query: str, text: str) -> float:
    query_terms = {token for token in re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", query.lower()) if len(token) > 1}
    text_terms = {token for token in re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", text.lower()) if len(token) > 1}
    if not query_terms:
        return 0.0
    overlap = query_terms & text_terms
    return len(overlap) / max(len(query_terms), 1)
