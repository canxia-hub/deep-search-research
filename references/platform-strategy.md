# Deep Search Platform Strategy

## Tier 1: Start Here
优先接入：
- GitHub
- Hacker News
- arXiv
- Semantic Scholar
- Telegram（公开/可访问频道）

策略：
- 官方 API 优先
- 联邦查询优先
- 适合作为 MVP

## Tier 2: Controlled Expansion
后续接入：
- Reddit
- YouTube
- Discord
- B站
- 知乎
- Medium
- Substack

策略：
- 适配器 + 定向索引
- 加强配额与缓存控制
- 评论层与登录态需谨慎

## Tier 3: High Risk / Not for MVP
暂缓：
- X / Twitter
- 小红书
- 抖音
- 微信公众号公开生态

策略：
- 不纳入 MVP
- 若未来接入，必须单独审查 ToS / 风险 / 凭证 / 合规模式

## Routing Guidance
### federated
适合：
- API 友好
- 结构化数据明确
- 低反爬

### indexed
适合：
- 高价值垂直领域
- 可做定时同步
- API / 搜索结果不稳定

### hybrid
适合：
- 平台可查，但单一路径不稳定
- 需要 API + 定向抓取并行

## Risk Guidance
默认：
- compliant 模式优先
- API > 索引 > HTTP > 浏览器
- 禁止默认开启 aggressive 模式