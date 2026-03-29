# Deployment Notes

## 1. Skill runtime
This project is designed as an OpenClaw skill. The canonical skill entry is `SKILL.md`.

## 2. Embedding / reranker reuse
This version can reuse the current LanceDB Pro configuration from OpenClaw's `openclaw.json`:
- embedding: `plugins.entries.memory-lancedb-pro.config.embedding`
- reranker: `plugins.entries.memory-lancedb-pro.config.retrieval`

Validated provider path:
- embedding: DashScope `qwen3-vl-embedding`
- reranker: DashScope `qwen3-vl-rerank`

## 3. OpenSearch route
### Recommended on this host class
For Tencent Cloud CVM / Windows Server machines without nested virtualization:
- do **not** rely on Docker Linux / WSL2
- prefer **Windows-native OpenSearch**

### Important compatibility fixes
To make native OpenSearch work on this machine, the project needed:
- `lucene` k-NN engine instead of default `nmslib`
- hybrid query without `fusion` field
- index rewrite when vector dims / engine mismatch (example: `deep-search-mvp-d2560-lucene`)
- dedupe of OpenSearch hybrid results before rerank/report

## 4. Validation sample
Validated sample target:
- `比较 2024-2026 年主流 deep research 产品形态`

Validated outcome:
- `opensearch_used=true`
- `hybrid=true`
- `review=pass`

## 5. Secrets
This repository intentionally includes only `.env.example` and no live secrets.
