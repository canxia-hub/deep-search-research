# Deep Search Quality Layer

## Goal
在真实 embedding、reranker 和 OpenSearch 混合检索逐步接入时，把“检索质量层”做成可退化、可替换、可追踪的结构，而不是一组一次性启发式。

## Current Components
- `adapter_registry.py`：统一适配器注册与能力查询
- `query_router.py`：基于 mode + risk + strategy + query-fit 的路由决策；现已改为参考 `goal + question` 联合语境，而不只看子问题句子
- `query_understanding.py`：语言识别、地区提示、平台定制 query 压缩与改写；现支持多 query 变体扩展
- `quality_layer.py`：可信度、相关度、综合分、题型信号、内容完整度、authority breakdown、来源归并
- `embedding_stub.py`：embedding provider 抽象；支持 `openai-compatible` 真实向量接入，未配置时退化为 deterministic stub
- `reranker_stub.py`：reranker 抽象；支持 `jina`、`http-json` 与 `embedding-sim` 语义重排回退
- `opensearch_backend.py`：混合检索 query、向量索引 mapping、bulk index/search helper
- `http_utils.py`：缓存、重试、退避、基础限流、SSL 降级开关
- `run_mvp_research.py`：已接入平台 cooldown、本地质量层、goal+question 联合检索、source expansion、可选 embedding + reranker + OpenSearch 混合检索

## Scoring Strategy v1
### Relevance
- 关键词重叠
- 标题与摘要优先
- 语言 / 地区匹配
- 内容完整度加权
- 题型信号加权（trend / risk / product-comparison 等）

### Credibility
- source_type 基准分
- authority calibration
- credibility_hints 加权
- 作者 / 发布时间 / engagement 轻量加分

### Combined
组合：
- relevance 56%
- credibility 30%
- engagement 10%
- content completeness 4%
- suspicious penalty 反向扣分

## Source Expansion
### Why
只用单条 query 往往会把“定义题 / 对比题”搜偏，因为子问题本身不带足够主题语义。

### Current behavior
- 检索时使用 `goal + question` 联合语境
- 每个平台会生成多条 query 变体，而不是只打一枪
- 当 step 级 query 结果稀薄时，会回退到 `goal` 级 query 再补一轮

### Practical effect
- 定义题不再搜成“这个主题是什么”这种空洞句子
- product-comparison 能更稳定拉到 GitHub / HN / 学术来源的组合

## Authority Calibration v1
authority 现在不只返回单分，而会输出：
- `tier`
- `ruleLabel`
- `tierScore`
- `typeFloor`
- `positiveHintBoost`
- `negativeHintPenalty`
- `score`

这使得后续：
- review 更容易解释为什么一条来源被判高/低权威
- OpenSearch 结果也能保留 authority trace

## Hybrid Retrieval Behavior
### 无真实 embedding provider
- 本地质量层 + 词法排序
- OpenSearch 若可用，则退化为 text retrieval

### 有真实 embedding provider
- 文档与查询会生成真实向量
- OpenSearch 启用 lexical + vector hybrid retrieval
- reranker 可继续叠加在 hybrid 结果之上

## Reranker Behavior
### `embedding-sim`
- 使用真实 embedding 计算 query-doc cosine similarity
- 与本地 quality combined score 融合

### `jina`
- 调用 Jina rerank API
- 返回结果与本地 combined score 融合，保留 provider trace

### `http-json`
- 允许外接自定义 reranker 服务
- 请求体统一为 `{query, documents, top_n, model}`
- 结果期望为 `results[{index, score}]`

## Reliability Notes
- 对开放 API 使用 TTL 缓存，减少重复请求
- 对 429 / 5xx 使用退避重试
- 对连续 429 的平台启用本轮 cooldown
- 对 embedding / reranker / OpenSearch 都保留 graceful fallback，避免单点故障把整轮研究打断

## Future Upgrade Path
1. 接更多真实 embedding provider（而不只 openai-compatible）
2. 接更多 hosted reranker / cross-encoder provider
3. 加入 source agreement / contradiction detection
4. 建立 claim-evidence graph
5. 把 authority calibration 做成垂类表
