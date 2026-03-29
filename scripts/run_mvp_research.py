from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from adapter_registry import get_adapter
from embedding_stub import embed_text, embed_texts, embedding_backend_details, embedding_backend_name, get_embedding_config, has_real_embedding_provider
from evidence_clustering import build_evidence_clusters
from opensearch_backend import OpenSearchClient, OpenSearchConfig, prepare_document_for_indexing
from plan_research import build_plan
from quality_layer import annotate_documents, diversify_ranked_documents, lightweight_rerank
from query_router import route_plan
from query_understanding import build_platform_query
from question_classifier import classify_question
from render_report import render_markdown
from reranker_stub import rerank_candidates
from review_pipeline import review_findings, write_review
from source_adapter import NormalizedDocument


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
    return text.strip("-")[:50] or "research-run"


def dedupe_documents(documents: list[NormalizedDocument]) -> list[NormalizedDocument]:
    seen: set[str] = set()
    deduped: list[NormalizedDocument] = []
    for doc in documents:
        key = doc.canonical_url or doc.content_hash or doc.doc_id
        if key in seen:
            continue
        seen.add(key)
        deduped.append(doc)
    return deduped


def dedupe_document_payloads(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for doc in documents:
        key = str(doc.get("canonical_url") or doc.get("content_hash") or doc.get("doc_id") or doc.get("docId") or doc.get("index_id") or "")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped.append(doc)
    return deduped


def _reranker_backend(documents: list[dict[str, Any]]) -> str:
    if not documents:
        return "none"
    return str((((documents[0].get("rerank") or {}).get("provider")) or "stub"))


def _quality_sort_key(doc: dict[str, Any]) -> float:
    quality = doc.get("quality") or {}
    return float(quality.get("rerankBlended") or quality.get("combined") or 0.0)


def _embedding_text(doc: NormalizedDocument) -> str:
    topics = " ".join(str(topic) for topic in (doc.metadata or {}).get("topics", []))
    return " ".join(
        part.strip()
        for part in [
            doc.title or "",
            doc.snippet or "",
            doc.body or "",
            doc.author or "",
            topics,
        ]
        if str(part).strip()
    )[:6000]


def run_collection(plan: dict[str, Any], limit_per_platform: int) -> tuple[list[dict[str, Any]], list[NormalizedDocument], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    all_candidates: list[NormalizedDocument] = []
    routing_trace: list[dict[str, Any]] = []
    cooling_platforms: dict[str, str] = {}
    real_embeddings_available = has_real_embedding_provider()

    for step, route in zip(plan.get("steps", []), route_plan(plan), strict=False):
        question = step["question"]
        query = f"{plan['goal']} {question}".strip()
        fallback_queries = [query, plan["goal"]]
        step_docs: list[NormalizedDocument] = []
        errors: list[str] = []
        for platform in route.platforms:
            if platform in cooling_platforms:
                errors.append(f"{platform}: skipped_due_to_cooldown ({cooling_platforms[platform]})")
                continue
            adapter = get_adapter(platform)
            if not adapter:
                continue
            platform_docs: list[NormalizedDocument] = []
            for fallback_query in fallback_queries:
                try:
                    platform_docs.extend(adapter.search(fallback_query, limit=limit_per_platform))
                except Exception as exc:  # noqa: BLE001
                    message = str(exc)
                    errors.append(f"{platform}: {message}")
                    if "429" in message or "Rate exceeded" in message:
                        cooling_platforms[platform] = message
                        break
                if len(platform_docs) >= limit_per_platform:
                    break
            step_docs.extend(platform_docs[:limit_per_platform])

        step_docs = dedupe_documents(step_docs)
        ranked = lightweight_rerank(plan["goal"], question, step_docs)
        question_profile = classify_question(question)
        annotated_top_docs = annotate_documents(plan["goal"], question, ranked[:12])
        annotated_top_docs = rerank_candidates(query, annotated_top_docs, top_n=8)
        annotated_top_docs = diversify_ranked_documents(annotated_top_docs, question_profile.question_type, top_n=5)
        findings.append(
            {
                "step": step,
                "questionProfile": question_profile.to_dict(),
                "candidateCount": len(step_docs),
                "topDocs": annotated_top_docs,
                "clusters": build_evidence_clusters(annotated_top_docs),
                "rankingBackend": "local-quality-layer",
                "rerankerBackend": _reranker_backend(annotated_top_docs),
                "embeddingBackend": embedding_backend_name() if real_embeddings_available else "stub",
                "route": route.to_dict(),
                "coolingPlatforms": dict(cooling_platforms),
                "errors": errors,
            }
        )
        routing_trace.append(route.to_dict())
        all_candidates.extend(step_docs)
    return findings, dedupe_documents(all_candidates), routing_trace


def maybe_build_opensearch_client(url: str | None, index_name: str, dims: int) -> OpenSearchClient | None:
    if not url:
        env_config = OpenSearchConfig.from_env()
        if not env_config:
            return None
        env_config.index_name = index_name or env_config.index_name
        env_config.vector_dims = dims or env_config.vector_dims
        return OpenSearchClient(env_config)
    config = OpenSearchConfig(
        base_url=url,
        index_name=index_name,
        username=os.getenv("OPENSEARCH_USERNAME"),
        password=os.getenv("OPENSEARCH_PASSWORD"),
        vector_dims=dims,
    )
    return OpenSearchClient(config)


def _prepare_index_documents(documents: list[NormalizedDocument]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payloads = [doc.to_dict() for doc in documents]
    real_embeddings_available = has_real_embedding_provider()
    embedding_vectors: list[list[float]] = []
    if documents and real_embeddings_available:
        embedding_vectors = embed_texts([_embedding_text(doc) for doc in documents], require_real_provider=True)
        if len(embedding_vectors) != len(documents):
            embedding_vectors = []

    indexed_documents = [
        prepare_document_for_indexing(payload, embedding=embedding_vectors[index] if embedding_vectors else None)
        for index, payload in enumerate(payloads)
    ]
    vector_dims = len(embedding_vectors[0]) if embedding_vectors else 0
    return indexed_documents, {
        "embeddingBackend": embedding_backend_name() if real_embeddings_available else "stub",
        "vectorizedDocuments": len(embedding_vectors),
        "vectorDims": vector_dims,
    }


def rerank_with_opensearch(
    client: OpenSearchClient,
    plan: dict[str, Any],
    findings: list[dict[str, Any]],
    all_docs: list[NormalizedDocument],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    indexed_documents, index_diagnostics = _prepare_index_documents(all_docs)
    vector_dims = index_diagnostics.get("vectorDims") or client.config.vector_dims
    target_index, existing_dims, existing_engine, rewritten = client.resolve_index_for_vector_dims(vector_dims=vector_dims)
    client.ensure_index(index_name=target_index, vector_dims=vector_dims)
    if indexed_documents:
        client.bulk_index(indexed_documents, index_name=target_index)

    diagnostics: dict[str, Any] = {
        "index": target_index,
        "requestedIndex": client.config.index_name,
        "indexRewritten": rewritten,
        "existingVectorDims": existing_dims,
        "existingVectorEngine": existing_engine,
        "indexedDocuments": len(indexed_documents),
        "embeddingBackend": index_diagnostics.get("embeddingBackend"),
        "vectorizedDocuments": index_diagnostics.get("vectorizedDocuments"),
        "vectorDims": index_diagnostics.get("vectorDims"),
        "perStepHits": [],
    }
    reranked: list[dict[str, Any]] = []
    for item in findings:
        question = item["step"]["question"]
        query = f"{plan['goal']} {question}".strip()
        lexical_query = build_platform_query(query, "semantic-scholar") or query
        query_vector = embed_text(lexical_query, require_real_provider=True)
        response = client.search(lexical_query, size=6, vector=query_vector or None, index_name=target_index)
        docs = dedupe_document_payloads(client.extract_documents(response))
        diagnostics["perStepHits"].append({
            "question": question,
            "hits": len(docs),
            "hybrid": bool(query_vector),
            "lexicalQuery": lexical_query,
        })
        if docs:
            normalized_docs = [NormalizedDocument.from_dict(doc) for doc in docs]
            annotated_docs = annotate_documents(plan["goal"], question, normalized_docs)
            reranked_docs = rerank_candidates(query, annotated_docs, top_n=8)
            reranked_docs = diversify_ranked_documents(reranked_docs, ((item.get("questionProfile") or {}).get("question_type") or "generic-research"), top_n=5)
        else:
            reranked_docs = item["topDocs"]

        reranked.append(
            {
                **item,
                "topDocs": reranked_docs,
                "rankingBackend": "opensearch-hybrid" if query_vector else "opensearch-text",
                "rerankerBackend": _reranker_backend(reranked_docs),
            }
        )
    return reranked, diagnostics


def build_section_bullets(item: dict[str, Any], fallback_docs: list[dict[str, Any]] | None = None) -> tuple[list[str], list[str]]:
    question_type = ((item.get("questionProfile") or {}).get("question_type") or "generic-research")
    top_docs = item.get("topDocs") or []
    clusters = item.get("clusters") or []
    if not top_docs and question_type == "definition" and fallback_docs:
        top_docs = fallback_docs[:2]
        clusters = []
    if not top_docs:
        return ["未获取到足够结果，建议扩大平台或改写子问题。"], []

    citations = [doc.get("doc_id", "") or doc.get("docId", "") for doc in top_docs[:3]]
    if question_type == "definition":
        bullets = [f"定义线索：{doc.get('title', 'Untitled')} — {(doc.get('snippet') or doc.get('body') or '')[:160]}" for doc in top_docs[:3]]
        bullets.append("对象—范围—边界：优先参考定义更清晰、命名更稳定的来源。")
        bullets.append("工作定义：基于当前证据，可将该主题视为围绕共同目标、工作流与能力边界组织起来的一组对象或方法；后续应再用更高权威来源收紧定义。")
    elif question_type == "examples":
        bullets = [f"代表案例：{doc.get('title', 'Untitled')} — {(doc.get('snippet') or doc.get('body') or '')[:160]}" for doc in top_docs[:3]]
        bullets.append("案例集合：优先保留可直接代表该主题的项目、产品或讨论样本。")
    elif question_type == "trend":
        bullets = [f"趋势信号：{doc.get('title', 'Untitled')} — {(doc.get('snippet') or doc.get('body') or '')[:160]}" for doc in top_docs[:3]]
        bullets.append("变化—样本—证据簇：优先展示近两年变化信号及其来源簇。")
    elif question_type == "risk":
        bullets = [f"风险/限制：{doc.get('title', 'Untitled')} — {(doc.get('snippet') or doc.get('body') or '')[:160]}" for doc in top_docs[:3]]
        bullets.append("风险—证据—边界：优先标注风险点、证据出处与适用边界。")
    elif question_type == "product-comparison":
        bullets = [f"对比样本：{doc.get('title', 'Untitled')} — {(doc.get('snippet') or doc.get('body') or '')[:160]}" for doc in top_docs[:3]]
        bullets.append("对比维度：样本来源、工作流、产品定位、可见限制。")
        bullets.append("筛选纪律：优先保留描述差异、边界或基准的样本，减少泛泛目录式结果。")
    else:
        bullets = [f"发现：{doc.get('title', 'Untitled')} — {(doc.get('snippet') or doc.get('body') or '')[:160]}" for doc in top_docs[:3]]

    if clusters:
        cluster_summary = "；".join(f"{cluster.get('sourceType')} / {cluster.get('theme')} x{cluster.get('count')}" for cluster in clusters[:3])
        bullets.append(f"证据聚类：{cluster_summary}")
    return bullets, citations


def synthesize_report(
    plan: dict[str, Any],
    findings: list[dict[str, Any]],
    all_docs: list[NormalizedDocument],
    routing_trace: list[dict[str, Any]],
    opensearch_used: bool,
    opensearch_diagnostics: dict[str, Any] | None,
) -> dict[str, Any]:
    sections: list[dict[str, Any]] = []
    global_fallback_docs: list[dict[str, Any]] = []
    for item in findings:
        global_fallback_docs.extend(item.get("topDocs") or [])
    global_fallback_docs.sort(key=_quality_sort_key, reverse=True)

    for item in findings:
        question = item["step"]["question"]
        bullets, citations = build_section_bullets(item, fallback_docs=global_fallback_docs)
        sections.append({
            "title": question,
            "questionType": ((item.get("questionProfile") or {}).get("question_type") or "generic-research"),
            "findings": bullets,
            "citations": citations,
        })

    source_mix = defaultdict(int)
    for doc in all_docs:
        source_mix[doc.source_type] += 1
    summary = (
        f"围绕“{plan['goal']}”共执行 {len(findings)} 个研究步骤，"
        f"收敛出 {len(all_docs)} 份去重后的候选证据。"
        f"来源构成：" + ("，".join(f"{k} {v} 条" for k, v in sorted(source_mix.items())) or "无")
    )

    limitations = [
        "当前主要覆盖开放平台与公开 API。",
        "高风险平台与登录态来源未纳入本轮自动执行。",
    ]
    if opensearch_used and (opensearch_diagnostics or {}).get("vectorizedDocuments"):
        limitations.append("当前已启用 OpenSearch 混合检索，但 reranker / authority calibration 仍可继续细化。")
    elif opensearch_used:
        limitations.append("当前 OpenSearch 已接入，但因未配置真实 embedding provider，本轮仅启用文本检索。")
    else:
        limitations.append("当前未接入 OpenSearch 实例，排序仍使用本地质量层与启发式回退。")

    report = {
        "reportId": f"report-{slugify(plan['goal'])}",
        "title": f"{plan['goal']} - MVP 研究报告",
        "summary": summary,
        "sections": sections,
        "questionProfiles": [item.get("questionProfile") for item in findings],
        "sources": [
            {
                "id": doc.doc_id,
                "title": doc.title,
                "url": doc.url,
            }
            for doc in all_docs
        ],
        "limitations": limitations,
        "nextQuestions": [
            "是否需要扩展到 Reddit / YouTube / Discord 等第二梯队平台？",
            "是否需要把 authority calibration 做成垂类表？",
            "是否要加入跨会话恢复与研究状态持久化？",
        ],
        "meta": {
            "opensearchUsed": opensearch_used,
            "opensearchDiagnostics": opensearch_diagnostics or {},
            "routingTrace": routing_trace,
            "embeddingBackend": embedding_backend_name() if has_real_embedding_provider() else "stub",
            "embeddingBackendDetails": embedding_backend_details(),
            "rerankerBackends": sorted({_reranker_backend(item.get("topDocs") or []) for item in findings}),
        },
    }
    return report


def write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + os.linesep, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the deep-search-research MVP pipeline against open platforms.")
    parser.add_argument("goal", help="Research goal in natural language")
    parser.add_argument("--mode", default="compliant", choices=["compliant", "standard", "aggressive"])
    parser.add_argument("--limit-per-platform", type=int, default=3)
    parser.add_argument("--output-dir", default=str(Path.cwd() / "tmp" / "deep-search-runs"))
    parser.add_argument("--opensearch-url", default=os.getenv("OPENSEARCH_URL"))
    parser.add_argument("--opensearch-index", default=os.getenv("OPENSEARCH_INDEX", "deep-search-mvp"))
    default_vector_dims = int(os.getenv("OPENSEARCH_VECTOR_DIMS", str(get_embedding_config().dimensions or 1024)))
    parser.add_argument("--vector-dims", type=int, default=default_vector_dims)
    args = parser.parse_args()

    plan = build_plan(args.goal, args.mode, [], [])
    findings, all_docs, routing_trace = run_collection(plan, args.limit_per_platform)

    opensearch_used = False
    opensearch_diagnostics: dict[str, Any] | None = None
    client = maybe_build_opensearch_client(args.opensearch_url, args.opensearch_index, args.vector_dims)
    if client:
        try:
            findings, opensearch_diagnostics = rerank_with_opensearch(client, plan, findings, all_docs)
            opensearch_used = True
        except Exception as exc:  # noqa: BLE001
            opensearch_diagnostics = {"error": str(exc), "index": args.opensearch_index}

    report = synthesize_report(plan, findings, all_docs, routing_trace, opensearch_used, opensearch_diagnostics)

    run_dir = Path(args.output_dir) / slugify(args.goal)
    run_dir.mkdir(parents=True, exist_ok=True)

    plan_path = run_dir / "plan.json"
    findings_path = run_dir / "findings.json"
    report_json_path = run_dir / "report.json"
    report_md_path = run_dir / "report.md"
    review_json_path = run_dir / "review.json"
    review_md_path = run_dir / "review.md"

    write_json(plan_path, plan)
    write_json(findings_path, findings)
    write_json(report_json_path, report)
    report_md_path.write_text(render_markdown(report), encoding="utf-8")
    review = review_findings(report, findings)
    write_review(review, str(review_json_path), str(review_md_path))

    print(
        json.dumps(
            {
                "plan": str(plan_path),
                "findings": str(findings_path),
                "report_json": str(report_json_path),
                "report_md": str(report_md_path),
                "review_json": str(review_json_path),
                "review_md": str(review_md_path),
                "documents": len(all_docs),
                "opensearch_used": opensearch_used,
                "opensearch": opensearch_diagnostics or {},
                "embedding_backend": embedding_backend_name() if has_real_embedding_provider() else "stub",
                "embedding_backend_details": embedding_backend_details(),
                "reranker_backends": sorted({_reranker_backend(item.get('topDocs') or []) for item in findings}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
