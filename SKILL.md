---
name: deep-search-research
description: Research-agent workflow for deep multi-source search, platform-aware routing, source normalization, evidence tracking, and structured report delivery. Use when the user asks to perform or build deep research across the web or multiple platforms; when a task needs a research plan before searching; when results must include citations, source credibility, or cross-platform synthesis; or when building/iterating a deep-search skill, adapters, retrieval pipelines, or research reports.
---

# Deep Search Research

## Overview

Use this skill to run or build a **research-style deep search workflow** instead of a plain keyword search. Treat the task as: **goal → plan → route → collect → normalize → rank → synthesize → report**.

Read additional references only when needed:
- For the end-to-end operating flow, read `references/workflow.md`.
- For payload formats and persistent artifacts, read `references/data-contracts.md`.
- For platform tiering and routing strategy, read `references/platform-strategy.md`.
- For current scoring, routing, reranking, and authority-calibration scaffolds, read `references/quality-layer.md`.
- For the finishing review and product-grade acceptance gates, read `references/review-procedure.md`.
- For local OpenSearch bring-up and diagnostics, read `references/local-opensearch-setup.md`.

## Quick start

### When executing a research task
1. Turn the user request into a research goal with explicit scope.
2. Generate a plan before searching.
3. Pick platforms and strategy by risk + access level:
   - `federated` for API-friendly/open sources
   - `indexed` for curated/topic indexes
   - `hybrid` when both are needed
4. Collect from the cheapest reliable path first:
   - API → index → HTTP → browser crawl
5. Normalize early.
6. Rank for evidence quality, not raw volume.
7. Deliver a report, not a pile of links.

### When building or iterating this skill
1. Update the technical contract first.
2. Keep `SKILL.md` lean; move detailed schemas and routing rules into `references/`.
3. Put deterministic helpers in `scripts/` and test them after edits.
4. Do not assume all platforms are equal—route by platform tier and risk mode.

## Workflow decision tree

### 1. Is the user asking for research or for skill development?
- **Research execution**: follow the runtime workflow below.
- **Skill design / implementation**: update contracts, adapters, and report pipeline skeleton first.

### 2. Does the task need a plan?
- **Yes, if multi-step / high-stakes / cross-platform**: generate a plan explicitly.
- **No, if small and obvious**: still create a minimal plan artifact internally.

### 3. Which retrieval path should you use?
- Use **federated** for GitHub / HN / arXiv / Semantic Scholar style sources.
- Use **indexed** for curated or unstable sources.
- Use **hybrid** when platform search alone is insufficient.

## Runtime workflow

### Step 1: Create a plan
Use `scripts/plan_research.py` to generate a deterministic plan skeleton when useful.

Example:
```bash
py scripts/plan_research.py "研究开源 AI 编码助手生态" --mode compliant
```

The generated plan should capture:
- goal
- sub-questions
- platform hints
- strategy per step
- include/exclude domains
- risk mode

### Step 2: Route by platform
Use the platform tiers in `references/platform-strategy.md`.

Default order:
1. Tier 1 open platforms
2. Tier 2 controlled expansion
3. Tier 3 high-risk sources only with explicit need and matching safeguards

### Step 3: Normalize findings
Convert all results into a uniform document shape before ranking or report writing. Use the `NormalizedDocument` contract from `references/data-contracts.md`.

### Step 4: Rank for evidence
Prefer:
- official / primary sources
- academic sources
- high-signal technical sources
- cross-source agreement

Apply:
- dedup
- source merge
- primary-source boosting
- credibility marking

### Step 5: Deliver a structured report
Use `scripts/render_report.py` to render Markdown from structured JSON when you already have synthesized findings.

Example:
```bash
py scripts/render_report.py report.json --output report.md
```

Preferred report behavior:
- `product-comparison` questions should emit a **structured comparison matrix** and a short **dimension-delta summary**.
- `risk` questions should emit a **risk consistency judgment**, a **risk consistency matrix**, and a **claim-lineage style summary** showing support vs. mitigation evidence.
- All major claims should stay source-traceable through citations or structured evidence blocks.

Default report sections:
- 执行摘要
- 关键发现
- 证据与引用
- 限制与边界
- 后续研究问题
- 来源列表

## Guardrails

- Do not treat deep search as unrestricted crawling.
- Prefer API over crawl, and HTTP over full browser automation when possible.
- Do not default to high-risk platforms or aggressive acquisition modes.
- Mark uncertainty explicitly when coverage is partial.
- Preserve source traceability so every major claim can point back to evidence.

## Resources

### scripts/
- `plan_research.py`: generate a deterministic research-plan skeleton.
- `render_report.py`: render Markdown research reports from structured JSON.
- `run_mvp_research.py`: run the current open-platform MVP pipeline end-to-end.
- `opensearch_backend.py`: emit OpenSearch mapping and provide the MVP OpenSearch client integration layer.
- `check_opensearch_ready.py`: probe whether a local OpenSearch endpoint is actually reachable and usable.
- `github_adapter.py`, `hackernews_adapter.py`, `arxiv_adapter.py`, `semantic_scholar_adapter.py`: first-wave platform adapters.
- `adapter_registry.py`, `query_router.py`, `quality_layer.py`: routing and quality-layer core.
- `query_understanding.py`: language/region-aware query understanding and platform-specific query construction.
- `question_classifier.py`, `evidence_clustering.py`: question typing and evidence clustering for report shaping.
- `review_pipeline.py`: finishing review gates for report quality and trustworthiness.
- `embedding_stub.py`, `reranker_stub.py`: semantic-provider abstraction with graceful fallback when real providers are not configured.
- `.env.example`: local configuration template for embedding / reranker / OpenSearch inputs.

### references/
- `workflow.md`: concise runtime workflow and delivery rules.
- `data-contracts.md`: core payload formats for plan, document, evidence, and report.
- `platform-strategy.md`: platform tiering, routing guidance, and risk-aware defaults.

---

## 研究规范（建议采用）

以下规范用于提升研究质量和报告可信度，作为**建议性内容**，可根据任务复杂度选择采用。

### 任务分类指南

在开始研究前，先将任务归入以下模式：

| 模式 | 特征 | 示例 |
|------|------|------|
| **快速事实查询** | 单一问题，最短路径 | 某公司 CEO 是谁？某标准最新版本？ |
| **当前动态查询** | 获取最近变化 | 今天发生了什么？某法规是否更新？ |
| **实体研究** | 围绕实体综合检索 | 某公司产品路线与融资情况 |
| **深度研究** | 多维问题，跨来源验证 | 某行业供给格局、竞争态势 |
| **核查/证伪** | 判断说法是否成立 | 某 API 是否已弃用？某政策是否生效？ |

### 时效性判定规则

凡是**有超过 10% 概率已变化**的信息，必须联网核验：

- 新闻、价格、规则、政策
- 产品规格、版本、优惠
- 人物职位、比赛结果
- 门店、餐馆、旅行信息

#### 时效性判断流程

1. 判断信息类型是否易变
2. 若易变，检查来源时间
3. 若来源时间 > 时效窗口，必须重新搜索
4. 标注信息的时效性边界

### 证据链规范

#### 来源分级

| 级别 | 类型 | 示例 | 可信度 |
|------|------|------|--------|
| 1 | 官方/原始 | 官方公告、法规原文、论文原文、招股书 | 最高 |
| 2 | 权威机构 | 研究机构、专业出版社、监管机构 | 高 |
| 3 | 主流媒体 | 高质量新闻媒体、专业数据库 | 中高 |
| 4 | 二手来源 | 转引、摘要、博客 | 中 |
| 5 | 社交/论坛 | Twitter、Reddit、论坛帖子 | 低（仅作线索） |

#### 证据链要求

| 风险等级 | 来源要求 |
|----------|----------|
| 低风险（普通事实） | ≥1 个高可信来源 |
| 中风险（重要结论） | ≥2 个独立来源，其中 1 个为官方/原始 |
| 高风险（决策依据） | ≥2-3 个来源，必须含原始来源 |

### 来源冲突处理

当不同来源说法不一致时：

#### 处理流程

1. **识别冲突点** — 具体哪个事实有分歧
2. **记录各方说法** — 每个来源分别怎么说
3. **比较来源质量** — 发布时间、类型、可信度
4. **标注不确定** — 暂不能下定论时明确说明

#### 输出模板

```markdown
⚠️ 来源冲突：

**冲突点**：[具体事实]

**来源 A**：[说法]（来源类型，发布时间）
**来源 B**：[说法]（来源类型，发布时间）

**判断**：[可信度分析]
**结论**：目前无法确定 / 倾向于 [来源]
```

### 不确定性披露规范

#### 必须披露的场景

在以下场景必须显式披露不确定：

- 来源冲突
- 仅有单一非官方来源
- 页面不可访问/抽取失败
- 最新信息可能尚未公开
- 结论依赖推断

#### 披露格式

```markdown
⚠️ 不确定性说明：

**不确定点**：[具体内容]
**原因**：[为什么不确定]
**影响范围**：[对结论的影响]
**建议**：[如何进一步核验]
```

### PDF/图表处理规范

#### 原则

- 纯文本能读取时，优先文本抽取
- 图表、扫描件、复杂表格，必须视觉确认
- 不得假设“解析文本已完整代表页面内容”

#### 处理流程

1. 判断 PDF 是否包含图表/表格/图片
2. 若包含，使用 browser 或截图工具确认
3. 对表格数据，优先引用表头、单位、注释
4. 在输出中标注“已视觉确认”

### 查询设计规范

#### 查询改写规则

每次搜索前，将用户问题改写为 2-5 条候选查询：

| 查询类型 | 目的 | 示例 |
|----------|------|------|
| 精确查询 | 完整表达问题 | `current CEO of [company]` |
| 召回查询 | 高信号关键词 | `[company] CEO` |
| 官方查询 | 找官方入口 | `site:[official domain] [company] leadership` |
| 时效查询 | 找最新信息 | `[topic] 2026 update` |
| 交叉查询 | 多维度验证 | `[topic] announcement site:[official domain]` |

#### 查询模板示例

**当前职位/持有人**
- `current CEO of [company]`
- `site:[official domain] [company] leadership`
- `"[role]" "[organization]"`

**新闻/最近动态**
- `[topic] latest news`
- `[topic] [current year] update`
- `[topic] announcement site:[official domain]`

**产品/规格/价格**
- `[product name] official specs`
- `[product name] price official`
- `site:[vendor domain] [product name]`

**技术/API/版本**
- `[feature] official documentation`
- `[product] release notes`
- `[product] deprecation site:[docs domain]`

**法规/标准**
- `[law / standard number] official text`
- `site:[regulator domain] [topic]`
- `[topic] guidance official`

#### 查询拆分规则

遇到复合问题时，先拆子问题。

例如：“比较 A 公司和 B 公司过去一年的产品发布、融资动态和监管风险”

应拆成：
- A 公司产品发布
- B 公司产品发布
- A 公司融资
- B 公司融资
- A 公司监管风险
- B 公司监管风险
- 综合对比与冲突核验

### 深度研究模式

当任务满足以下任一条件时，进入深度研究模式：

- 问题包含多个维度或多个实体
- 需要跨来源综合
- 需要发现最近变化
- 需要比较多个对象
- 需要形成可交付报告

#### 深度研究流程

1. **明确研究目标** — 核心问题、时间范围、地域范围、输出维度
2. **列出子问题** — 每个子问题必须可独立检索与核验
3. **每子问题至少两轮检索** — 广泛发现 → 官方回查/证据加固
4. **构建证据表** — 结论、来源、时间、类型、可信度、冲突
5. **输出综合报告** — 按标准结构输出

### 质量验收清单

#### 正确性
- [ ] 回答了用户真正的问题
- [ ] 时间范围、主体、地区无误
- [ ] 没有把旧闻说成新动态

#### 来源支撑
- [ ] 每个核心结论都有来源
- [ ] 高风险结论有原始来源
- [ ] 没有把社交平台当作唯一依据

#### 时效性
- [ ] 易变信息已联网核验
- [ ] 使用了足够新的来源
- [ ] 当前职位、价格、规则、版本已做最新确认

#### 表达边界
- [ ] 事实、推断、建议分开
- [ ] 冲突来源已说明
- [ ] 证据不足处已明确写出不确定

#### 成本控制
- [ ] 没有无意义重复搜索
- [ ] 先 API 后 crawl，先 HTTP 后 browser
- [ ] 已达到停止条件后未继续扩搜

---

## 与其他技能的协作

| 场景 | 推荐技能 |
|------|----------|
| 快速查证、RSS 监控 | `quick-web-search` |
| 复杂页面、JS-heavy、登录态 | `agent-browser` |
| 难抓取网页、反爬绕过 | `scrapling-plus` |
| 社交平台数据（B站/小红书/Twitter） | `opencli-bridge` |