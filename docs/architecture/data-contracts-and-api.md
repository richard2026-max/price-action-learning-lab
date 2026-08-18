# Price Action Learning Lab · 数据合同与 API 草案

> Milestone 0 架构文档。定义标准化数据合同、manifest、detector 输出结构，以及 REST API 草案。
> **内容分层遵循 `docs/content-provenance-policy.md`**；本架构文档以 Product / Engineering Design + Market Data Infrastructure 为主，涉及 Brooks 相关概念处标注来源。

## 〇、原始数据逻辑与聚合主线（Product / Engineering Design, MVP）

> **原始数据底层是 1 分钟，5 分钟由 1 分钟聚合而来**；不得把"直接下载 5m、把 1m 完全后置"当作默认路径。

- **第一阶段主线**：`SPY 1m raw → session-aware aggregation → SPY 5m` → 20 EMA / 关键价位 → 服务端 no-lookahead replay。
- **1m 为后台基础**：用于数据质量、5m 聚合、stop/target 顺序解析、MFE/MAE、intrabar 复盘。
- **默认学习界面不显示 1 分钟图**（1m 的 UI 属 Research/Later，不在本数据合同中先行设计）。

### 聚合时区 / Session 规则（session-aware aggregation）

> ⚠️ **不得简单按 UTC 整 5 分钟切桶而忽略交易所 session。** 必须按交易所时区做 session-aware 聚合。

- **时区 / Session 定义（SPY 第一阶段）**：使用 **America/New_York（exchange timezone）**，并正确处理 **DST（夏/冬令时）**。
- **RTH session**：标准盘中时段（SPY 为 09:30–16:00 ET）；每根 5m bar 的 **aggregation anchor 对齐 RTH 开市时间**，而非 UTC 整点。
- **premarket**：盘前时段单独聚合/标注（premarket H/L 为关键价位），不得与 RTH 混合进同一条 5m 连续序列的聚合锚点。
- **half day（提前收盘日）** 与 **holidays（休市日）**：由 `calendar_id` 关联的交易日历驱动，缺市日不得伪造 bar。
- **5m bar aggregation anchor**：以交易所时区开市/分桶对齐；bar 的 `timestamp_open` / `timestamp_close` 记录真实锚定时间。
- **incomplete / missing / duplicate bar 处理**：
  - `is_complete=false` 的未完成 bar 不得前视，也不得作为已收盘数据进入回放；
  - missing bar 必须明确记录（`missing_bar_count`），**禁止静默前向填充**；
  - duplicate bar 必须去重并记录（`duplicate_count`）；
  - 聚合器对 1m→5m 的边界、缺桶、重复桶行为在 manifest 中显式声明并可被质量报告核对。

## 一、数据合同

### 1.1 标准化 K 线（Parquet 行）

每条标准化 K 线至少包含。**所有 `*_utc` 时间戳仅作存储/交换用；聚合与 session 判定以交易所时区（`calendar_id` + `session_definition`）为准，不用 UTC 切桶**：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| instrument_id | str | 是 | 统一仪器 id（如 `SPY`，跨 provider 稳定） |
| symbol | str | 是 | 交易所符号（如 SPY / BTCUSDT） |
| asset_class | str | 是 | equity / crypto / forex |
| provider | str | 是 | binance / dukascopy / alpaca / synthetic |
| feed | str | 是 | 数据订阅/来源标识（如 iex / sip / coinbase-advanced） |
| timeframe | str | 是 | **1m（底层 raw）/ 5m（第一阶聚合核心）**；1h 属 Research，不在第一阶段 |
| timestamp_open_utc | datetime | 是 | K线开盘时间（UTC 存储） |
| timestamp_close_utc | datetime | 是 | K线收盘时间（UTC 存储） |
| open / high / low / close | float | 是 | OHLC |
| volume | float | 否 | 外汇若为 tick volume 必须标注，不得称真实成交量 |
| trade_count | int | 否 | 可空 |
| vwap | float | 否 | 可空 |
| is_complete | bool | 是 | 是否完整K线（未完成不得前视） |
| calendar_id | str | 是 | 交易日历 id（驱动 RTH / premarket / half day / holidays） |
| session_definition | str | 是 | 该 bar 所属 session（rth / premarket / postmarket），由交易所时区判定 |
| source_timezone | str | 是 | 数据源时区 |
| ingestion_time_utc | datetime | 是 | 摄取时间 |
| data_version | str | 是 | 数据版本 |

> 补充数据保真（Data Fidelity）字段见 1.4；该表不承载 broker 层面的合约字段（见 1.5 Instrument Metadata）。

### 1.2 Instrument Metadata（Product, MVP）

> 以 "one tick" 为依据的 detector 必须依赖此元数据；schema 缺失则补足。第一阶段 SPY 必须至少具备：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| instrument_id | str | 是 | 统一仪器 id（跨 provider 稳定） |
| symbol | str | 是 | 交易所符号 |
| provider | str | 是 | 数据提供方 |
| feed | str | 是 | 数据订阅/来源（如 sip / iex） |
| tick_size | float | 是 | 最小价格变动（tick） |
| price_precision | int | 是 | 价格小数精度 |
| tick_value | float | 是 | 每 tick 的货币价值 |
| contract_multiplier | float | 是 | 合约乘数（现货/ETF 为 1） |
| quote_currency | str | 是 | 报价货币（如 USD） |
| calendar_id | str | 是 | 关联交易日历（RTH/half day/holidays/DST） |
| session_definition | str | 是 | RTH/premarket/收盘 session 定义（交易所时区） |
| quote_side | str | 是 | bid / ask / mid / last（报价边语义） |
| feed_consolidated | bool | 是 | 是否合并（consolidated）行情 feed |

### 1.3 数据集 Manifest（每数据集一份）

| 字段 | 说明 |
|---|---|
| provider / feed / feed_consolidated | 数据来源与是否合并 |
| symbols | 品种列表 |
| timeframe | 周期（1m / 5m） |
| start / end | 时间范围（UTC） |
| row_count | K线总数 |
| missing_bar_count | 缺失数 |
| duplicate_count | 重复数 |
| aggregation_rules | 1m→5m 聚合规则（session/anchor/DST/边界处理） |
| checksum | 校验和 |
| generated_at | 生成时间 |
| schema_version | 数据模式版本 |

**规则**：禁止静默前向填充缺失K线；缺失数据必须明确记录、图表可识别、扫描按规则处理、质量报告展示。

### 1.4 Data Fidelity 声明（数据保真）

| 字段 | 说明 |
|---|---|
| provider | 数据提供方 |
| feed | 数据订阅/来源 |
| feed_consolidated | 是否 consolidated / non-consolidated |
| adjustment_mode | 复权模式（split/dividend-adjusted / raw），SPY 需显式声明 |
| quote_trade_semantics | quote/trade 语义（last / bid-ask / trade tape） |
| corporate_action_handling | 拆股/分红/配股等公司行为的处理方式 |
| data_quality_evidence | 数据源/feed 质量证据（文档、交叉核对记录） |

> ⚠️ **若数据源/feed 质量无证据可查，标记 `OPEN QUESTION / DATA FIDELITY BLOCKER`，不得猜测或假定。** 在数据摄取前需逐项补足；未解决项应视为 Milestone 阻塞项并在质量报告中显式列出。

### 1.5 Detector 候选输出结构

```json
{
  "detector_id": "inside_bar",
  "detector_version": "0.1.0",
  "instrument_id": "SPY",
  "symbol": "SPY",
  "timeframe": "5m",
  "event_at": "2025-01-02T09:35:00-05:00",
  "knowable_at": "2025-01-02T09:40:00-05:00",
  "result_type": "boolean",
  "result": true,
  "label": "inside_bar_candidate",
  "evidence": { "prior_high": 500.0, "prior_low": 498.0, "bar_high": 499.5, "bar_low": 498.5 },
  "parameters": {},
  "data_version": "2025.01",
  "rule_source": "mechanical_definition",
  "provenance": "Mechanical Approximation"
}
```

**关键约束**：
- `knowable_at ≥ event_at`（时区为交易所时区）。扫描/回放只在 `knowable_at` 之后显示，不得在 `knowable_at` 前揭晓结果。
- `rule_source` / `provenance` 严格区分来源四层分层（遵循 `docs/content-provenance-policy.md`）：**Brooks Source / Mechanical Approximation / Product·Engineering Design / Research Extension**。
- **`result_type` 支持多类型，不要求所有 detector 输出 0~1 `score`**：`boolean / categorical / ordinal / continuous / count / evidence_set`。示例：inside/outside bar → `boolean`；H2/L2 → `categorical / event`；overlap → `continuous`；breakout strength → `evidence_set`；Signs of Strength → `count`。
- 每个 detector 必有：evidence、rule_source、rule_version、structure_version、input_data_version、input_slice_hash、event_at、knowable_at。

### 1.6 封存考试集 sealed exam set（Product / Learning Design, **Early**）

- **应尽早建立保护机制**（数据被浏览即污染）。
- **服务端强制保护**：普通 replay / Scanner / search 均**不可访问**封存样本；只有经授权的 exam 会话可读取。
- **确定性 stable split**：deterministic seed + stable hash + stratified split；**多年份保留封存样本**，不硬编码单一年份。
- **访问/解封审计**：对每次 exam 访问与解封操作记录审计日志。
- 服务端 API 对 exam 集返回与普通数据隔离，任何普通查询请求不得暴露其内容。

## 二、API 草案（REST，FastAPI）

> 基础路径 `/api/v1`。所有请求/响应经 Pydantic 校验。带认证：单用户本地，第一版可无登录或简单 API key（存于本地配置）。

### 2.1 数据源管理

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /data/providers | 列出可用数据源 |
| GET | /data/symbols | 列出某 provider 的品种 |
| POST | /data/ingest | 触发数据摄取（下载/导入） |
| GET | /data/manifests | 查询数据集 manifest |
| GET | /data/quality | 数据质量报告 |

### 2.2 行情查询

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /bars | 查询K线（symbol/timeframe/start/end） |
| GET | /bars/{symbol}/{timeframe} | 单品种K线 |

### 2.3 回放

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /replay/sessions | 创建回放会话 |
| GET | /replay/sessions/{id} | 获取会话状态 |
| POST | /replay/sessions/{id}/advance | 前进一根（带 no-lookahead） |
| POST | /replay/sessions/{id}/back | 后退一根（仅训练模式） |
| POST | /replay/sessions/{id}/judge | 提交判断（解锁系统候选） |
| POST | /replay/sessions/{id}/save | 保存会话 |
| POST | /replay/sessions/{id}/resume | 恢复会话 |
| POST | /replay/sessions/{id}/random | 随机日（带 seed） |
| POST | /replay/sessions/{id}/trades | 记录模拟交易 |

### 2.4 标注

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /annotations | 创建标注（K线/区间/文本） |
| PUT | /annotations/{id} | 修改标注 |
| GET | /annotations?session= | 查询标注 |
| POST | /annotations/{id}/review | 标记审核状态 |

### 2.5 模拟交易

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /trades | 查询模拟交易 |
| POST | /trades | 创建模拟交易 |
| PUT | /trades/{id}/exit | 记录离场 |
| GET | /trades/{id}/metrics | MFE/MAE/P&L in R |

### 2.6 候选识别器与扫描

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /detectors | 列出已注册 detector |
| GET | /detectors/{id} | 获取 detector 规格 |
| POST | /scan/tasks | 创建扫描任务 |
| GET | /scan/tasks/{id} | 任务状态/进度 |
| GET | /scan/tasks/{id}/candidates | 候选结果 |
| POST | /candidates/{id}/review | 人工确认/拒绝/不确定 |

### 2.7 知识库

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /knowledge/docs | 导入书籍（PDF） |
| GET | /knowledge/docs | 列出已导入文档 |
| GET | /knowledge/search?q= | 全文检索 |
| POST | /knowledge/ask | AI 教练问答（区分三类来源） |

### 2.8 学习统计

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /analytics/behavior | 学习行为统计 |
| GET | /analytics/judgment | 判断质量统计 |
| GET | /analytics/trades | 模拟交易统计 |
| GET | /analytics/report | 周报告 |

### 2.9 健康检查

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /health | 服务健康（含各存储可用性） |

---

## 三、API 设计原则

- 类型优先：Pydantic schema 定义请求/响应。
- 领域逻辑不放在路由：路由只做参数校验与调度，核心逻辑在 services/。
- 时间统一 UTC（后端内部），时区转换由前端按用户偏好显示。
- 错误处理统一：结构化错误响应，含错误码与可读信息。
- 密钥/敏感信息不入日志。

---

*本文档与 PRD、架构图、领域模型、ADR、风险清单、路线图共同构成 Milestone 0 交付。*