# Local OpenSearch Setup

Use this guide when you want `deep-search-research` to use a **local OpenSearch backend** for text retrieval or hybrid retrieval.

## What OpenSearch does here

OpenSearch is the **local retrieval backend**, not the original public-web source.
The skill still gathers documents from its source adapters first, then optionally indexes and searches those documents through OpenSearch.

## Required environment variables

```bash
OPENSEARCH_URL=http://localhost:9200
OPENSEARCH_INDEX=deep-search-mvp
OPENSEARCH_VECTOR_DIMS=1024
OPENSEARCH_VERIFY_TLS=true
```

Optional authentication:

```bash
OPENSEARCH_USERNAME=
OPENSEARCH_PASSWORD=
```

## Windows installation example

### 1. Download OpenSearch

Download the Windows zip from the official OpenSearch releases page.

Example release page:
- https://opensearch.org/downloads.html

### 2. Extract it

Extract to a stable local path, for example:

```text
C:\tools\opensearch-2.19.1
```

### 3. Edit `config/opensearch.yml`

For a local single-node install, a minimal configuration is usually enough:

```yaml
cluster.name: deep-search-local
node.name: node-1
network.host: 127.0.0.1
http.port: 9200
discovery.type: single-node
plugins.security.disabled: true
```

> Only disable security for a strictly local development environment.

### 4. Start OpenSearch

From the extracted directory:

```bash
bin\opensearch.bat
```

### 5. Check that it is reachable

```bash
py scripts/check_opensearch_ready.py --url http://localhost:9200
```

Expected healthy diagnosis:

```json
{
  "diagnosis": ["ready"]
}
```

## Mapping generation check

Before a full run, you can test mapping generation only:

```bash
py scripts/opensearch_backend.py --url http://localhost:9200 mapping --output opensearch-mapping.json
```

## Full run with OpenSearch

```bash
py scripts/run_mvp_research.py "研究开源 AI 编码助手生态" --opensearch-url http://localhost:9200 --vector-dims 1024
```

## Expected behavior matrix

### A. No OpenSearch service
- `check_opensearch_ready.py` returns `socket_unreachable`
- `run_mvp_research.py` falls back to the local quality layer

### B. OpenSearch is healthy, but no real embedding provider
- readiness check returns `ready`
- the run uses **OpenSearch text retrieval**
- the report notes that real vector retrieval is not enabled

### C. OpenSearch and a real embedding provider are both ready
- the run can use **hybrid retrieval**
- diagnostics should show vectorized documents

## Matching vector dimensions

`OPENSEARCH_VECTOR_DIMS` must match the actual dimension produced by the embedding model.
Examples:
- stub / small setup: `1024`
- DashScope `qwen3-vl-embedding`: typically `2560`

If dimensions do not match, indexing or vector search may fail, or the client may rewrite the target index name to avoid collisions.

## Troubleshooting

### `socket_unreachable`
OpenSearch is not listening on the expected host/port.
Check:
- process actually started
- `network.host`
- `http.port`
- firewall rules

### `ping_failed`
The TCP port opens, but the HTTP layer is not healthy.
Check the OpenSearch console logs.

### `index_check_failed`
OpenSearch is reachable, but the index operation failed.
Check permissions, index name, and cluster health.

### Hybrid retrieval does not activate
Check:
- real embedding provider is configured
- embedding provider returns the configured dimensions
- `OPENSEARCH_VECTOR_DIMS` matches the embedding output

## Important environment reality check

If `localhost:9200` is unavailable and there is no real local OpenSearch installation, then the blocker is **environment setup**, not the deep-search code path.
