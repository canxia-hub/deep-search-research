# Deep Search Research Workflow

## 1. Goal-first
先把用户输入转成研究目标，而不是直接拿关键词去搜。

需要明确：
- 研究目标
- 子问题
- 时间范围
- 优先平台
- 包含/排除域名
- 风险模式
- 交付格式

## 2. Plan before search
先生成研究计划，再执行：
1. 输出研究提纲
2. 标出每个子问题建议的平台与策略
3. 等用户确认或自行在低风险场景直接执行

## 3. Route by source type
### 优先级
1. 官方 API
2. 已建立的专题索引
3. 静态 HTTP 获取
4. 浏览器穿透采集

不要一上来就全站浏览器抓取。

## 4. Normalize early
所有来源尽快转成统一文档结构，避免后续排序和报告阶段持续处理异构结果。

## 5. Search with full context
不要只拿子问题句子直接搜。

### Current rule
检索语境至少应包含：
- `goal`
- `question`
- 题型导向（若有）

### Why
像“这个主题的核心对象、范围与定义是什么？”这种句子本身没有主题锚点，脱离 goal 会把检索直接带偏。

## 6. Expand queries before giving up
当单条 query 结果稀薄时：
- 生成平台定制 query
- 生成英语 alias / product / workflow 等变体
- 必要时回退到 `goal` 级 query 再试一次

不要把“搜不到”过早误判成“没有证据”。

## 7. Rank with evidence in mind
目标不是把最多结果堆出来，而是：
- 结果去重
- 来源归并
- 首发优先
- 可信度明确
- 对比题保留差异性证据

## 8. Deliver a report, not a pile of links
默认交付：
- 执行摘要
- 关键发现
- 证据与引用
- 限制与未覆盖点
- 后续研究问题

## 9. Fail gracefully
如果部分来源失败：
- 明确标注失败来源
- 提供部分可交付结果
- 给出下一轮补充研究建议
- 区分 hard failure 与 soft warning

## 10. Resume when useful
长研究任务要保留 checkpoint，允许：
- 暂停
- 继续
- 调整焦点
- 从既有证据继续深挖
