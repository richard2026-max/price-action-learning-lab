# Price Action Learning Lab · 价格行为学习与训练平台

> 服务于 Al Brooks 价格行为学长期学习、刻意训练、研究验证、个人认知积累的**本地专业研究平台**。
> **这不是自动交易机器人，也不是传统回测平台**。系统输出永远是"候选"，帮助用户建立认知而非取代思考。

---

## 📌 文档入口（AI Agent 请从这里开始）

> 本文件是**所有以后 AI agent 的文档入口**。先按下列顺序阅读，建立正确上下文，再处理具体任务。

### 推荐阅读顺序

| # | 文档 | 状态 | 为什么读 |
|---|---|---|---|
| 1 | [docs/review-state.md](docs/review-state.md) · [docs/repository-consistency-report.md](docs/repository-consistency-report.md) | Active | **项目背景/审计总览**：先了解审计进度、已改/废弃文档、未决问题 |
| 2 | [docs/product/PRD.md](docs/product/PRD.md) | **Canonical** | **产品需求**：SPY 5m 单图、MVP-A/B/C/D 递进、detector 多 result type、服务端 no-lookahead、Predict First |
| 3 | [docs/content-provenance-policy.md](docs/content-provenance-policy.md) | **Canonical** | **内容来源策略**：四层来源×优先级二维、source_confidence A/B/D、design_rationale、结构化引用 |
| 4 | [docs/architecture/brooks-system-design-implications.md](docs/architecture/brooks-system-design-implications.md) | **Canonical** | **Brooks 体系对系统设计的影响**：把"先懂 Brooks"落到"怎么开发"的桥梁 |
| 5 | [docs/product/docs-consistency-review.md](docs/product/docs-consistency-review.md) | **Canonical** | **一致性核对表**：原文档冲突与修改记录、十五项跨文档核对 |
| 6 | [docs/architecture/architecture.md](docs/architecture/architecture.md) | Active | **系统架构**：总体架构、数据流、技术栈、关键设计原则 |
| 7 | [docs/architecture/data-contracts-and-api.md](docs/architecture/data-contracts-and-api.md) | Active | **数据合同与 API**：K线字段、Instrument Metadata、Data Fidelity、REST 草案 |
| 8 | [docs/architecture/domain-model.md](docs/architecture/domain-model.md) · [docs/architecture/adr-and-risks.md](docs/architecture/adr-and-risks.md) | Active | **Replay / No-Lookahead Spec**：领域模型（event_time≠knowable_time）、ADR 决策与风险 |
| 9 | [docs/concepts/README.md](docs/concepts/README.md) | Active | **Concept Specs**：16 类 detector 规格索引（全部先规格后实现） |
| 10 | [docs/architecture/project-structure-and-roadmap.md](docs/architecture/project-structure-and-roadmap.md) | Active | **Roadmap / Milestones**：MVP-A/B/C/D → Later 递进 |
| 11 | [docs/user-guide/getting-started.md](docs/user-guide/getting-started.md) | Active | **用户手册**：全套操作指南、快捷键与真实数据接入流程 |

---

## 核心功能

- **历史K线逐根回放训练器**（SPY 5m 单图，服务端权威游标，严格无前视，支持前置加载 1~10 天连续走势背景与封存考试隔离模式）；
- **Predict First 盘中判断表单**（十问结构、双理由规则、失效点止损校验、提交后永久锁定）；
- **模拟交易与交易管理引擎**（市价/限价/停止单、ADR-005 保守结算、MFE/MAE 实时 R 倍数追踪、一键平仓）；
- **价格行为形态识别器（Level 1-5 共 19 类）**（K线解剖、十字星、趋势K线、内包/外包、ii/iii/ioi、信号棒证据、Swing、回调、H1-H4/L1-L4 计数、趋势线/通道线、双顶双底、突破/失败突破、Always In 状态机、楔形三推、高潮反转、微型通道、尖刺通道、终极旗形）；
- **历史价格行为候选扫描器**（批量历史扫描、任务进度监控、候选多维筛选、人工 4 档审核、错题本与典型案例收藏）；
- **学习分析与认知统计大屏**（训练总量统计、读图画像分布、反例拒绝原因归纳、盲测复评 Blind Recheck 一致性自测、交易统计与日类型分类）。

## 快速开始

### 方式一：启动脚本（推荐，在仓库根目录双击或运行）

```powershell
.\start-backend.cmd    # 后端 + Web 界面 http://127.0.0.1:8000 （单进程即可日常使用）
.\start-frontend.cmd   # 仅开发前端时需要（Vite 热更新，http://localhost:5173）
```

> 日常使用只需 `start-backend.cmd`：后端会直接伺服前端构建产物（`apps/web/dist`）。

### 方式二：手动命令

```bash
# 后端（从仓库根目录）
cd apps/api
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"      # Windows；macOS/Linux 用 .venv/bin/pip
.venv/Scripts/alembic upgrade head          # 建表（data/app.sqlite）
.venv/Scripts/python -m app.cli data seed --start 2024-01-02 --end 2024-03-28 # 生成演示数据
.venv/Scripts/python -m app.cli api          # http://127.0.0.1:8000/api/docs

# 前端构建
cd apps/web
npm install
npm run build
```

## 提交反馈与建议 (Issues)

如果你在训练过程中发现任何 Bug、看盘不顺手的地方或希望增加的新功能，欢迎直接在 GitHub 提交 Issue：
- 点击仓库顶部的 **`Issues` -> `New Issue`**，选择 **“功能建议或 Bug 反馈”** 模板填写即可。

## 验证命令

```bash
cd apps/api
.venv/Scripts/python -m pytest tests/   # 95 项测试全绿（含 no-lookahead 权威断言；2026-08-28 全量实测复核）
.venv/Scripts/python -m ruff check app tests
.venv/Scripts/python -m mypy app
```

## 状态总览

- **Phase 0 到 MVP-D + Level 5 全部形态**：✅ **100% 全链路交付**（95 项测试全绿，Ruff 0 违规，Mypy 0 错误——2026-08-28 实测复核）。
