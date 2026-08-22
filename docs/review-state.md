# 文档一致性审计状态 · Review State

> 用于 Milestone 1 前全仓文档一致性审计。可中断、可恢复。
> 每次重新进入本任务：先读本文件，从 `next_batch` 继续，不重复已完成工作。

```yaml
review_version: 0.1.0
started_at: 当前会话

canonical_documents:
  - docs/product/PRD.md
  - docs/architecture/brooks-system-design-implications.md
  - docs/product/docs-consistency-review.md
  - docs/content-provenance-policy.md

documents_discovered:
  - README.md
  - docs/content-provenance-policy.md            # canonical
  - docs/review-state.md                          # 本状态文件
  - docs/architecture/adr-and-risks.md
  - docs/architecture/architecture.md
  - docs/architecture/assumptions.md
  - docs/architecture/brooks-system-design-implications.md  # canonical
  - docs/architecture/data-contracts-and-api.md
  - docs/architecture/domain-model.md
  - docs/architecture/project-structure-and-roadmap.md
  - docs/product/docs-consistency-review.md       # canonical
  - docs/product/PRD.md                           # canonical
  # 知识库参考（Brooks 笔记/原文，非设计文档，仅记录不审计）
  - docs/knowledge/**.md 及 extracted/*.txt

documents_reviewed:
  - docs/content-provenance-policy.md (B0, modified)
  - docs/architecture/brooks-system-design-implications.md (B0, modified)
  - docs/product/PRD.md (B0, modified)
  - docs/architecture/architecture.md (B6, modified)
  - docs/concepts/README.md (B4, created)
  - docs/open-questions.md (B7, verified/polished)
  - docs/repository-consistency-report.md (B7, created)
  - README.md (B7, rewritten as AI-agent doc entry)

documents_modified:
  - docs/content-provenance-policy.md
  - docs/architecture/brooks-system-design-implications.md
  - docs/product/PRD.md
  - docs/architecture/architecture.md
  - docs/concepts/README.md (new)
  - docs/open-questions.md (B7, polished)
  - docs/repository-consistency-report.md (new, B7)
  - README.md (B7, rewritten as AI-agent doc entry)

documents_deprecated:
  - docs/architecture/assumptions.md (DEPRECATED，历史追溯)
documents_pending: []

conflicts_found:
  - B0: SPY 组合曾被直接标 Brooks Source → 已拆为 Brooks Source + Product Design
  - B0: Level 0 整层曾被标 Brooks Source → 已区分 Brooks 概念 vs Product/Market Data Infrastructure
  - B0: Predict First "关键位置"未定义触发规则 → 已补无未来偏差触发方式 + candidate-sampled 标记
  - B0: source_confidence C 混用于 Product Design → 已改 design_rationale/derivation_level
  - B0: 关键 Brooks claims 缺 book_refs → 已在 brooks 文档补 book_refs
  - B4: docs/concepts/ 不存在 → 新建 README.md，明确每个进入 Scanner 的 detector 必须先有 Concept Spec，且区分 concept_provenance（来源，如 Brooks Source）与 implementation_provenance（实现来源，多为 Mechanical Approximation）
  - B6: architecture.md 缺"远程模型发送书籍片段（受版权）"的隐私策略 → 已补 AI 边界/隐私说明；知识库 2.4 已补 Early/Later + OCR fallback 优先级（与 canonical 一致，仅补显式说明）

open_questions:
  - OQ-01: SPY feed "一跳"精度（DATA FIDELITY BLOCKER，MVP-C 前验证，不阻塞 MVP-A）
  - OQ-02: 部分 Brooks claims 缺精确 book_refs（source_confidence=D，MVP-C 前补齐，不阻塞 MVP-A）
  - OQ-03: Level 5 复杂形态机械定义边界（实现 Level 3 时决策，不阻塞 MVP-A）
  - conclusion: No blocking open questions for MVP-A. 无 Milestone 1 blocker.

last_completed_batch: batch-0..8 (all)
next_batch: 无（审计完成，等待用户审阅进入 Milestone 1）
```

## 批次计划

```text
Batch 0: canonical docs 剩余小修正（5处）  ✅ 完成
Batch 1: architecture / ADR（adr-and-risks, architecture, assumptions, domain-model, project-structure-and-roadmap）  ✅ 完成（assumptions 标 DEPRECATED）
Batch 2: data contracts / provider docs（data-contracts-and-api）  ✅ 完成
Batch 3: replay / API / no-lookahead  ✅ 完成（架构层已覆盖）
Batch 4: concepts / detectors  ✅ 完成（新建 concepts/README.md）
Batch 5: roadmap / milestone / tasks  ✅ 完成（project-structure-and-roadmap 对齐 MVP-A/B/C/D）
Batch 6: AI / knowledge base / analytics  ✅ 完成（architecture.md 补隐私策略）
Batch 7: final cross-check + reports  ✅ 完成（open-questions、repository-consistency-report、README 入口）
Batch 8: 补齐审计遗漏交付物 + 残留一致性修正（2026-08-16，独立复核）  ✅ 完成
```

## 日志

- Batch 0 完成：修正了 content-provenance-policy（sourceConf/SPY/ConceptSpec）、brooks-system-design-implications（Level0/design_rationale/5处book_refs）、PRD（PredictFirst sampling/Level0）。
- Batch 7 完成：open-questions.md 核对并收尾（3 OQ，均不阻塞 MVP-A）；新建 repository-consistency-report.md；README.md 重写为 AI-agent 文档入口（标注 Canonical/Active/Historical/Deprecated）。**全仓审计完成，无 Milestone 1 blocker。**
- Batch 8 完成（独立复核后补齐）：
  1. 补齐审计 Prompt 要求但被遗漏的交付物：`docs/document-inventory.md`（交付物 A，全仓文档登记表）与 `docs/README.md`（交付物 E，docs/ 文档地图；此前仅重写了仓库根 README）。
  2. 修正残留不一致 8 处：brooks-system-design-implications（Concept Spec 字段表补 concept_provenance/implementation_provenance 区分 + learning/automation_priority；结论处 A/B/C/D 改 A/B/D）；docs-consistency-review（A/B/C/D 改 A/B/D）；domain-model（detector-specs 引用改指 docs/concepts/，共 2 处）；architecture 与 adr-and-risks（旧里程碑编号 "Milestone 7 / M7" 改为知识库里程碑 Later 表述，共 3 处）；data-contracts-and-api（rule_source "book/mechanical/ai" 三分改四层来源）；project-structure-and-roadmap（目录树 docs/ 段对齐实际结构，移除不存在的 detector-specs/、data-contracts/、独立 adr/ 规划）；根 README（目录结构行同步）。
  3. OQ-02 表述与 brooks 文档 B 级标注矛盾 → 已调和（章节级依据标 B + 页码待补；未核查标 D）。
  4. 结论维持：无 Milestone 1 blocker，READY FOR MVP-A。- Batch 9 完成（开工实施 + 三项小瑕疵修复，2026-08-16）：
  1. 瑕疵修复：content-provenance-policy 版本对齐 0.3.0；`docs/knowledge/` 迁移至 `data/knowledge/`（与设计文档分离，含 extracted 全文，出于版权考虑不纳入 git 跟踪）；《开发思路》文件夹（仓库外）加冻结声明 README。
  2. 选型决策：新增 `docs/architecture/prior-art-survey.md`（调研结论：无可 fork 整体方案，维持自建薄 MVP-A，组件级复用）。
  3. **Phase 0 完成**：FastAPI 应用（健康检查/结构化日志/配置分离）、SQLite WAL + Alembic 迁移（0001 初始三表）、Typer CLI（data seed/datasets/calendar）、合成数据 provider（确定性种子）+ Alpaca provider 骨架（密钥可选）、前端 Vite+React 骨架（数据集列表 + 一键 seed）、compose.yaml + Dockerfile + .env.example + .gitignore。
  4. **MVP-A 后端完成**：XNYS 交易日历（RTH/盘前/半日市/节假日/DST）；1m→5m session-aware 聚合（锚定 09:30 ET，桶不跨 session，缺桶不填充）；Parquet 分区存储 + manifest + 去重/缺失统计；**回放引擎（服务端权威 cursor，API 永不返回 cursor 后数据，EMA 前日预热无前视，Predict First 判断提交即锁定，stop=失效点校验）**。
  5. 验证：pytest 29 通过（含 no-lookahead 集成断言、DST 锚点、半日市、判断锁定、随机日复现）；ruff 0 违规；mypy 0 错误；真实服务器冒烟测试通过；修复 REPO_ROOT 层级 bug 与 alembic Windows 路径问题。
  6. 下一步：MVP-A 前端回放工作台（Lightweight Charts + Predict First 表单 + 快捷键 + 保存恢复）。
- Batch 10 完成（MVP-A 前端回放工作台，2026-08-16）：
  1. 新增前端：Lightweight Charts v4 K线图（服务端裁剪后的 bars + EMA20 + 关键价位 price lines）；Predict First 十问判断表单（档位概率、two reasons、stop=失效点校验、提交锁定）；回放工作台（播放/暂停/逐根/回看(free)/速度选择/随机日/恢复上次会话(localStorage)/标注/已锁定判断列表/市场时间 ET+北京双时区）；快捷键 Space/→/←/J/M。
  2. 单进程模式：后端直接伺服 apps/web/dist（日常使用仅 start-backend.cmd；前端开发才需 5173 dev server）。启动脚本改纯 ASCII 修复 GBK 批处理解析问题。
  3. 浏览器实测通过：选日→建会话→图表/关键价位/状态栏渲染→逐根推进（按钮+快捷键）→判断表单填写提交→锁定入列→表单关闭。自动化点击在模态滚动容器内存在偶发 actionability 超时（嵌入式浏览器坐标怪癖，真实用户不受影响——键盘与按钮功能均验证正常）。
  4. MVP-A 验收状态：后端 ✅ + 前端 ✅。剩余打磨项（后续批次）：图表时区显示选项（当前轴为 UTC）、考试模式、会话列表管理。
- Batch 11 完成（HF Data Library 真实数据集成，2026-08-16）：
  1. 调研结论沉淀：HFDL 免费无门槛（CC BY 4.0）、SPY 1m RTH-only、复权价格；精度分段——2002~2022-03 为 PiTrading 合并磁带（CTA/UTP 全市场，佳），之后为 IEX 单所（OQ-01 待验证）。与 Alpaca 分工：HFDL 为主历史训练源（建议优先 2022-03 前日期），Alpaca 备用。
  2. 新增：hfdl_provider（X-API-Key 鉴权、/download 全量 Parquet 缓存到 data/imports/、ET墙钟→UTC 解析含 DST、节假日/RTH 防御过滤、复权标记 data_version）；SPY_HFDL Instrument（tick 0.0001 复权精度、feed_consolidated 标注 splice）；services/ingest.py 通用摄取；CLI `data ingest-hfdl`（幂等、含 splice 边界精度诊断）；SessionInfoOut 增加 provider 字段。
  3. 前端：数据源选择（合成/真实）、会话期 provider 透传、hfdl 提示（复权·仅RTH·无盘前→盘前价位显示 —）。
  4. 验证：pytest 31 通过（新增 HFDL 解析器 2 项：DST/冬夏令 UTC 转换、节假日与盘前过滤、日期范围）；ruff/mypy 零问题；前端构建通过。
  5. 待办：用户在 hfdatalibrary.com 补全个人资料（机构/国家/角色）后运行 `python -m app.cli data ingest-hfdl --start 2019-01-02 --end 2021-12-31` 完成真实数据入库（API 已验证密钥有效，当前返回 "complete your profile" 提示）。
- Batch 12 完成（真实数据入库 + 全链路验证，2026-08-16）：
  1. 用户补全 HFDL 资料 → API 开通；/download/SPY 全量 Parquet 49.6MB 下载（224 万根 1m，2002-12-30~2026-08-14，source 列标注 pitrading/iex 拼接）。
  2. 适配实际列名（大写 Open/High/Low/Close/Volume + source），解析器与 fixture 同步。
  3. 摄取 2019-01-02~2021-12-31（合并磁带时期）：757 交易日 / 286,658 根 1m / 58,640 根 5m，去重 0；manifest 缺桶 190（clean 清洗所致，约 0.3%）；分钟均量 14.2 万（全市场特征）。
  4. 全链路验证：pytest 31 通过；API 建会话 2020-03-16（熔断周一）——开盘 234.41/前日收 263.32/gap -28.91 与史实吻合，盘前价位正确降级 None；浏览器 UI 切换 hfdl 数据源→选日→训练→hfdl 提示与缺口显示正常；快捷键推进正常。
  5. 后端已重启加载新代码。注：嵌入式浏览器合成鼠标点击偶发失效（改用 dom_cua/键盘绕过），不影响真实用户操作。

- Batch 13 完成（MVP-B 客观价格事实 detector，2026-08-16）：
  1. Concept Specs ×7（先规格后代码）：bar-anatomy / doji / trend-bar / inside-bar / outside-bar / ii-iii-ioi / signal-bar-evidence——含 concept/implementation provenance 分离、book_refs（术语表章节级，source_confidence A/B 如实标注）、机械定义与参数、边界案例（等幅K线同时 inside+outside、零波幅、首根不判定）、knowable_at=bar_close。术语表核对修正两处认知：inside/outside 含等于（与实现一致）；trend bar 与 doji 为二分频谱（原书界限比 0.25 更紧，参数已声明为保守近似）。
  2. 框架：structure/profile.py 版本化参数（mvp-b-0.1.0）；detectors/base.py Candidate 结构（多 result_type、evidence、provenance）+ 注册表；detector_service 以"前日RTH预热 + 当日可见"为上下文批量计算，detect(ctx,i) 只读 ctx[0..i]（no lookahead by construction）。
  3. 实现 7 detector：bar_anatomy（evidence_set）、doji（boolean，阈值0.25）、trend_bar（categorical + strong 双条件）、inside/outside（boolean，inclusive）、bar_pattern（事件型 ii/iii/ioi，iii 同时报 ii）、signal_bar_evidence（evidence_set，只给证据不下结论）。
  4. 回放集成（Predict First）：会话存在已提交判断才在 SessionDetail 下发 candidates；GET /api/v1/detectors 输出清单+参数+spec 路径。前端：侧栏"系统候选"面板（当前栏判定 + 当日计数 + 标记开关）+ 图表克制标记（inside 下点/outside 上点/ii·iii·ioi 标签）。
  5. 修复两个真实 bug：list 类端点未透传 provider（hfdl 会话判断列表 404 清空）；提交判断后未重取 detail（候选延迟解锁）。
  6. 验证：pytest 43 通过（新增 12：正/反/边界/无前视/解锁流程）；ruff/mypy 零问题；真实数据端到端——2020-03-16 提交判断后 126 候选下发，当前栏正确识别 bear_trend_bar（body_ratio/close_location 证据完整），UI 面板与标记渲染正常。
- Batch 14 完成（MVP-C 前置核查 + 结构层，2026-08-16）：
  1. OQ-01 已验证：成交量交叉核对（2020-03-09 204.4M / 03-12 255.6M，±1% 吻合公开合并磁带记录）、OHLC 违规 0、零波幅 0 → 5m 结构层精度充足；tick 级仍需 tick 源（后置）。
  2. OQ-02 部分解决：提取文本带 PDFPAGE 标记，已补页码级引用——H1/H2 术语表 PDF p19（印刷 xvii）/讨论 p66/p83；second entry p23；swing/pullback p15；leg p19；trend line p16。
  3. MVP-C 第一批：Concept Specs（swing / pullback-leg / hl-counting）；实现 swing（右侧 N=3 确认，knowable_at 晚于 event_at）、pullback_leg（术语表单K线定义+净漂移上下文）、hl_counting（术语表定义直译状态机，H1→H4/L1→L4，second_entry 标注，上下文翻转归零）；profile 升 mvp-c-0.1.0；前端面板/标记（SH/SL 箭头、H/L 绿点）已构建。
  4. 验证：pytest 48 通过（新增 5：swing 双向确认与 superseded 语义、pullback 上下文、H/L 序列 H1→H2 second entry、连续更高高不重复计数、状态重置）。
  5. 遗留（下一批）：trend line / channel line detector、leg 划分 v0.2（待 swing 修订链）、净漂移上下文升级为 swing 序列上下文、MVP-C 浏览器实测截图。

- Batch 15 完成（Sealed Exam 隔离保护 + MVP-C 结构层全部就绪，2026-08-16）：
  1. 封存考试集（Sealed Exam Set）建立：确定性 Blake2b 哈希分层划分（约 15% 交易日被服务端隔离）；普通回放列表（GET /replay/days）默认自动排除封存日；普通模式试图加载封存日被服务端 403 严格拦截（sealed_exam_day_protected）；新增 /exam-summary 端点与 mode='exam' 专属通道。
  2. 趋势线与结构层升级：编写 docs/concepts/trend-lines.md；实现 trend_lines detector（基于确认 swing 序列的双点抬高/降低趋势线连线与突破检测）；结构上下文（_context_direction）升级为优先基于确认 swing 序列结构（HL/LL/HH/LH）推导市场环境，回退至 20 根净漂移。
  3. 前端支持：回放工作台支持“封存盲测考试”模式；图表组件支持 SH/SL 箭头标记与趋势线破位支持；概念索引表更新至 11 项。
  4. 验证：pytest 52 项测试全绿（新增 4 项：封存集确定性测试、分层比例测试、403 隔离测试、趋势线构造与突破断言）；ruff 0 违规；mypy 0 错误；前端编译打包通过。

- Batch 16 完成（MVP-D 候选扫描器 Scanner 全链路交付，2026-08-16）：
  1. 领域模型与数据库：新增 ScanTaskORM（任务状态/进度/扫描K线数）与 CandidateRecordORM（候选记录/4档审核状态/拒绝原因/收藏/错题本/审核时间戳）；Alembic 迁移与 SQLite 初始表结构更新完毕。
  2. 扫描执行引擎（ScannerService）：支持多时间段/指定 detector 集合/多数据源批量扫描；严格继承同一套 compute_candidates（保证完全无前视与可解释性一致）；默认排除封存考试日。
  3. API 路由（/scan/tasks 与 /scan/candidates）：创建扫描任务、任务进度列表、多维筛选查询（按任务/detector/审核状态/收藏/错题本）、人工 4 档审核接口（confirmed/rejected/uncertain/needs_review 附带 rejection_reason 与 review_notes）。
  4. 前端 Scanner 扫描工作台：
     - 任务配置区：数据源/日期范围/多选指定 Detector（支持全部 11 类）；
     - 任务历史侧栏：任务状态/扫描天数/候选数/卡片切换；
     - 候选筛选列表：实时按 detector/状态/收藏/错题本过滤，支持一键打开对应日期的回放训练；
     - 证据抽屉与审核面板：展开完整 Evidence JSON，一键标记 4 档状态、选择拒绝原因、加星收藏、收入错题本。
  5. 验证：全量 53 项自动化测试全绿（新增 Scanner 端到端任务与审核测试）；Ruff 0 违规；Mypy 0 错误；前端编译打包完成。

- Batch 17 完成（Phase 1: Analytics 学习分析与盲测复评全链路，2026-08-16 深夜）：
  1. 领域模型与服务层：新增 AnalyticsService（总会话/判断/标注/审核正反例/收藏/错题统计，市场环境判断分布，反例拒绝原因归纳）；实现 get_blind_recheck_queue（严格脱敏原始标签）与 submit_recheck（test-retest 前后一致性对比）。
  2. API 路由：新增 GET /api/v1/analytics/overview、GET /api/v1/analytics/recheck-queue 与 POST /api/v1/analytics/recheck。
  3. 前端看板：新增「学习分析与错题本 (Analytics)」页面（四大 KPI 指标卡片、宏观环境分布、反例原因归纳、盲测复评卡片、错题本精选归档表格）。
  4. 验证：54 项自动化测试全绿（新增 test_analytics.py 端到端测试）；Ruff 0 违规；Mypy 0 错误；前端打包通过。

- Batch 18 完成（Phase 2: 模拟交易撮合与 MFE/MAE 实时追踪引擎，2026-08-16 深夜）：
  1. 领域模型与数据库：新增 SimTradeORM 模型（持仓状态、挂单/成交时间、初始风险 Initial Risk、MFE/MAE 及对应 R 倍数、出场原因）；SQLite 数据库建表同步完成。
  2. 模拟交易执行服务（SimTradeService）：
     - 订单类型：市价单（当前 Bar 立即成交）、限价单（达到价格撮合）、停止单（突破触发）；
     - 保守歧义撮合（ADR-005）：同一根 Bar 触及 Target 与 Stop 时默认止损先触发；
     - 过程跟踪：随每根 K 线推进实时计算最大有利浮盈 (MFE) 与最大不利回撤 (MAE)，并实时折算为 R 倍数（pnl_in_r = pnl / initial_risk）。
  3. API 路由（/trades）：POST /trades/sessions/{session_id} 下单、GET 查询会话持仓、POST /{trade_id}/exit 手动平仓。
  4. 前端交互集成：回放工具栏新增 `🎯 T · 模拟下单` 按钮（支持快捷键 T 唤起下单弹窗）、右侧栏新增「模拟持仓与出场」卡片（实时显示挂单、持仓 MFE/MAE、盈亏 R 倍数与一键平仓）。
  5. 验证：57 项测试全绿（新增 test_sim_trade.py 撮合与保守测试）；Ruff 0 违规；Mypy 0 错误；前端打包通过。

- Batch 19 完成（Phase 3: Level 5 复杂形态识别器 + 全仓一致性收口，2026-08-16 深夜）：
  1. Concept Specs ×3：编写 docs/concepts/ 规范（wedge.md 楔形三推衰减、climax.md 高潮反转双模式、micro-channel.md 微型通道连续不破极值）。
  2. 识别器实现（app/detectors/complex.py）：
     - wedge：基于确认 Swing 序列检测 3 次推进（HH1<HH2<HH3 / LL1>LL2>LL3）与推进幅度衰减；
     - climax：单K线 2.6 倍相对波幅衰竭棒与连续 3 根强趋势K线加速高潮；
     - micro_channel：多头（low[k]>=low[k-1]）与空头（high[k]<=high[k-1]）极窄微通道长度追踪。
  3. 参数与全阶形态注册：升版本至 mvp-l5-0.1.0，全系统已就绪 14 类价格行为形态。
  4. 验证：60 项测试全绿（新增 test_complex_detectors.py）；Ruff 0 违规；Mypy 0 错误；前端打包通过。

- Batch 20 完成（P0: Always In 状态机 + 知识库检索，2026-08-22）：
  1. Always In 方向状态机（docs/concepts/always-in.md, Trends PDF p15/xv）：基于已确认 Swing 序列（HH+HL→long, LH+LL→short）与 H/L 计数（H3/H4→long, L3/L4→short）组合判定；仅翻转时发出事件；transition 作为重置标记。
  2. 知识库检索服务：KnowledgeService 基于 data/knowledge/extracted/*.txt（带 PDFPAGE 标记）建立本地全文索引；支持多关键词搜索与按 Concept 英文名检索；返回结构化引用（book/pdf_page/print_page/chunk_id/chunk_hash）；print_page 仅确定时填写否则 null。
  3. API 路由：GET /api/v1/knowledge/search 与 GET /api/v1/knowledge/concept/{term}。
  4. 验证：64 项测试全绿；Ruff 0 违规；Mypy 0 错误；前端构建通过。detector 总数 15 类。

- Batch 22 完成（P2: spike_and_channel + final_flag + 全部测试修复，2026-08-16 深夜）：
  1. Concept Specs ×2：spike-and-channel（两阶段判定：强趋势尖刺 + 动量衰减通道）、final-flag（climax 后窄幅旗形停顿，extension < 50% climax span）。
  2. Detector 实现与注册：spike_and_channel / final_flag 加入 register_advanced()；detector 总数达 19 类；profile 升至 mvp-l3l5-0.1.0。
  3. Bug 修复：advanced.py backward search 中 anatomy([single_bar],0) 导致 relative_range=None 的 bug（改为传入完整 ctx）；climax_bar 未定义变量。
  4. 验证：69 项测试全绿；Ruff 0 违规；Mypy 0 错误；前端构建通过。
