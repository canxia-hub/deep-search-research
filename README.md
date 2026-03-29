# deep-search-research

A research-oriented OpenClaw skill for **multi-source deep search**, evidence tracking, structured synthesis, and report delivery.

This is not a plain keyword-search skill. It is meant for tasks that need:
- a research plan before searching
- cross-platform evidence gathering
- source normalization and credibility-aware ranking
- structured Markdown/JSON report output

## What this repo contains

- `SKILL.md` — the skill entrypoint
- `scripts/` — the runnable pipeline, adapters, rerank helpers, and OpenSearch helpers
- `references/` — supporting docs for workflow, contracts, routing, scoring, review, and OpenSearch setup
- `.env.example` — portable environment template for embedding / reranker / OpenSearch configuration

## Validated status

This repository contains the stabilized version validated on 2026-03-30 with:
- goal + question joint retrieval
- multi-query source expansion
- question-type-aware planning and review
- authority calibration breakdown
- reusable embedding / reranker provider configuration
- Windows-native OpenSearch route
- OpenSearch text / hybrid retrieval support depending on provider readiness

## Retrieval model

`deep-search-research` currently works in two layers:

1. **Source acquisition layer**
   - GitHub
   - Hacker News
   - arXiv
   - Semantic Scholar

2. **Retrieval enhancement layer**
   - optional **OpenSearch** indexing and search
   - optional real **embedding provider** for vector / hybrid retrieval
   - optional real **reranker** for rerank quality

So OpenSearch is not the original public-web source by itself; it is the local retrieval backend you can enable after documents are collected and indexed.

---

## Quick install for another Agent / workspace

### 1. Copy or clone the skill

Put this repository in an OpenClaw skill directory, for example:

```bash
~/.openclaw/skills/deep-search-research
```

### 2. Install Python dependency

```bash
pip install requests
```

### 3. Prepare environment variables

Start from `.env.example` and export the values you actually use.

If you do nothing else, the skill still works in a degraded mode:
- embedding → `stub`
- reranker → `stub` or `embedding-sim`
- OpenSearch → optional

That means you can run the pipeline first, then add better retrieval quality later.

### 4. Smoke test the pipeline

```bash
py scripts/run_mvp_research.py "研究开源 AI 编码助手生态"
```

### 5. Optional: enable OpenSearch and real semantic providers

See:
- `references/local-opensearch-setup.md`
- `.env.example`

---

## Embedding model configuration

The embedding side supports:
- `stub`
- `openai-compatible`

If environment variables are not set, the skill will also try to reuse embedding settings from:

```text
~/.openclaw/openclaw.json
plugins.entries.memory-lancedb-pro.config.embedding
```

### Minimal stub mode

```bash
DEEP_SEARCH_EMBEDDING_PROVIDER=stub
DEEP_SEARCH_EMBEDDING_DIMENSIONS=1024
```

Use this when you only want the pipeline to run, without real vector semantics.

### Generic OpenAI-compatible embedding endpoint

```bash
DEEP_SEARCH_EMBEDDING_PROVIDER=openai-compatible
DEEP_SEARCH_EMBEDDING_MODEL=text-embedding-3-large
DEEP_SEARCH_EMBEDDING_BASE_URL=https://your-endpoint.example.com/v1
DEEP_SEARCH_EMBEDDING_API_KEY=YOUR_KEY
DEEP_SEARCH_EMBEDDING_DIMENSIONS=3072
DEEP_SEARCH_EMBEDDING_TIMEOUT=30
```

### DashScope / Qwen multimodal embedding example

The repository supports `qwen3-vl-embedding` and related models through a special request path.
Use a non-empty base URL value plus the DashScope API key.

```bash
DEEP_SEARCH_EMBEDDING_PROVIDER=openai-compatible
DEEP_SEARCH_EMBEDDING_MODEL=qwen3-vl-embedding
DEEP_SEARCH_EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
DEEP_SEARCH_EMBEDDING_API_KEY=YOUR_DASHSCOPE_KEY
DEEP_SEARCH_EMBEDDING_DIMENSIONS=2560
DEEP_SEARCH_EMBEDDING_TIMEOUT=30
```

### Important note on dimensions

Set `DEEP_SEARCH_EMBEDDING_DIMENSIONS` to match the actual vector size produced by the model.
OpenSearch index dimensions must match the embedding dimensions.

---

## Reranker configuration

The reranker side supports:
- `stub`
- `jina`
- `http-json`
- `embedding-sim`

If no reranker is configured:
- it falls back to `embedding-sim` if a real embedding provider exists
- otherwise it falls back to `stub`

### Jina hosted reranker example

```bash
DEEP_SEARCH_RERANKER_PROVIDER=jina
DEEP_SEARCH_RERANKER_MODEL=jina-reranker-v2-base-multilingual
DEEP_SEARCH_RERANKER_API_KEY=YOUR_JINA_KEY
DEEP_SEARCH_RERANKER_TIMEOUT=30
```

You may also use:

```bash
JINA_API_KEY=YOUR_JINA_KEY
```

### Generic HTTP JSON reranker example

```bash
DEEP_SEARCH_RERANKER_PROVIDER=http-json
DEEP_SEARCH_RERANKER_MODEL=your-rerank-model
DEEP_SEARCH_RERANKER_URL=https://your-reranker.example.com/v1/rerank
DEEP_SEARCH_RERANKER_API_KEY=YOUR_KEY
DEEP_SEARCH_RERANKER_TIMEOUT=30
```

### DashScope-style HTTP reranker example

If you already have a compatible rerank endpoint, point `DEEP_SEARCH_RERANKER_URL` at it and keep provider as `http-json`:

```bash
DEEP_SEARCH_RERANKER_PROVIDER=http-json
DEEP_SEARCH_RERANKER_MODEL=qwen-reranker-plus
DEEP_SEARCH_RERANKER_URL=https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank
DEEP_SEARCH_RERANKER_API_KEY=YOUR_DASHSCOPE_KEY
DEEP_SEARCH_RERANKER_TIMEOUT=30
```

### Embedding-sim fallback

```bash
DEEP_SEARCH_RERANKER_PROVIDER=embedding-sim
```

This uses query/document embedding similarity instead of an external rerank API.

---

## OpenSearch installation and setup

If you want local retrieval enhancement, install OpenSearch first.

### Required variables

```bash
OPENSEARCH_URL=http://localhost:9200
OPENSEARCH_INDEX=deep-search-mvp
OPENSEARCH_VECTOR_DIMS=1024
OPENSEARCH_VERIFY_TLS=true
```

Optional auth:

```bash
OPENSEARCH_USERNAME=
OPENSEARCH_PASSWORD=
```

### Install and verify

See the step-by-step guide here:
- `references/local-opensearch-setup.md`

### Health check

```bash
py scripts/check_opensearch_ready.py --url http://localhost:9200
```

### Generate mapping JSON

```bash
py scripts/opensearch_backend.py --url http://localhost:9200 mapping --output opensearch-mapping.json
```

### Run with OpenSearch enabled

```bash
py scripts/run_mvp_research.py "研究开源 AI 编码助手生态" --opensearch-url http://localhost:9200 --vector-dims 1024
```

If OpenSearch is reachable but no real embedding provider is configured, the run degrades to **OpenSearch text retrieval**.
If OpenSearch and real embeddings are both ready, the run can use **hybrid retrieval**.

---

## Recommended installation path by maturity

### Level 1 — minimum viable install
- `requests`
- no real embedding
- no real reranker
- no OpenSearch

Result: the pipeline runs with heuristic ranking.

### Level 2 — better ranking
- real embedding provider
- reranker as `embedding-sim` or a real reranker
- OpenSearch optional

Result: better semantic ranking and reranking.

### Level 3 — full local retrieval enhancement
- real embedding provider
- real reranker (optional but recommended)
- OpenSearch installed and healthy

Result: text or hybrid OpenSearch retrieval with better rerank quality.

---

## References worth reading

- `references/workflow.md`
- `references/data-contracts.md`
- `references/platform-strategy.md`
- `references/quality-layer.md`
- `references/review-procedure.md`
- `references/local-opensearch-setup.md`

---

## Practical note for other Agents

If another Agent installs this skill into a different workspace, it should **not** rely on any hard-coded local machine path.
This repository now prefers environment variables first and uses `~/.openclaw/openclaw.json` as the portable fallback path when reusing OpenClaw embedding or rerank settings.
