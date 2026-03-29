# Changelog

All notable changes to this project will be documented in this file.

## 0.1.0 - 2026-03-30
### Added
- Public project packaging for `deep-search-research`
- `README.md`, `docs/FINAL-CHECKLIST.md`, `docs/DEPLOYMENT-NOTES.md`, and `docs/PUBLIC-RELEASE-AUDIT.md`
- OpenSearch readiness probe and Windows-native OpenSearch deployment notes
- Embedding provider abstraction with LanceDB Pro config reuse
- Reranker abstraction with LanceDB Pro / DashScope config reuse
- Quality layer, authority calibration, review pipeline, and evidence clustering

### Improved
- Goal + question joint retrieval
- Multi-query source expansion
- Product-comparison planning and review gates
- OpenSearch hybrid retrieval compatibility on Windows-native OpenSearch (`lucene` k-NN engine)
- Result deduplication and diversity-aware final selection

### Validated
- Windows-native OpenSearch route
- Real embedding provider: `qwen3-vl-embedding` (2560 dims)
- Real reranker: `qwen3-vl-rerank` via DashScope
- End-to-end hybrid retrieval run with `review=pass`
