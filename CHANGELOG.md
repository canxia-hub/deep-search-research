# Changelog

All notable changes to this project will be documented in this file.

## 2.0.0 - 2026-10-04

### Added
- Shared quick-web-search v2 research entry with sibling/SEARCH_V2_HOME resolution.
- Agent-led query decomposition, original-page reading, evidence-gap follow-up and cited synthesis.
- Budget/cancel/status contracts and same-question checkpoint resume through the shared core.

### Changed
- Default entry is scripts/research.py; no new model/index service is required.
- Reports are evidence packages, not automatically synthesized final conclusions.
- Legacy MVP/OpenSearch/embedding/rerank scripts are retained but are not the v2 default.
- Portable installation and cross-repository dependency documentation.

## 0.2.0 - 2026-04-20

### Added
- **Research Standards Section**: Integrated commercial-grade research methodology into SKILL.md
  - Task classification guide (quick lookup / current status / entity research / deep research / verification)
  - Time-sensitivity rules with 10% change probability threshold
  - Evidence chain standards with 5-level source classification
  - Source conflict handling procedures with output templates
  - Uncertainty disclosure standards with mandatory disclosure scenarios
  - PDF/chart processing standards requiring visual confirmation
  - Query design standards with rewriting templates
  - Quality verification checklist (correctness, sources, timeliness, boundaries, cost)

- **Templates Directory**: Added reusable templates
  - `templates/uncertainty-disclosure.md` - Uncertainty disclosure template with examples

- **References**: Added comprehensive search norms documentation
  - `references/search-norms.md` - Complete search standards reference

### Improved
- Better source credibility tracking with explicit type labels
- Conflict detection and resolution guidance
- Transparent uncertainty reporting guidelines
- Query optimization with multi-strategy rewriting

### Compatibility
- All changes are additive and backward-compatible
- Standards marked as "recommended" (not enforced) for flexibility

---

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
