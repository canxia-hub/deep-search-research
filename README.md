# deep-search-research

Productized OpenClaw research-agent skill for multi-step deep search, evidence synthesis, review-gated reporting, and optional OpenSearch hybrid retrieval.

## What this project contains
- OpenClaw skill entry: `SKILL.md`
- Research pipeline scripts: `scripts/`
- Design/usage references: `references/`
- Final packaging docs: `docs/`
- Safe local config template: `.env.example`

## Final status
This repository contains the stabilized version that was validated on 2026-03-30 with:
- goal + question joint retrieval
- multi-query source expansion
- question-type-aware planning and review
- authority calibration breakdown
- LanceDB Pro embedding config reuse (`qwen3-vl-embedding`, 2560 dims)
- LanceDB Pro reranker config reuse (`qwen3-vl-rerank` via DashScope)
- Windows-native OpenSearch route
- OpenSearch hybrid retrieval passing end-to-end validation

## Key scripts
- `scripts/run_mvp_research.py` — end-to-end pipeline
- `scripts/check_opensearch_ready.py` — local OpenSearch readiness probe
- `scripts/opensearch_backend.py` — OpenSearch mapping / client / search integration
- `scripts/embedding_stub.py` — embedding provider abstraction + LanceDB Pro config reuse
- `scripts/reranker_stub.py` — reranker abstraction + LanceDB Pro config reuse
- `scripts/review_pipeline.py` — review gating and diagnostics

## OpenSearch note
On Tencent Cloud CVM / Windows Server environments without nested virtualization, Docker Linux / WSL2 is not a stable route. This version includes a Windows-native OpenSearch path and documents the required adjustments.

See:
- `docs/FINAL-CHECKLIST.md`
- `docs/DEPLOYMENT-NOTES.md`
- `references/local-opensearch-setup.md`
