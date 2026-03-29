# Security Policy

## Supported versions
This repository currently tracks a single active public line:
- `main`

## Reporting a vulnerability
If you discover a security issue:
1. Do **not** open a public issue with live exploit details or secrets.
2. Report the problem privately to the maintainer before public disclosure.
3. Include:
   - affected file(s)
   - reproduction steps
   - impact assessment
   - whether secrets, tokens, local paths, or unsafe defaults are involved

## Scope of review
Security-sensitive areas in this project include:
- provider config discovery (`embedding_stub.py`, `reranker_stub.py`)
- HTTP request construction for embedding / rerank / OpenSearch calls
- public-release sanitization and secret handling
- any future additions that read local config stores or environment variables

## Safe-publication rule
Public releases should never include:
- live API keys or bearer tokens
- local runtime config files such as `openclaw.json`
- local logs, caches, or generated outputs containing sensitive content
