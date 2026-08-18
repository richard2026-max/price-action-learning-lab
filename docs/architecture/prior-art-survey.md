# Prior Art Survey · 既有方案调研与选型决策

> **日期**：2026-08-16（Batch 9）
> **问题**：本项目文档设计思路在业界/互联网/GitHub 是否已有成熟项目？是否可以直接 fork 改造？
> **结论**：**无可直接 fork 的整体方案；维持自建薄 MVP-A 路线，组件级复用不变。**

---

## 一、调研范围与代表性项目

| 类别 | 代表 | 结论 |
|---|---|---|
| 商业回放训练 | TradingView Bar Replay、FX Replay、NinjaTrader/Tradovate、Bookmap、Forex Tester | 成熟但只有"回放"；无判断锁定、无学习闭环；闭源、数据不在本地；TV 可滚屏偷看未来 |
| 开源回放训练 | robswc/tradingview-trainer、yash-dk/stocks-trader（Selenium 挂 TV）、OpenCharts（自绘 Canvas） | 小工具级；前者浏览器自动化不可控，后者图表能力弱于 Lightweight Charts |
| 预测游戏 | ChartGame.com（活跃）、Chart Guess、Bulliq、Hedgd | 机制近似 Predict First，但只猜涨跌，无结构化判断、无概念体系、无法复盘 |
| Brooks 专属 | 无开源；商业有 Brooks Trading Course 软件（Sierra Chart）与 Brooks Instinct | Brooks 工具化有人在做且收费，无人开放；TV 社区有 Brooks 风格 pine 脚本可作思路参考 |
| 形态扫描器 | PatternPy、ChartVantage、candlestick-patterns topic | 近似我们的候选识别器，但普遍无 knowable_at（前视污染）、无 provenance 分层、无人工确认闭环 |
| 交易日志 | TradeNote、TradeTally、Deltalytix | 只有盈亏统计，无判断质量/校准/一致性分析，不与回放训练结合 |
| 量化基建 | NautilusTrader、quantreplay、awesome-systematic-trading | 面向算法回测/撮合仿真；理念（确定性回放）可借鉴，引入太重且与"不自动交易"定位相悖 |

## 二、对照本项目核心设计的覆盖核验

| 本项目设计 | 覆盖情况 |
|---|---|
| 服务端权威 no-lookahead cursor | ❌ 全缺（均为前端隐藏/信任客户端） |
| Predict First + 提交锁定 | ❌（预测游戏最接近但无结构化判断与锁定） |
| Brooks 概念 + 四层来源 + 页码级引用 | ❌ |
| knowable_at + evidence 候选识别 | ❌ |
| sealed exam set + 盲测复评 | ❌（无先例） |
| 学习分析（一致性/校准/混淆） | ❌ |
| 本地优先/书籍不出境 | ⭕ 部分（self-hosted journal） |
| 与交易执行解耦 | ⭕ 部分 |

**判断**：本项目定位（学习科学 + 领域知识库 + 防前视构造）在市场上是真实空白。拼装最接近的碎片（OpenCharts + ChartGame 机制 + TradeNote）改造成本高于自建，因为"防前视构造 + 概念溯源"必须从数据层开始内建。

## 三、决策

1. **不自建轮子的部分（组件级复用，即"拿来主义"的正确层级）**：TradingView Lightweight Charts、exchange_calendars、Polars/DuckDB、FastAPI——已在技术栈中。
2. **具体借鉴**：Lightweight Charts issue #1518（bar replay 实现参考，前端里程碑用）；TV 社区 Brooks pine 脚本（MVP-B/C detector 机械定义思路参考，须走 Concept Spec 流程，不直接抄参数）；awesome-systematic-trading 作持续选型清单。
3. **后置评估**：知识库里程碑时评估通用本地 RAG（AnythingLLM/PrivateGPT 类）能否满足结构化引用协议。
4. **过渡期**：Replay Trainer 建成前，用户可用 TradingView Bar Replay 手工练习（注意其可偷看未来、判断无法留存）。

---

*本文件为选型决策记录（ADR 性质），避免未来重复纠结"是否 fork 现成项目"。*
