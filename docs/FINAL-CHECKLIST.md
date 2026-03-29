# Final Checklist

## Skill completeness
- [x] Query understanding layer
- [x] Platform-aware routing
- [x] Open-platform adapters (GitHub / Hacker News / arXiv / Semantic Scholar)
- [x] Quality layer with authority calibration
- [x] Review pipeline with section-level diagnostics
- [x] Product-comparison handling
- [x] Goal + question joint retrieval
- [x] Multi-query source expansion
- [x] Claim/evidence consistency checks

## Retrieval stack
- [x] Local lexical fallback
- [x] Embedding provider abstraction
- [x] LanceDB Pro embedding config reuse
- [x] Reranker abstraction
- [x] LanceDB Pro reranker config reuse
- [x] OpenSearch backend integration
- [x] Windows-native OpenSearch route
- [x] Hybrid retrieval validated end-to-end

## Validation signals
- [x] Smoke runs produced `review: pass`
- [x] Native OpenSearch run produced `opensearch_used=true`
- [x] Native OpenSearch run produced `hybrid=true`
- [x] Real embedding provider active (`qwen3-vl-embedding`, 2560 dims)
- [x] Real reranker active (`qwen3-vl-rerank` / DashScope)
- [x] Final validation sample reached `review=pass`

## Environment notes
- [x] Nested virtualization limitation documented
- [x] Windows-native OpenSearch route documented
- [x] Safe config template included
