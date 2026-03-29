from __future__ import annotations

import json
import re
from pathlib import Path
from statistics import mean
from typing import Any


def _question_type_expectation(section: dict[str, Any]) -> dict[str, Any]:
    question_type = section.get("questionType") or "generic-research"
    if question_type == "definition":
        return {"minCitations": 1, "minBullets": 2, "minSupport": 0.08, "minDomains": 1}
    if question_type == "examples":
        return {"minCitations": 2, "minBullets": 2, "minSupport": 0.10, "minDomains": 2}
    if question_type == "trend":
        return {"minCitations": 2, "minBullets": 2, "minSupport": 0.10, "minDomains": 2}
    if question_type == "risk":
        return {"minCitations": 2, "minBullets": 2, "minSupport": 0.10, "minDomains": 2}
    if question_type == "product-comparison":
        return {"minCitations": 3, "minBullets": 3, "minSupport": 0.10, "minDomains": 2}
    return {"minCitations": 1, "minBullets": 1, "minSupport": 0.08, "minDomains": 1}


def _meaningful_bullets(section: dict[str, Any]) -> list[str]:
    findings = [str(item).strip() for item in (section.get("findings") or [])]
    return [item for item in findings if item and not item.startswith("证据聚类")]


def _claim_citation_mismatch(section: dict[str, Any]) -> bool:
    meaningful_bullets = _meaningful_bullets(section)
    citations = section.get("citations") or []
    return bool(meaningful_bullets and not citations)


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", (text or "").lower()) if len(token) > 1}


def _support_score(claim: str, documents: list[dict[str, Any]]) -> float:
    claim_tokens = _tokenize(claim)
    if not claim_tokens or not documents:
        return 0.0
    best = 0.0
    for doc in documents:
        doc_text = " ".join(
            [
                str(doc.get("title") or ""),
                str(doc.get("snippet") or ""),
                str(doc.get("body") or ""),
            ]
        )
        doc_tokens = _tokenize(doc_text)
        if not doc_tokens:
            continue
        overlap = len(claim_tokens & doc_tokens) / max(len(claim_tokens), 1)
        best = max(best, overlap)
    return best


def _resolve_cited_docs(section: dict[str, Any], item: dict[str, Any], citation_lookup: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    citations = [citation for citation in (section.get("citations") or []) if citation]
    if citations:
        cited = [citation_lookup[citation] for citation in citations if citation in citation_lookup]
        if cited:
            return cited
    top_docs = item.get("topDocs") or []
    return top_docs


def _definition_fallback_ok(section: dict[str, Any], support_scores: list[float]) -> bool:
    if (section.get("questionType") or "") != "definition":
        return True
    bullets = _meaningful_bullets(section)
    has_working_definition = any("工作定义" in bullet or "定义" in bullet for bullet in bullets)
    return has_working_definition and (mean(support_scores) if support_scores else 0.0) >= 0.06


def review_findings(report: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    citation_lookup: dict[str, dict[str, Any]] = {}
    for item in findings:
        for doc in item.get("topDocs", []):
            doc_id = doc.get("doc_id") or doc.get("docId")
            if doc_id and doc_id not in citation_lookup:
                citation_lookup[doc_id] = doc

    total_sections = len(report.get("sections", []))
    nonempty_sections = sum(1 for section in report.get("sections", []) if section.get("citations"))
    total_sources = len(report.get("sources", []))
    unique_domains = len({source.get("url", "").split("/")[2] for source in report.get("sources", []) if isinstance(source, dict) and source.get("url")})
    suspicious_hits = 0
    combined_scores: list[float] = []
    authority_scores: list[float] = []
    question_type_failures: list[str] = []
    claim_citation_failures: list[str] = []
    evidence_support_failures: list[str] = []
    definition_fallback_failures: list[str] = []
    warnings: list[str] = []
    section_details: list[dict[str, Any]] = []

    for item, section in zip(findings, report.get("sections", []), strict=False):
        expectation = _question_type_expectation(section)
        findings_count = len(_meaningful_bullets(section))
        citations_count = len(section.get("citations") or [])
        supporting_docs = _resolve_cited_docs(section, item, citation_lookup)
        support_scores = [_support_score(bullet, supporting_docs) for bullet in _meaningful_bullets(section)]
        mean_support = mean(support_scores) if support_scores else 0.0
        cited_domains = {
            ((doc.get("quality") or {}).get("domain") or "")
            for doc in supporting_docs
            if isinstance(doc, dict)
        }
        cited_domains.discard("")
        cited_types = {str(doc.get("source_type") or doc.get("sourceType") or "") for doc in supporting_docs}
        cited_types.discard("")

        if citations_count < expectation["minCitations"] or findings_count < expectation["minBullets"]:
            question_type_failures.append(f"{section.get('questionType')}:coverage")
        if len(cited_domains) < expectation["minDomains"]:
            question_type_failures.append(f"{section.get('questionType')}:domain-diversity")
        if _claim_citation_mismatch(section):
            claim_citation_failures.append(section.get("title", "untitled-section"))
        if mean_support < expectation["minSupport"]:
            evidence_support_failures.append(section.get("title", "untitled-section"))
        if not _definition_fallback_ok(section, support_scores):
            definition_fallback_failures.append(section.get("title", "untitled-section"))

        section_flags: list[str] = []
        if (section.get("questionType") or "") == "product-comparison" and len(cited_types) < 2:
            if citations_count >= 3 and len(cited_domains) >= 2:
                section_flags.append("community_heavy_comparison")
                warnings.append(section.get("title", "untitled-section") + ":community_heavy_comparison")
            else:
                question_type_failures.append(f"{section.get('questionType')}:source-type-diversity")

        for doc in item.get("topDocs", []):
            quality = doc.get("quality") or {}
            combined_scores.append(float(quality.get("combined", 0)))
            authority_scores.append(float(quality.get("credibility", 0)))
            if quality.get("suspiciousPenalty", 0) >= 0.35:
                suspicious_hits += 1

        section_details.append(
            {
                "title": section.get("title", "untitled-section"),
                "questionType": section.get("questionType") or "generic-research",
                "citations": citations_count,
                "domains": sorted(cited_domains),
                "sourceTypes": sorted(cited_types),
                "meanSupport": round(mean_support, 4),
                "supportScores": [round(score, 4) for score in support_scores],
                "flags": section_flags,
            }
        )

    source_diversity_ok = unique_domains >= 2
    section_coverage_ok = nonempty_sections >= max(1, total_sections // 2)
    source_volume_ok = total_sources >= 3
    suspicious_ok = suspicious_hits == 0
    authority_ok = (mean(authority_scores) if authority_scores else 0.0) >= 0.58
    combined_ok = (mean(combined_scores) if combined_scores else 0.0) >= 0.24
    question_type_ok = len(question_type_failures) == 0
    claim_citation_ok = len(claim_citation_failures) == 0
    evidence_support_ok = len(evidence_support_failures) == 0
    definition_fallback_ok = len(definition_fallback_failures) == 0

    decision = "pass"
    reasons: list[str] = []
    if not source_diversity_ok:
        decision = "needs_review"
        reasons.append("source_diversity_low")
    if not section_coverage_ok:
        decision = "needs_review"
        reasons.append("section_coverage_low")
    if not source_volume_ok:
        decision = "needs_review"
        reasons.append("source_volume_low")
    if not suspicious_ok:
        decision = "needs_review"
        reasons.append("suspicious_content_present")
    if not authority_ok:
        decision = "needs_review"
        reasons.append("authority_floor_low")
    if not combined_ok:
        decision = "needs_review"
        reasons.append("combined_quality_low")
    if not question_type_ok:
        decision = "needs_review"
        reasons.append("question_type_acceptance_failed")
    if not claim_citation_ok:
        decision = "needs_review"
        reasons.append("claim_citation_consistency_failed")
    if not evidence_support_ok:
        decision = "needs_review"
        reasons.append("claim_evidence_support_low")
    if not definition_fallback_ok:
        decision = "needs_review"
        reasons.append("definition_fallback_discipline_failed")

    return {
        "decision": decision,
        "reasons": reasons,
        "checks": {
            "totalSections": total_sections,
            "nonemptySections": nonempty_sections,
            "totalSources": total_sources,
            "uniqueDomains": unique_domains,
            "suspiciousHits": suspicious_hits,
            "avgCombinedScore": round(mean(combined_scores), 4) if combined_scores else 0.0,
            "avgAuthorityScore": round(mean(authority_scores), 4) if authority_scores else 0.0,
            "questionTypeFailures": question_type_failures,
            "claimCitationFailures": claim_citation_failures,
            "evidenceSupportFailures": evidence_support_failures,
            "definitionFallbackFailures": definition_fallback_failures,
            "warnings": warnings,
            "sections": section_details,
        },
    }


def render_review_markdown(review: dict[str, Any]) -> str:
    lines = ["# Deep Search Review", "", f"Decision: **{review.get('decision', 'unknown')}**", ""]
    lines.append("## Checks")
    lines.append("")
    checks = review.get("checks") or {}
    for key, value in checks.items():
        if key == "sections":
            continue
        lines.append(f"- {key}: {value}")
    lines.append("")

    warnings = checks.get("warnings") or []
    if warnings:
        lines.extend(["## Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    section_rows = checks.get("sections") or []
    if section_rows:
        lines.extend(["## Section diagnostics", ""])
        for section in section_rows:
            lines.append(f"### {section.get('title', 'untitled-section')}")
            lines.append(f"- questionType: {section.get('questionType')}")
            lines.append(f"- citations: {section.get('citations')}")
            lines.append(f"- domains: {section.get('domains')}")
            lines.append(f"- sourceTypes: {section.get('sourceTypes')}")
            lines.append(f"- meanSupport: {section.get('meanSupport')}")
            lines.append(f"- supportScores: {section.get('supportScores')}")
            lines.append(f"- flags: {section.get('flags')}")
            lines.append("")

    reasons = review.get("reasons") or []
    if reasons:
        lines.append("## Reasons")
        lines.append("")
        for reason in reasons:
            lines.append(f"- {reason}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_review(review: dict[str, Any], output_json: str, output_md: str) -> None:
    Path(output_json).write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(output_md).write_text(render_review_markdown(review), encoding="utf-8")
