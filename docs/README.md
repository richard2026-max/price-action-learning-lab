# docs/ · 文档目录入口

> 本文件是 `docs/` 目录的地图（审计 Prompt §14 交付物，Batch 8 补齐）。
> 仓库总入口见根 [README.md](../README.md)（含运行方式）；本文件回答"**文档在哪里、该先读什么**"。
> 任何 AI agent 处理本项目任务前，请按下方顺序阅读，建立正确上下文。

---

## 一、状态标记

| 标记 | 含义 |
|---|---|
| **Canonical** | 权威文档。跨文档冲突时以此为准（共 4 份） |
| **Active** | 现行有效，与 canonical 对齐 |
| **Deprecated** | 已废弃，仅保留历史追溯，不得作为实现依据 |
| **参考** | 知识库资料（Brooks 原书笔记/提取文本），非设计文档 |

## 二、推荐阅读顺序

| # | 文档 | 状态 | 内容 |
|---|---|---|---|
| 1 | [product/PRD.md](product/PRD.md) | **Canonical** | 产品需求：SPY 5m 单图、MVP-A/B/C/D 递进、Predict First、no-lookahead |
| 2 | [content-provenance-policy.md](content-provenance-policy.md) | **Canonical** | 内容来源策略：四层来源 × 优先级、source_confidence A/B/D、引用协议 |
| 3 | [architecture/brooks-system-design-implications.md](architecture/brooks-system-design-implications.md) | **Canonical** | Brooks 体系 → 系统设计的桥梁：Level 0-6、knowable_at、单图原则 |
| 4 | [product/docs-consistency-review.md](product/docs-consistency-review.md) | **Canonical** | 一致性核对表：十五项跨文档核对结论 |
| 5 | [architecture/architecture.md](architecture/architecture.md) | Active | 系统架构、数据流、技术栈 |
| 6 | [architecture/data-contracts-and-api.md](architecture/data-contracts-and-api.md) | Active | 数据合同：K线字段、Instrument Metadata、1m→5m 聚合规则、REST 草案 |
| 7 | [architecture/domain-model.md](architecture/domain-model.md) | Active | 领域模型：Candidate(event_at≠knowable_at)、ReplaySession 等 |
| 8 | [architecture/adr-and-risks.md](architecture/adr-and-risks.md) | Active | ADR-001~008 与风险清单 |
| 9 | [architecture/project-structure-and-roadmap.md](architecture/project-structure-and-roadmap.md) | Active | 目录结构与 MVP-A/B/C/D → Later 路线图 |
| 10 | [concepts/README.md](concepts/README.md) | Active | Concept Spec 强制流程：detector 进入 Scanner 的唯一关卡 |
| 11 | [open-questions.md](open-questions.md) | Active | 未决问题 OQ-01/02/03（均不阻塞 MVP-A） |
| 12 | [document-inventory.md](document-inventory.md) | Active | 全仓文档登记表：改文档前先查状态 |
| 13 | [review-state.md](review-state.md) · [repository-consistency-report.md](repository-consistency-report.md) | Active | 文档审计进度与最终报告 |
| — | [architecture/assumptions.md](architecture/assumptions.md) | **Deprecated** | 初版默认值，已被 canonical 取代，勿引用 |
| — | `../data/knowledge/` | 参考 | Brooks 原书笔记与提取文本（book_refs 核查来源，Batch 9 自 docs/knowledge 迁入） |

## 三、目录结构

```
docs/
├── README.md                  # 本文件（文档地图）
├── document-inventory.md      # 全仓文档登记表
├── content-provenance-policy.md  # [Canonical] 来源分层策略
├── open-questions.md          # 未决问题登记
├── review-state.md            # 文档审计状态（可中断恢复）
├── repository-consistency-report.md  # 审计最终报告
├── product/                   # PRD、一致性核对表
├── architecture/              # 架构、领域模型、数据合同、ADR、路线图（含 deprecated 的 assumptions）
├── concepts/                  # Concept Specs（detector 实现前必须先有 <concept>.md）
└── （Brooks 笔记/提取文本在 ../data/knowledge/，非设计文档）
```

> 未来新增：`user-guide/`（MVP-A 可用后）。旧规划中的 `detector-specs/`、`data-contracts/`、独立 `adr/` 目录已合并进 `concepts/` 与 `architecture/`，勿再按旧路径创建。

## 四、修改文档的规则

1. **先查 [document-inventory.md](document-inventory.md)** 确认目标文档状态；deprecated 文档不得作为依据。
2. 修改 canonical 文档须做跨文档一致性自查（对照 [product/docs-consistency-review.md](product/docs-consistency-review.md) 十五项）。
3. 新增/改状态 → 同步更新 document-inventory.md；新增 Concept Spec → 同步更新 [concepts/README.md](concepts/README.md) 索引。
4. 在 [review-state.md](review-state.md) 追加批次记录（what/why/when），保持审计链可追溯。
