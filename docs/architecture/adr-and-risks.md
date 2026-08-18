# Price Action Learning Lab · ADR 架构决策记录 与 风险清单

> Milestone 0 架构文档。ADR 记录关键架构决策及其理由；风险清单列出项目风险与缓解措施。
> 已对齐 canonical：`docs/product/PRD.md`、`docs/content-provenance-policy.md`、`docs/architecture/brooks-system-design-implications.md`。

---

## 一、ADR 架构决策记录

### ADR-001：采用前后端分离的 Monorepo
- **状态**：已接受
- **决策**：`apps/api`（Python/FastAPI）+ `apps/web`（TypeScript/React/Vite）+ `data/` + `docs/` + `scripts/` + `docker/`。
- **理由**：Python 负责数据处理/扫描/统计，React+Lightweight Charts 负责专业图表与逐根回放体验，各取所长。
- **后果**：需维护两套构建工具链；但领域边界清晰，可独立测试。

### ADR-002：存储职责分离（Parquet / DuckDB / SQLite）
- **状态**：已接受
- **决策**：行情存 Parquet（分区），扫描/统计用 DuckDB 直接查 Parquet，事务型应用数据（回放/标注/模拟交易/收藏）存 SQLite（WAL）。
- **理由**：Parquet 高效存大容量K线；DuckDB 批量扫描快；SQLite 处理小事务型数据简单可靠。
- **后果**：需同步维护三种存储，但各司其职、符合本地单用户场景。

### ADR-003：数据源采用 provider adapter 模式
- **状态**：已接受
- **决策**：统一 `MarketDataProvider` 协议接口，业务逻辑不直接依赖某数据商。
- **理由**：保留 provider abstraction，符合"未来可增加数据源"的扩展要求。
- **注意（与 canonical 对齐）**：第一阶段唯一正式训练品种为 **SPY**（Brooks Source 语境 + Product Design 项目选择）。其他市场（BTC/crypto、外汇）与"三 provider 同时实现"为 Research Extension，**不在第一阶段并行接入**；但 adapter 抽象本身可保留。
- **后果**：每加一个数据源需实现 adapter，但核心逻辑不受影响。

### ADR-004：detector 统一输出并区分 event_time / knowable_time
- **状态**：已接受（Brooks 体系核心依据）
- **决策**：每个 detector 输出标准 Candidate 结构，含 `event_time`（实际发生）与 `knowable_time`（系统首次可知），且 `knowable_time ≥ event_time`；并支持多 result type（boolean / categorical / ordinal / continuous / count / evidence_set）。
- **对齐**：**不要求**所有 detector 输出 0~1 `score`——`evidence` 与 `knowable_at` 比 score 更重要；score 仅用于 continuous/ordinal 类 result type。
- **理由**：Brooks 明确 swing 需右侧确认、signal bar 先收盘再入场——"何时知道"严格晚于"何时发生"。这是 no-lookahead 的工程根基。
- **后果**：扫描/回放只能在 knowable_time 后显示信号，需专门防前视测试。

### ADR-005：模拟成交默认 pessimistic（保守）
- **状态**：已接受
- **决策**：同一根K线内同时触及止损和目标时，默认按保守规则结算；保留 optimistic / ambiguous 接口。
- **理由**：无法从 OHLC 确定先后顺序时，不得偷偷选择有利结果（需求文档明确要求）。
- **后果**：回测结果偏保守，但诚实。

### ADR-006：AI 采用 provider-neutral 抽象，禁用模式可运行
- **状态**：已接受
- **决策**：AI 功能经统一接口，至少支持禁用 / 本地 OpenAI-compatible / 远程模型 API。
- **理由**：系统不依赖 AI 也能完成核心工作流；AI 是教练非决策者。
- **后果**：AI 相关功能与核心逻辑解耦，可在知识库里程碑（roadmap "Later"，Early 文本提取部分可并行）逐步接入。

### ADR-007：第一版不引入分布式基础设施
- **状态**：已接受
- **决策**：不用 Redis/Kafka/Celery/Kubernetes/微服务/云数据库；扫描用本地进程 + SQLite 任务状态 + 进程池。
- **理由**：单用户本地系统，避免不必要的分布式复杂度。
- **后果**：未来如需扩展再演进，当前保持简单可靠。

### ADR-008：第一阶段核心为 SPY 5 分钟单图；1h 为 Research Extension
- **状态**：已接受（对齐 PRD：单一 5 分钟核心决策图）
- **决策**：第一阶段**唯一核心决策图为 SPY 5 分钟单图**，**不要求用户同时观察 1 小时图**。服务端 no-lookahead 由权威 replay cursor 保证（后端永不返回 cursor 之后数据）。
- **1 小时 / 多周期**：归为 **Research Extension**，移出第一阶段 Must / 成功标准 / 核心验收；只在长期架构中保留。Brooks 原书主张只读 5 分钟单图，**并无"5m+1h 双图同步分析"的 Must 要求**。
- **理由**：忠实 Brooks 单一 5 分钟决策图语境，保证第一件可用产品是 Replay Trainer。
- **后果**：第一阶段回放器不渲染 1h 背景图；1h 相关防前视风险（未完成高周期聚合）整体随 Research Extension 后置。

---

## 二、风险清单

| # | 风险 | 等级 | 缓解措施 |
|---|---|---|---|
| 1 | 前视偏差（未来数据泄露） | 高 | event_time/knowable_time 分离 + 服务端权威 replay cursor + 专项防前视测试；API 永不返回 cursor 之后数据，autoscale 只用已可见数据；detector 只能在 knowable_at 后揭晓，不模拟失忆 |
| 2 | 概念机械近似误导 | 高 | detector 明确标为"候选"，evidence 比 score 重要，支持多 result type（不强制 0~1 score）；rule_source 按来源四层分层（Brooks Source / Mechanical Approximation / Product / Research） |
| 3 | 数据源混用导致质量不一致 | 中 | provider/feed 记录到每行 + manifest + 禁止静默混用不同来源数据 |
| 4 | 缺失/重复/不完整K线处理不当 | 中 | 明确记录、图表可识别、扫描按规则、质量报告展示；禁止静默前向填充 |
| 5 | 项目范围过度膨胀 | 中 | 严格分阶段（MVP-A/B/C/D → Later），每阶段可独立验收，不堆功能 |
| 6 | detector 版本变更导致旧标注不可追溯 | 中 | detector 版本化，保存用户原始判断与 detector 版本，不覆盖原始输出 |
| 7 | AI 输出被误当权威 | 中 | 区分三类内容来源；无依据时直说"当前知识库没有足够依据" |
| 8 | 密钥泄露 | 中 | .env 加载，不入 Git；市场数据密钥与交易密钥分离；不入日志 |
| 9 | 扫描性能不足 | 低 | 用 Polars/DuckDB 批量计算，不用 Python for-loop 逐行处理大量行情 |
| 10 | 时区/夏令时/交易时段错误 | 中 | 统一 UTC 内部，前端按用户时区显示；专项测试夏令时、美股时段、外汇周末 |
| 11 | 高周期K线聚合前视 | 低 | 1h 现为 Research Extension、第一阶段不渲染。第一阶段防前视由服务端权威 cursor 保证；autoscale 只读当前已可见数据 |
| 12 | 单点失败（如 API 密钥缺失、AI 不可用） | 中 | 演示数据兜底；核心功能不依赖 AI；健康检查 |

---

*本文档与 PRD、架构图、领域模型、数据合同、API草案、路线图共同构成 Milestone 0 交付。*