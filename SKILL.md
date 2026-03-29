---
name: deep-search-research
description: Research-agent workflow for deep multi-source search, platform-aware routing, source normalization, evidence tracking, and structured report delivery. Use when the user asks to perform or build deep research across the web or multiple platforms; when a task needs a research plan before searching; when results must include citations, source credibility, or cross-platform synthesis; or when building/iterating a deep-search skill, adapters, retrieval pipelines, or research reports.
---

# Deep Search Research

## Overview

Use this skill to run or build a **research-style deep search workflow** instead of a plain keyword search. Treat the task as: **goal → plan → route → collect → normalize → rank → synthesize → report**.

Read additional references only when needed:
- For the end-to-end operating flow, read `references/workflow.md`.
- For payload formats and persistent artifacts, read `references/data-contracts.md`.
- For platform tiering and routing strategy, read `references/platform-strategy.md`.
- For current scoring, routing, reranking, and authority-calibration scaffolds, read `references/quality-layer.md`.
- For the finishing review and product-grade acceptance gates, read `references/review-procedure.md`.
- For local OpenSearch bring-up and diagnostics, read `references/local-opensearch-setup.md`.

## Quick start

### When executing a research task
1. Turn the user request into a research goal with explicit scope.
2. Generate a plan before searching.
3. Pick platforms and strategy by risk + access level:
   - `federated` for API-friendly/open sources
   - `indexed` for curated/topic indexes
   - `hybrid` when both are needed
4. Collect from the cheapest reliable path first:
   - API → index → HTTP → browser crawl
5. Normalize early.
6. Rank for evidence quality, not raw volume.
7. Deliver a report, not a pile of links.

### When building or iterating this skill
1. Update the technical contract first.
2. Keep `SKILL.md` lean; move detailed schemas and routing rules into `references/`.
3. Put deterministic helpers in `scripts/` and test them after edits.
4. Do not assume all platforms are equal—route by platform tier and risk mode.

## Workflow decision tree

### 1. Is the user asking for research or for skill development?
- **Research execution**: follow the runtime workflow below.
- **Skill design / implementation**: update contracts, adapters, and report pipeline skeleton first.

### 2. Does the task need a plan?
- **Yes, if multi-step / high-stakes / cross-platform**: generate a plan explicitly.
- **No, if small and obvious**: still create a minimal plan artifact internally.

### 3. Which retrieval path should you use?
- Use **federated** for GitHub / HN / arXiv / Semantic Scholar style sources.
- Use **indexed** for curated or unstable sources.
- Use **hybrid** when platform search alone is insufficient.

## Runtime workflow

### Step 1: Create a plan
Use `scripts/plan_research.py` to generate a deterministic plan skeleton when useful.

Example:
```bash
py scripts/plan_research.py "研究开源 AI 编码助手生态" --mode compliant
```

The generated plan should capture:
- goal
- sub-questions
- platform hints
- strategy per step
- include/exclude domains
- risk mode

### Step 2: Route by platform
Use the platform tiers in `references/platform-strategy.md`.

Default order:
1. Tier 1 open platforms
2. Tier 2 controlled expansion
3. Tier 3 high-risk sources only with explicit need and matching safeguards

### Step 3: Normalize findings
Convert all results into a uniform document shape before ranking or report writing. Use the `NormalizedDocument` contract from `references/data-contracts.md`.

### Step 4: Rank for evidence
Prefer:
- official / primary sources
- academic sources
- high-signal technical sources
- cross-source agreement

Apply:
- dedup
- source merge
- primary-source boosting
- credibility marking

### Step 5: Deliver a structured report
Use `scripts/render_report.py` to render Markdown from structured JSON when you already have synthesized findings.

Example:
```bash
py scripts/render_report.py report.json --output report.md
```

Default report sections:
- 执行摘要
- 关键发现
- 证据与引用
- 限制与边界
- 后续研究问题
- 来源列表

## Guardrails

- Do not treat deep search as unrestricted crawling.
- Prefer API over crawl, and HTTP over full browser automation when possible.
- Do not default to high-risk platforms or aggressive acquisition modes.
- Mark uncertainty explicitly when coverage is partial.
- Preserve source traceability so every major claim can point back to evidence.

## Resources

### scripts/
- `plan_research.py`: generate a deterministic research-plan skeleton.
- `render_report.py`: render Markdown research reports from structured JSON.
- `run_mvp_research.py`: run the current open-platform MVP pipeline end-to-end.
- `opensearch_backend.py`: emit OpenSearch mapping and provide the MVP OpenSearch client integration layer.
- `check_opensearch_ready.py`: probe whether a local OpenSearch endpoint is actually reachable and usable.
- `github_adapter.py`, `hackernews_adapter.py`, `arxiv_adapter.py`, `semantic_scholar_adapter.py`: first-wave platform adapters.
- `adapter_registry.py`, `query_router.py`, `quality_layer.py`: routing and quality-layer core.
- `query_understanding.py`: language/region-aware query understanding and platform-specific query construction.
- `question_classifier.py`, `evidence_clustering.py`: question typing and evidence clustering for report shaping.
- `review_pipeline.py`: finishing review gates for report quality and trustworthiness.
- `embedding_stub.py`, `reranker_stub.py`: semantic-provider abstraction with graceful fallback when real providers are not configured.
- `.env.example`: local configuration template for embedding / reranker / OpenSearch inputs.

### references/
- `workflow.md`: concise runtime workflow and delivery rules.
- `data-contracts.md`: core payload formats for plan, document, evidence, and report.
- `platform-strategy.md`: platform tiering, routing guidance, and risk-aware defaults.