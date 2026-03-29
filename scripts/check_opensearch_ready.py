from __future__ import annotations

import argparse
import json
import os
import socket
from typing import Any
from urllib.parse import urlparse

from opensearch_backend import OpenSearchClient, OpenSearchConfig


def _probe_socket(host: str, port: int, timeout_seconds: float = 3.0) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return {"ok": True, "message": "tcp_connect_ok"}
    except OSError as exc:
        return {"ok": False, "message": str(exc)}


def _health(client: OpenSearchClient) -> dict[str, Any]:
    return client._request("GET", "/_cluster/health")  # noqa: SLF001


def build_result(config: OpenSearchConfig) -> dict[str, Any]:
    parsed = urlparse(config.base_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    socket_probe = _probe_socket(host, port)

    result: dict[str, Any] = {
        "url": config.base_url,
        "host": host,
        "port": port,
        "socket": socket_probe,
        "ping": None,
        "health": None,
        "index": config.index_name,
        "index_exists": None,
        "diagnosis": [],
    }

    if not socket_probe["ok"]:
        result["diagnosis"].append("socket_unreachable")
        return result

    client = OpenSearchClient(config)
    try:
        result["ping"] = client.ping()
    except Exception as exc:  # noqa: BLE001
        result["diagnosis"].append("ping_failed")
        result["ping"] = {"error": str(exc)}
        return result

    try:
        result["health"] = _health(client)
    except Exception as exc:  # noqa: BLE001
        result["diagnosis"].append("health_failed")
        result["health"] = {"error": str(exc)}

    try:
        result["index_exists"] = client.index_exists()
    except Exception as exc:  # noqa: BLE001
        result["diagnosis"].append("index_check_failed")
        result["index_exists"] = {"error": str(exc)}

    if not result["diagnosis"]:
        result["diagnosis"].append("ready")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether a local OpenSearch endpoint is reachable and usable.")
    parser.add_argument("--url", default=os.getenv("OPENSEARCH_URL", "http://localhost:9200"))
    parser.add_argument("--index", default=os.getenv("OPENSEARCH_INDEX", "deep-search-mvp"))
    parser.add_argument("--username", default=os.getenv("OPENSEARCH_USERNAME"))
    parser.add_argument("--password", default=os.getenv("OPENSEARCH_PASSWORD"))
    parser.add_argument("--dims", type=int, default=int(os.getenv("OPENSEARCH_VECTOR_DIMS", "1024")))
    args = parser.parse_args()

    config = OpenSearchConfig(
        base_url=args.url,
        index_name=args.index,
        username=args.username,
        password=args.password,
        vector_dims=args.dims,
    )
    result = build_result(config)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
