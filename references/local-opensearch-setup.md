# Local OpenSearch Setup Notes

## Goal
给 `deep-search-research` 一个明确的本地 OpenSearch 落地路径，并把“服务没起来”和“代码没接好”区分开。

## Required runtime inputs
- `OPENSEARCH_URL`
- `OPENSEARCH_INDEX`
- `OPENSEARCH_VECTOR_DIMS`
- 可选认证：`OPENSEARCH_USERNAME` / `OPENSEARCH_PASSWORD`

## Quick check
### 1) 仅检查服务连通性
```bash
py scripts/check_opensearch_ready.py --url http://localhost:9200
```

输出会分成三层：
- `socket`：TCP 能不能连上
- `ping`：HTTP 根端点能不能通
- `health`：集群健康状态

### 2) 仅检查 mapping 生成是否正常
```bash
py scripts/opensearch_backend.py mapping --output opensearch-mapping.json
```

### 3) 运行研究流水线并让它自动尝试 OpenSearch
```bash
py scripts/run_mvp_research.py "研究目标" --opensearch-url http://localhost:9200
```

## Expected behavior matrix
### A. 没有 OpenSearch 服务
- `check_opensearch_ready.py` 返回 `socket_unreachable`
- `run_mvp_research.py` 自动退回本地质量层，不会因为缺服务直接崩

### B. 有 OpenSearch，但没有真实 embedding provider
- `check_opensearch_ready.py` 应返回 `ready`
- `run_mvp_research.py` 会走 `opensearch-text`
- 报告里 `limitations` 会明确说明尚未启用真实向量检索

### C. OpenSearch + 真实 embedding provider 都已就绪
- `run_mvp_research.py` 会走 `opensearch-hybrid`
- 诊断中可见 `vectorizedDocuments > 0`

## Important environment reality check
如果本机 Docker Linux engine 不可达、`localhost:9200` 连接被拒绝、且系统里没有 Java / OpenSearch 现成本地安装，那么问题是**本机没有可运行的 OpenSearch 服务**，不是 deep-search 代码接不进去。
