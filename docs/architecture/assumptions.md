# 需求理解与关键默认值确认

> ⚠️ **DEPRECATED 本文档已被 `docs/product/PRD.md` 与 `docs/content-provenance-policy.md` 取代。保留仅用于历史追溯。**
> 其中"多市场（外汇/加密/美股）、5m 主图+1h 背景、三 provider 并行、detector 统一 score 输出、Level 1-5 分层、Milestone 0-9 一次性路线"等旧表述均已过时；权威以 PRD、content-provenance-policy、brooks-system-design-implications 为准。
> 本文档的技术栈与"不实盘/不自动交易/不泄露未来"等边界仍有参考价值。

> 本文档用于记录我们对原始需求的解读，以及在与用户确认后锁定的关键默认决策。
> 在正式进入仓库创建之前，请先审阅本文档，确认以下理解准确无误。

## 一、项目定位（来自两份文档的共同结论）

本项目 **不是** 一个自动交易机器人，**也不是** 一个传统回测平台。

它是一个服务于 **长期学习、刻意训练、研究验证、个人认知积累** 的本地价格行为学习平台。

核心原则：**系统帮助我建立认知，而不是取代我的思考。** 系统输出永远以"候选"（candidate）形式呈现，不冒充权威答案。

## 二、用户画像

- 半职业交易员，正在系统学习 Al Brooks 价格行为学，处于初学阶段。
- 具备扎实 Python 编程能力，长期关注 AI / 数据分析 / 自动化工具。
- 交易市场：第一阶段聚焦 **SPY**（美股指数日内语境）；外汇、加密货币后置（Research Extension）。
- 主要周期：**SPY 5 分钟单图为核心决策图**；1小时 / 多周期为 Research Extension。
- 单用户，本地运行。

## 三、第一阶段核心产品能力

1. **历史K线逐根回放训练器** —— 无未来信息、逐根播放、可记录判断与模拟交易。
2. **历史价格行为候选扫描器** —— 从历史数据中扫描符合概念的候选位置，人工复核确认。

## 四、技术栈（已在要求文档中锁定）

- 后端：Python 3.12+、FastAPI、Pydantic、Polars、DuckDB、PyArrow、SQLAlchemy 2、Alembic、SQLite（WAL）、pytest、Ruff、mypy/Pyright、httpx、Typer
- 前端：TypeScript、React、Vite、TradingView Lightweight Charts、TanStack Query、Zustand、React Router、Vitest、React Testing Library、Playwright
- 本地存储：Parquet（行情数据，分区存储）、DuckDB（扫描/统计）、SQLite（事务型应用数据）
- 容器化：Docker Compose（api + web）
- 明确不引入：Redis、Kafka、Celery、Kubernetes、微服务、云数据库

## 五、候选识别器（candidate detector）统一规范

- 每个 detector 必须是独立、可测试、可版本化的模块。
- 输出结构：`detector_id`、`detector_version`、`symbol`、`timeframe`、`event_time`、`knowable_time`、`evidence`、`label`、`parameters`、`data_version`、`rule_source`、`result_type`。
- **支持多 result type**：boolean / categorical / ordinal / continuous / count / evidence_set；**不强制所有 detector 输出 0~1 score**——evidence 与 knowable_at 比 score 更重要，score 仅用于 continuous/ordinal 类。
- **必须区分 `event_time`（实际发生时间）与 `knowable_time`（系统首次可知时间）**，扫描与回放只能在 `knowable_time` 之后显示。
- 所有计算结果必须可在界面中展开查看依据，不得只输出一个神秘分数。
- 学习顺序遵循 PRD 的 Level 0-6（learning_priority）与 automation_priority 两维度区分；H1/H2/L1/L2 属 Brooks 基础路线（依赖 swing/leg/pullback），wedge/climax/always-in 为 Brooks Source + Later（非 Research Extension）。

## 六、AI 边界（已在要求文档中锁定）

- AI 是学习教练/研究助手/编程助手，不是拥有最终决策权的交易员。
- 必须区分：书中定义（Source-grounded）、系统机械近似（System mechanical）、AI解释（Coach interpretation）。
- 知识库不足时必须直说"当前知识库没有足够依据"。
- 不得冒充 Brooks 原意、不得泄露未来行情、不得自动修改已冻结规则、不得自动交易。
- **第一版：只做 AI provider 抽象 + 禁用模式，不实现具体教练功能。** 具体教练功能放到 Milestone 7。

## 七、数据方案

- 采用 provider adapter 架构，业务逻辑不直接依赖某个数据商（抽象保留）。
- **第一阶段唯一正式训练品种为 SPY**；Binance（加密）/Dukascopy（外汇）/Alpaca（美股）等其他 provider 为 Research Extension，不在阶段一并行接入。
- **第一阶段：内置合成演示数据（零配置可跑完整流程）+ 真实数据下载 CLI（可选项）并行。** 核心功能不依赖任何 API 密钥。
- 数据统一 UTC，界面默认显示 Asia/Shanghai。
- 行情数据必须防前视：由服务端权威 replay cursor 保证——API 永不返回 cursor 之后数据；autoscale 只读当前已可见数据；不模拟失忆。
- 每条K线至少含：symbol、asset_class、provider、feed、timeframe、timestamp_open_utc、timestamp_close_utc、open/high/low/close、volume、trade_count、vwap、is_complete、source_timezone、ingestion_time_utc、data_version。

## 八、模拟交易成交规则（第一阶段默认）

- 支持：市价单、限价单、停止单。
- 同一根K线内同时触及止损和目标时，**第一阶段只实现 pessimistic（保守）规则**，保留 optimistic / ambiguous 的接口供后续扩展。
- 必须处理：跳空、滑点、手续费；无法从 OHLC 确定先后顺序时，不偷偷选择有利结果。

## 九、学习路线（Level 1-5）

第一阶段优先实现 Level 1（单根K线）与 Level 2（局部结构）的 detector：

1. bar anatomy（K线实体/影线/比例/多头/空头/doji/趋势K线）
2. inside bar（内包线）
3. outside bar（外包线）
4. trend bar（趋势K线）
5. overlap（与前一根重叠率）
6. consecutive bars（连续同向K线）
7. pivot（摆动高低点）
8. swing
9. breakout（突破）
10. pullback（回调）
11. failed breakout candidate（失败突破候选）

## 十、分阶段交付（对齐 PRD 的 MVP-A/B/C/D → Later）

> 旧版 Milestone 0-9（M0→M9 一次性规划）已被 PRD 的**产品递进**取代，权威见 `docs/product/PRD.md` 第三章。关键顺序：

- **MVP-A Replay Trainer**：SPY 数据、1m→5m 聚合、RTH、20EMA、关键价位、服务端 no-lookahead 回放、Predict First Reveal Later、基础标注、保存/恢复——**此阶段可完全没有复杂 detector**。
- **MVP-B 客观价格事实**：bar anatomy、bull/bear bar、trend bar、doji、inside/outside、ii/iii/ioi、基础 signal bar evidence。
- **MVP-C 结构层**：local extreme、swing、leg、pullback、trend line、channel line、bar counting → 然后 **H1/H2、L1/L2、second entry**。
- **MVP-D Scanner**：批量扫描、candidate review（confirmed/rejected/uncertain）、错题本、blind recheck——仅在 detector 可人工验证后增加。
- **Later**：always-in、wedge、spike and channel、climax、final flag、day type 复杂识别、完整交易管理、复杂成交模拟。

> 知识库 / AI coach / Figure extraction / 三 provider / 1h 多周期 **均不阻塞 MVP-A**，属 Later 或 Research Extension。

## 十一、本次交付方式（已与用户确认）

用户选择：**先做架构文档，确认后再写代码**。

因此本次（本文件之后的动作）先只做 **Milestone 0** 的产品规格与架构文档，并生成仓库目录骨架。
不编写 Milestone 1 的实际代码，待用户审阅架构文档后再进入 Milestone 1。

## 十二、界面与默认产品设置（沿用要求文档）

- 默认界面语言：中文
- 原始书籍语言：英文
- 默认显示时区：Asia/Shanghai
- 数据内部时区：UTC
- 默认核心决策图：**SPY 5m 单图**（1h 为 Research Extension，非默认背景）
- 默认隐藏 detector：开启
- 默认模拟成交歧义策略：pessimistic
- 默认美股时段：常规交易时段
- 默认单用户、本地运行、不启用 AI、不连接交易账户

## 十三、边界（禁止事项，第一阶段）

- 不实盘下单
- 不自动交易
- 不保存券商/交易权限密钥
- 市场数据 API 密钥与交易 API 密钥必须在设计上分离
- 不静默前向填充缺失K线
- 不把 AI 输出直接写成权威标签
  - 不为了演示而伪造真实盈利结果