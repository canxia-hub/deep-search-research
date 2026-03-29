from __future__ import annotations

from typing import Type

from arxiv_adapter import ArxivAdapter
from github_adapter import GitHubAdapter
from hackernews_adapter import HackerNewsAdapter
from semantic_scholar_adapter import SemanticScholarAdapter
from source_adapter import SourceAdapter, SourceCapability

ADAPTER_CLASSES: dict[str, Type[SourceAdapter]] = {
    "github": GitHubAdapter,
    "hackernews": HackerNewsAdapter,
    "arxiv": ArxivAdapter,
    "semantic-scholar": SemanticScholarAdapter,
}


def list_capabilities() -> list[SourceCapability]:
    return [adapter_cls.capability for adapter_cls in ADAPTER_CLASSES.values()]


def get_adapter(platform: str) -> SourceAdapter | None:
    adapter_cls = ADAPTER_CLASSES.get(platform)
    return adapter_cls() if adapter_cls else None


def get_capability(platform: str) -> SourceCapability | None:
    adapter = get_adapter(platform)
    return adapter.capability if adapter else None
