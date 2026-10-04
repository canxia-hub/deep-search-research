# Deep Search Research v2 · OpenClaw

当前Agent驱动的多轮研究与证据综合技能；默认通过quick-web-search v2共享检索/正文阅读底座，旧MVP/OpenSearch/语义后端仅为保留的legacy选项。

## 安装

需要同级安装[quick-web-search v2](https://github.com/canxia-hub/quick-web-search)及其requirements.txt中的依赖：

~~~text
skills/
  quick-web-search/
  deep-search-research/
~~~

如底座在其他位置，SEARCH_V2_HOME应指向quick-web-search仓库或技能根目录。本技能不会下载底座、安装服务或自动启用付费模型。

## 使用

用户以自然语言提出研究、比较或带来源报告；Agent负责查询拆解、读取证据、回查缺口与最终综合。CLI示例从本仓库根目录执行，Windows可用py替代python：

~~~shell
python scripts/research.py "AI 视频制作 工作流 教程" --sources wechat,bilibili,xiaohongshu,web --output ./research-output
python scripts/research.py "AI 视频制作 工作流 教程" --resume ./research-output/checkpoint.json --output ./research-output
~~~

默认总工作预算300秒，快速search为30秒工作预算；这是工作上限/目标，不是全负载SLA。平台登录与限流边界、取消/缓存/配置及正文契约以quick-web-search/SKILL.md为准。

## 产物

- report.json：结果、traces、平台覆盖、读取documents/evidence及缺口。
- checkpoint.json：同问题续跑；成功读取可复用，未成功内容仍须回查。
- report.md：检索证据包，不是已经完成事实综合的LLM报告。
- body/pdf_text/transcript/metadata/none分级，逐段定位、时间码与失败状态保持原样。

最终报告由当前Agent写作，区分事实、推断、冲突和未知项；不把摘要、简介、索引线索当全文。

## 兼容与验证范围

scripts/research.py为v2薄入口；旧run_mvp_research.py、OpenSearch与embedding/rerank流程保留、不自动运行、不对旧入口套用新预算。v2默认仅词法排序，不能将旧版历史语义验收当本版本默认能力证明。

2026-10-04已通过真实共享入口与同问题续跑验证；平台代表样本和限制见quick-web-search的[发布验收](https://github.com/canxia-hub/quick-web-search/blob/master/docs/SEARCH-V2-ACCEPTANCE.md)。详情：[SKILL.md](SKILL.md)；版本：[CHANGELOG.md](CHANGELOG.md)。

许可证：MIT（LICENSE）；安全策略：SECURITY.md。历史参考保留在docs/与references/，其中旧流程说明不替代当前v2指引。
