from __future__ import annotations

import urllib.parse
from collections import defaultdict
from typing import Any

from authority_calibration import authority_breakdown, authority_score
from http_utils import keyword_overlap_score
from query_understanding import build_query_profile
from source_adapter import NormalizedDocument

SOURCE_BASE = {
    "official": 0.90,
    "academic": 0.86,
    "newsroom": 0.72,
    "community": 0.60,
    "aggregator": 0.40,
}

HINT_BOOSTS = {
    "official_repo": 0.10,
    "academic_paper": 0.10,
    "citation_indexed": 0.06,
    "github_repo": 0.04,
    "hn_discussion": 0.03,
    "arxiv_preprint": 0.02,
}

DOMAIN_BOOSTS = {
    "github.com": 0.08,
    "arxiv.org": 0.10,
    "semanticscholar.org": 0.08,
    "news.ycombinator.com": 0.03,
}

SUSPICIOUS_PATTERNS = [
    "assistant_response_preferences",
    "user_interaction_metadata",
    "notable_past_conversation_topic_highlights",
    "helpful_user_insights",
]

COMPARISON_TERMS = {
    "对比",
    "比较",
    "vs",
    "versus",
    "comparison",
    "compare",
    "product-comparison",
}

TREND_TERMS = {"trend", "trends", "趋势", "发展", "recent", "latest"}
RISK_TERMS = {"risk", "risks", "controversy", "争议", "风险", "限制", "limitations"}


def domain_of(url: str) -> str:
    return (urllib.parse.urlparse(url).netloc or "").lower()


def credibility_score(doc: NormalizedDocument) -> float:
    domain = domain_of(doc.canonical_url or doc.url)
    score = max(SOURCE_BASE.get(doc.source_type, 0.5), authority_score(domain, doc.source_type, doc.credibility_hints))
    for hint in doc.credibility_hints:
        score += HINT_BOOSTS.get(hint, 0.0)
    score += DOMAIN_BOOSTS.get(domain, 0.0)
    if doc.author:
        score += 0.02
    if doc.published_at:
        score += 0.02
    score += min(sum(v for v in doc.engagement.values() if isinstance(v, (int, float))) / 100000.0, 0.08)
    return max(0.0, min(score, 0.99))


def language_region_fit(goal: str, question: str, doc: NormalizedDocument) -> float:
    profile = build_query_profile(goal + " " + question)
    score = 0.0
    if "zh" in profile.detected_languages and doc.platform in {"zhihu", "bilibili", "xiaohongshu", "douyin"}:
        score += 0.20
    if "en" in doc.language.lower() and doc.platform in {"github", "hackernews", "arxiv", "semantic-scholar"}:
        score += 0.12
    text = f"{doc.title} {doc.snippet} {doc.body}".lower()
    for region_hint in profile.region_hints:
        if region_hint.lower() in text:
            score += 0.05
    return min(score, 0.25)


def suspicious_text_penalty(doc: NormalizedDocument) -> float:
    text = f"{doc.title} {doc.snippet} {doc.body}".lower()
    penalty = 0.0
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern in text:
            penalty += 0.25
    if text.count("{") + text.count("}") > 20:
        penalty += 0.12
    if len(text) > 2000:
        penalty += 0.08
    return min(penalty, 0.7)


def content_completeness_bonus(doc: NormalizedDocument) -> float:
    score = 0.0
    if len((doc.snippet or "").strip()) >= 80:
        score += 0.04
    if len((doc.body or "").strip()) >= 160:
        score += 0.05
    if doc.metadata:
        score += 0.03
    if len(doc.engagement) >= 2:
        score += 0.02
    return min(score, 0.12)


def question_signal_bonus(question: str, doc: NormalizedDocument) -> float:
    question_lc = question.lower()
    text = f"{doc.title} {doc.snippet} {doc.body}".lower()
    bonus = 0.0
    if any(term in question_lc for term in COMPARISON_TERMS):
        if any(term in text for term in ["compare", "comparison", "versus", "vs", "benchmark", "pricing", "feature"]):
            bonus += 0.08
        if doc.source_type in {"official", "academic", "newsroom"}:
            bonus += 0.04
    if any(term in question_lc for term in TREND_TERMS):
        if doc.published_at:
            bonus += 0.04
        if any(term in text for term in ["trend", "latest", "recent", "2024", "2025", "2026"]):
            bonus += 0.04
    if any(term in question_lc for term in RISK_TERMS):
        if any(term in text for term in ["risk", "limitation", "controvers", "trade-off", "constraint"]):
            bonus += 0.06
    return min(bonus, 0.14)


def relevance_score(goal: str, question: str, doc: NormalizedDocument) -> float:
    text = " ".join([doc.title, doc.snippet, doc.body]).strip()
    lexical = keyword_overlap_score(goal + " " + question, text)
    fit = language_region_fit(goal, question, doc)
    penalty = suspicious_text_penalty(doc)
    completeness = content_completeness_bonus(doc)
    signal_bonus = question_signal_bonus(question, doc)
    return max(0.0, lexical + fit + completeness + signal_bonus - penalty)


def combined_score(goal: str, question: str, doc: NormalizedDocument) -> float:
    rel = relevance_score(goal, question, doc)
    cred = credibility_score(doc)
    engagement = min(sum(v for v in doc.engagement.values() if isinstance(v, (int, float))) / 5000.0, 0.12)
    penalty = suspicious_text_penalty(doc)
    return max(0.0, rel * 0.56 + cred * 0.30 + engagement * 0.10 + content_completeness_bonus(doc) * 0.04 - penalty * 0.35)


def source_merge(documents: list[NormalizedDocument], max_per_domain: int = 2) -> list[NormalizedDocument]:
    grouped: dict[str, list[NormalizedDocument]] = defaultdict(list)
    for doc in documents:
        grouped[domain_of(doc.canonical_url or doc.url) or doc.platform].append(doc)
    merged: list[NormalizedDocument] = []
    for _, docs in grouped.items():
        merged.extend(docs[:max_per_domain])
    return merged


def annotate_documents(goal: str, question: str, documents: list[NormalizedDocument]) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for doc in documents:
        rel = relevance_score(goal, question, doc)
        cred = credibility_score(doc)
        combined = combined_score(goal, question, doc)
        fit = language_region_fit(goal, question, doc)
        suspicious = suspicious_text_penalty(doc)
        completeness = content_completeness_bonus(doc)
        signal_bonus = question_signal_bonus(question, doc)
        domain = domain_of(doc.canonical_url or doc.url)
        authority = authority_breakdown(domain, doc.source_type, doc.credibility_hints)
        payload = doc.to_dict()
        payload["quality"] = {
            "relevance": round(rel, 4),
            "credibility": round(cred, 4),
            "combined": round(combined, 4),
            "languageRegionFit": round(fit, 4),
            "suspiciousPenalty": round(suspicious, 4),
            "contentCompleteness": round(completeness, 4),
            "questionSignal": round(signal_bonus, 4),
            "domain": domain,
            "authorityTier": authority.get("tier"),
            "authorityLabel": authority.get("ruleLabel"),
            "authorityBreakdown": authority,
        }
        annotated.append(payload)
    annotated.sort(key=lambda item: item["quality"]["combined"], reverse=True)
    return annotated


def lightweight_rerank(goal: str, question: str, documents: list[NormalizedDocument]) -> list[NormalizedDocument]:
    ranked = sorted(documents, key=lambda doc: combined_score(goal, question, doc), reverse=True)
    filtered = [doc for doc in ranked if combined_score(goal, question, doc) >= 0.18 and suspicious_text_penalty(doc) < 0.45]
    if not filtered:
        filtered = ranked[:2]
    return source_merge(filtered)


def diversify_ranked_documents(documents: list[dict[str, Any]], question_type: str, top_n: int = 5) -> list[dict[str, Any]]:
    if not documents:
        return []
    if question_type not in {"examples", "trend", "product-comparison", "risk"}:
        return documents[:top_n]

    selected: list[dict[str, Any]] = []
    used_domains: set[str] = set()
    used_source_types: set[str] = set()
    remaining = list(documents)

    while remaining and len(selected) < top_n:
        best_index = 0
        best_score = float("-inf")
        for index, doc in enumerate(remaining):
            quality = doc.get("quality") or {}
            domain = str(quality.get("domain") or "")
            source_type = str(doc.get("source_type") or doc.get("sourceType") or "")
            score = float(quality.get("rerankBlended") or quality.get("combined") or 0.0)
            if domain and domain not in used_domains:
                score += 0.18
            if source_type and source_type not in used_source_types:
                score += 0.12
            if question_type == "product-comparison" and source_type in {"official", "academic", "newsroom"}:
                score += 0.08
            if question_type == "trend" and domain in {"news.ycombinator.com", "arxiv.org", "semanticscholar.org"}:
                score += 0.05
            if score > best_score:
                best_score = score
                best_index = index
        chosen = remaining.pop(best_index)
        selected.append(chosen)
        domain = str(((chosen.get("quality") or {}).get("domain")) or "")
        source_type = str(chosen.get("source_type") or chosen.get("sourceType") or "")
        if domain:
            used_domains.add(domain)
        if source_type:
            used_source_types.add(source_type)

    return selected[:top_n]
