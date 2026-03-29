# Deep Search Review Procedure

## Goal
在深度搜索技能接近收尾时，不把“生成了报告”误判成“达到了产品级可信度”。

## Review gates v0
1. **Section coverage**：至少一半章节有有效引用
2. **Source volume**：至少 3 个来源
3. **Source diversity**：至少 2 个不同域名
4. **Suspicious content**：高可疑内容不能进入最终交付
5. **Routing trace present**：报告中必须保留 route / diagnostics / limitations

## Decision states
- `pass`
- `needs_review`

## Current implementation
- `review_pipeline.py` 输出 review JSON + Markdown
- `run_mvp_research.py` 会自动生成 `review.json` / `review.md`
- review 结果包含 section-level diagnostics，便于定位到底是 coverage、authority 还是 claim-evidence support 出问题

## Review gates v1
在 v0 基础上进一步要求：
1. **Authority floor**：平均权威/可信度不能过低
2. **Combined quality floor**：平均综合质量分不能过低
3. **Question-type acceptance**：不同题型满足不同最小 coverage / domain diversity 标准
4. **Claim-citation consistency**：有实质性结论的章节不能没有引用
5. **Definition fallback discipline**：定义题必须给出工作定义，并且该定义仍需有最低支持度
6. **Claim-evidence support**：每个章节的有效 bullet 需要和引用文档形成最低支持度，不能只是“看起来像结论”
7. **Product-comparison realism**：对比题优先要求多域名与足够 citations；如果暂时只有 community-heavy 证据但 coverage / support 已达标，则给 warning 而不是直接硬失败

## Section diagnostics
每个章节会输出：
- questionType
- citations
- domains
- sourceTypes
- meanSupport
- supportScores
- flags

这些字段可直接用于调试：
- 是因为 citations 不够？
- 还是 domain diversity 不够？
- 还是 bullet 和 cited docs 根本对不上？
- 还是只是比较题当前证据仍偏 community-heavy？

## Warnings vs Failures
### Hard failure
- coverage 不足
- authority / combined 过低
- claim 与 citation 断裂
- definition fallback 不合规

### Soft warning
- `community_heavy_comparison`
  - 说明比较题已能成文并通过支持度检查
  - 但对比结论暂时主要来自社区与仓库层证据，后续可继续补官方 / 学术 / 更高权威来源

## Future product-level review
后续可再引入：
- contradiction detection
- cross-source agreement scoring
- source authority calibration tables by vertical
- final human-in-the-loop approval hooks
- stricter claim lineage / evidence graph tracing
