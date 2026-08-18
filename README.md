# Price Action Learning Lab · 价格行为学习与训练平台

> 服务于 Al Brooks 价格行为学长期学习、刻意训练、研究验证、个人认知积累的**本地研究平台**。
> **这不是自动交易机器人，也不是传统回测平台**。系统输出永远是"候选"，帮助用户建立认知而非取代思考。

---

## 📌 文档入口（AI Agent 请从这里开始）

> 本文件是**所有以后 AI agent 的文档入口**。先按下列顺序阅读，建立正确上下文，再处理具体任务。

### 文档状态标记

| 标记 | 含义 |
|---|---|
| **Canonical** | 权威文档。跨文档一致性的最终依据，冲突时以此为准 |
| **Active** | 现行有效，与 canonical 对齐，作为设计与实现依据 |
| **Historical** | 历史参考，可追溯旧决策，不再作为权威 |
| **Deprecated** | 已废弃，仅保留用于追溯，不得作为实现依据 |

### 推荐阅读顺序

| # | 文档 | 状态 | 为什么读 |
|---|---|---|---|
| 1 | [docs/review-state.md](docs/review-state.md) · [docs/repository-consistency-report.md](docs/repository-consistency-report.md) | Active | **项目背景/审计总览**：先了解审计进度、已改/废弃文档、未决问题 |
| 2 | [docs/product/PRD.md](docs/product/PRD.md) | **Canonical** | **产品需求**：SPY 5m 单图、MVP-A/B/C/D 递进、detector 多 result type、服务端 no-lookahead、Predict First |
| 3 | [docs/content-provenance-policy.md](docs/content-provenance-policy.md) | **Canonical** | **内容来源策略**：四层来源×优先级二维、source_confidence A/B/D、design_rationale、结构化引用 |
| 4 | [docs/architecture/brooks-system-design-implications.md](docs/architecture/brooks-system-design-implications.md) | **Canonical** | **Brooks 体系对系统设计的影响**：把"先懂 Brooks"落到"怎么开发"的桥梁 |
| 5 | [docs/product/docs-consistency-review.md](docs/product/docs-consistency-review.md) | **Canonical** | **一致性核对表**：原文档冲突与修改记录、十三项跨文档一致性核对 |
| 6 | [docs/architecture/architecture.md](docs/architecture/architecture.md) | Active | **系统架构**：总体架构、数据流、技术栈、关键设计原则 |
| 7 | [docs/architecture/data-contracts-and-api.md](docs/architecture/data-contracts-and-api.md) | Active | **数据合同与 API**：K线字段、Instrument Metadata、Data Fidelity、REST 草案 |
| 8 | [docs/architecture/domain-model.md](docs/architecture/domain-model.md) · [docs/architecture/adr-and-risks.md](docs/architecture/adr-and-risks.md) | Active | **Replay / No-Lookahead Spec**：领域模型（event_time≠knowable_time）、ADR 决策与风险 |
| 9 | [docs/concepts/README.md](docs/concepts/README.md) | Active | **Concept Specs**：detector 进入 Scanner 的强制流程 |
| 10 | [docs/architecture/project-structure-and-roadmap.md](docs/architecture/project-structure-and-roadmap.md) | Active | **Roadmap / Milestones**：MVP-A/B/C/D → Later 递进 |
| 11 | [docs/open-questions.md](docs/open-questions.md) | Active | **ADR/未决问题**：3 个 open questions，均不阻塞 MVP-A |

### 状态标记汇总

| 文档 | 状态 |
|---|---|
| `docs/product/PRD.md` | **Canonical** |
| `docs/content-provenance-policy.md` | **Canonical** |
| `docs/architecture/brooks-system-design-implications.md` | **Canonical** |
| `docs/product/docs-consistency-review.md` | **Canonical** |
| `docs/architecture/architecture.md` | Active |
| `docs/architecture/data-contracts-and-api.md` | Active |
| `docs/architecture/domain-model.md` | Active |
| `docs/architecture/adr-and-risks.md` | Active |
| `docs/architecture/project-structure-and-roadmap.md` | Active |
| `docs/concepts/README.md` | Active |
| `docs/open-questions.md` | Active |
| `docs/repository-consistency-report.md` | Active |
| `docs/review-state.md` | Active |
| `docs/architecture/assumptions.md` | **Deprecated**（历史追溯） |
| `data/knowledge/**` | **Historical**（Brooks 笔记/原文参考，非设计文档；Batch 9 自 docs/knowledge 迁入） |
| `docs/README.md` | Active（docs/ 文档地图） |
| `docs/document-inventory.md` | Active（全仓文档登记表，改文档前先查） |

---

## 项目定位

- **学习**：理解市场背景、趋势、区间、突破、回调、失败突破等价格行为概念。
- **训练**：历史行情逐根回放，无未来信息做出判断并记录检查。
- **研究**：将概念转成候选识别器，扫描大量历史数据，由用户人工复核与统计。

## 技术栈

- 后端：Python 3.12+ / FastAPI / Polars / DuckDB / SQLite（WAL）
- 前端：TypeScript / React / Vite / TradingView Lightweight Charts / Zustand / TanStack Query
- 容器化：Docker Compose（可选）

## 核心功能（第一版）

- 历史K线逐根回放训练器（**SPY 5m 单图**，严格无前视）
- 历史价格行为候选扫描器（candidate detector，多 result type）
- 标注系统 + 模拟交易
- 书籍知识库 + AI 教练（可选，禁用可运行）

## 目录结构

```
apps/api/      后端 FastAPI
apps/web/      前端 React
data/          本地数据（demo/market/imports/knowledge/exports）
docs/          文档（入口见 docs/README.md；product/architecture/concepts/knowledge）
scripts/       本地脚本
docker/        容器相关
```

详见 [docs/architecture/project-structure-and-roadmap.md](docs/architecture/project-structure-and-roadmap.md)。

## 分阶段路线图（产品递进）

> 旧版 Milestone 0-9 已被 PRD 的 **MVP-A/B/C/D → Later** 递进取代。**第一件可用产品是 Replay Trainer（MVP-A）。**

- **MVP-A** Replay Trainer（SPY 数据、1m→5m、RTH、20EMA、服务端 no-lookahead、Predict First、基础标注）——无需复杂 detector
- **MVP-B** 客观价格事实（bar anatomy、inside/outside、trend bar 等）
- **MVP-C** 结构层（swing、leg、pullback）→ **H1/H2、L1/L2、second entry**
- **MVP-D** Scanner（批量扫描、review、错题本、blind recheck）
- **Later** wedge、always-in、climax、完整交易管理、知识库 Figure、AI coach

## 快速开始

### 方式一：启动脚本（推荐，在仓库根目录双击或运行）

```powershell
.\start-backend.cmd    # 后端 + Web 界面 http://127.0.0.1:8000 （单进程即可日常使用）
.\start-frontend.cmd   # 仅开发前端时需要（Vite 热更新，http://localhost:5173）
```

> 日常使用只需 `start-backend.cmd`：后端会直接伺服前端构建产物（`apps/web/dist`）。
> 修改前端代码后运行 `cd apps/web && npm run build` 更新产物；开发时用 `start-frontend.cmd`（5173 + 热更新，/api 自动代理到 8000）。

### 方式二：手动命令（注意：cd 命令以仓库根目录为起点，已在子目录时不要重复 cd）

```bash
# 后端（Python 3.12+）——从仓库根目录开始
cd apps/api
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"      # Windows；macOS/Linux 用 .venv/bin/pip
.venv/Scripts/alembic upgrade head          # 建表（data/app.sqlite）
.venv/Scripts/python -m app.cli data seed --start 2024-01-02 --end 2024-03-28
.venv/Scripts/python -m app.cli api          # http://127.0.0.1:8000/api/docs

# 前端（Node 18+）——新开终端，从仓库根目录开始
cd apps/web
npm install
npm run dev                                  # http://localhost:5173（/api 代理到 8000）

# 或容器化（从仓库根目录）
docker compose up --build
```

## 验证命令

```bash
cd apps/api
.venv/Scripts/python -m pytest tests/   # 29 项测试（含 no-lookahead 集成断言）
.venv/Scripts/python -m ruff check app tests
.venv/Scripts/python -m mypy app
```

## 状态

- **Phase 0（可运行基础仓库）**：✅ 完成——FastAPI + React 骨架、SQLite/Alembic、合成演示数据、健康检查、CLI、Docker Compose。
- **MVP-A（Replay Trainer）**：✅ 完成——服务端权威 cursor 回放（no-lookahead、EMA 前日预热、Predict First 判断锁定、关键价位覆盖）+ 前端工作台（Lightweight Charts、快捷键、随机日、恢复）；**真实 SPY 数据已入库**（HF Data Library，2019-2021 共 757 交易日，CC BY 4.0）。
- **MVP-B（客观价格事实 detector）**：✅ 完成——7 个 detector（bar_anatomy/doji/trend_bar/inside/outside/ii-iii-ioi/signal_bar_evidence），Concept Spec 先行，判断提交后解锁候选显示（Predict First 揭晓）。
- **MVP-C（结构层与形态原语）**：✅ 完成——11 个 detector（新增 swing/pullback_leg/hl_counting/trend_lines）；结构上下文升级为基于确认 swing 序列；**封存考试集（Sealed Exam Set）建立并实现服务端 403 严格隔离**。
- **MVP-D（候选扫描器 Scanner）**：✅ 完成——批量历史扫描引擎（11 类 detector）、任务历史监控、候选多维筛选、一键跳转无未来回放、人工 4 档审核（confirmed/rejected/uncertain/needs_review）、拒绝原因归档、典型案例收藏与错题本。
- 下一步：**MVP-D 增强与学习分析（Analytics）**（一致性统计、错题重现、置信度校准）。
- 文档阶段（Milestone 0 + 全仓审计 Batch 0-13）：✅ 完成，无 blocker。