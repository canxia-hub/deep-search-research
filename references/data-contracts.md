# Deep Search Research Data Contracts

## ResearchGoal
```json
{
  "goal": "研究目标",
  "questions": ["子问题"],
  "platforms": ["github", "arxiv"],
  "includeDomains": [],
  "excludeDomains": [],
  "timeRange": "2y",
  "mode": "compliant",
  "outputFormats": ["markdown", "json"]
}
```

## ResearchPlan
```json
{
  "planId": "plan-001",
  "goal": "...",
  "steps": [
    {
      "id": "step-1",
      "question": "需要回答的问题",
      "strategy": "federated",
      "platformHints": ["github"],
      "priority": "high"
    }
  ]
}
```

## SourceAdapterCapability
```json
{
  "platform": "github",
  "supportsApi": true,
  "supportsSiteSearch": true,
  "supportsBrowserCrawl": false,
  "supportsComments": true,
  "requiresAuth": false,
  "riskLevel": "low",
  "preferredMode": "federated"
}
```

## NormalizedDocument
```json
{
  "docId": "unique-id",
  "platform": "github",
  "sourceType": "official",
  "title": "...",
  "url": "...",
  "canonicalUrl": "...",
  "body": "...",
  "snippet": "...",
  "author": "...",
  "publishedAt": "...",
  "language": "en",
  "engagement": {},
  "credibilityHints": ["official_repo"],
  "contentHash": "..."
}
```

## EvidenceItem
```json
{
  "claim": "某条发现",
  "supportingDocs": ["doc-1", "doc-2"],
  "confidence": 0.82,
  "sourceMix": ["official", "academic"],
  "notes": "交叉验证一致"
}
```

## ResearchReport
```json
{
  "reportId": "report-001",
  "title": "标题",
  "summary": "执行摘要",
  "sections": [
    {
      "title": "章节标题",
      "findings": ["发现 1"],
      "citations": ["doc-1"]
    }
  ],
  "sources": ["doc-1"],
  "limitations": ["未覆盖平台 X"],
  "nextQuestions": ["下一步问题"]
}
```

## Report File Convention
- `*.plan.json` — 研究计划
- `*.findings.json` — 中间发现
- `*.report.md` — Markdown 报告
- `*.report.json` — 结构化报告