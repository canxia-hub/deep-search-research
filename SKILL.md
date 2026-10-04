---
name: deep-search-research
description: Use for in-depth research, comparisons, multi-source synthesis, evidence-gap investigation, or cited reports across web/news/official materials, technical GitHub sources and Chinese platforms. Shares retrieval/read contracts with quick-web-search.
---
# Deep Search Research v2

路径示例中的<OpenClaw目录>由Agent替换为当前用户实际绝对路径；以本技能所在目录定位脚本，不要求固定账号或系统目录。
自然语言研究由当前Agent完成，不另搭模型服务。统一检索/阅读底座在quick-web-search；本技能新增scripts/research.py薄入口，旧run_mvp_research.py保留为legacy，不将stub当向量能力。

## Agent研究循环（默认总工作预算5分钟）
1. 明确目标、来源、时间与交付；已有上下文可确定的事实先查文件，不反复问人。
2. 拆2-4个可检索子问题，生成保留实体的query variants；跨平台互补、官方与实践材料分别寻找。不机械要求所有问题都有官方社交回证，例如作者自身教程可用原文。
3. 调用research入口，预算300秒。配置/依赖/浏览器降级按quick-web-search；缺登录或验证码透明记为受限，相关人工决策使用OpenClaw ask_user，不把无答案当同意。
4. 读取report.json/documents与原文证据；核验信息时效、正文/摘要/元数据/字幕边界、来源身份、转载独立性、冲突。材料包requires_agent_synthesis=true不意味着事实已综合完成。
5. 发现缺口则在剩余预算内用search/read跟进；不为凑条数无限扩大。预算到或证据足够就停止，保留已取得材料及不足。
6. Agent写最终回答/报告：摘要、逐声明来源、证据边界、冲突、未知项、行动建议。不得把模型概览、搜索标题、未读取全文当正文引文；报告准确优先于篇幅。
7. 需要续跑使用同一问题checkpoint；保存步骤/证据产物至WM。--resume不会启动新Agent，不自动恢复被强制杀进程前未写入的材料。

## Windows入口
~~~powershell
py "<OpenClaw目录>\skills\deep-search-research\scripts\research.py" "AI 视频制作 工作流 教程" --sources wechat,bilibili,xiaohongshu,web --output "<OpenClaw目录>\workspace\outputs\ai-video-research"
py "<OpenClaw目录>\skills\deep-search-research\scripts\research.py" "AI 视频制作 工作流 教程" --resume "<OpenClaw目录>\workspace\outputs\ai-video-research\checkpoint.json" --output "<OpenClaw目录>\workspace\outputs\ai-video-research"
~~~
技术研究可选web,github；queries可由Agent追加英文。明确URL走统一read；batch/health亦可从薄入口传入action。
部署位置可通过SEARCH_V2_HOME覆盖，指向用户拥有的quick-web-search源码/技能根；不下载新的公共实现。

## 产物与完成标准
- report.json：sources/traces/coverage、相关性排序结果、阅读documents/evidence、gaps、research_plan、预算与状态。
- checkpoint.json：同契约续跑；成功正文复用，失败项允许重取。
- report.md：检索证据包，包含逐源链接与证据定位。它不是最终论断，Agent必须完成综合。
- 终态ok/partial/blocked/cancelled按实际数据；缺口不能藏在成功措辞里。
- 默认无真实embedding/rerankAPI，明确词法降级；如后续使用旧可选语义后端，必须实测真provider，而非embedding_stub。
- 免费优先是没有新增搜索/抓取API支出，不意味着当前Agent推理免费。

## 兼容边界
旧研究脚本及其GitHub/HN/arXiv/Semantic Scholar/OpenSearch可选流程保留、不自动运行、不强制安装；RSS继续quick-web-search/rss_fetch.py。新任务默认统一入口，旧脚本未受新预算控制，不对旧入口作30秒/5分钟承诺。
配置、手动登录、HTTP/浏览器回退规则与完整来源契约以quick-web-search/SKILL.md为准。
