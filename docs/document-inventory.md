# 文档清单 · Document Inventory

> 全仓文档登记表。**Milestone 1 前全仓文档一致性审计**（Prompt §3）要求的交付物，Batch 8 补齐。
> 用途：任何 AI agent / 人在修改文档前，先在此确认该文档的用途与状态，避免读到旧文档后把旧方案复活。
> 维护规则：**新增或变更文档状态时必须同步更新本表**（新增 detector Concept Spec 时同步登记 `docs/concepts/README.md` 索引）。
> 状态取值仅允许：`active` / `needs_update` / `deprecated` / `historical` / `unknown`。

```yaml
inventory_version: 1.1.0
generated_at: 2026-08-16
canonical_documents:
  - docs/product/PRD.md
  - docs/content-provenance-policy.md
  - docs/architecture/brooks-system-design-implications.md
  - docs/product/docs-consistency-review.md
```

---

## 一、设计与流程文档（审计对象）

| document | purpose | status | canonical? | needs_update? | reason |
|---|---|---|---|---|---|
| `README.md`（仓库根） | 全仓入口：AI agent 阅读顺序、状态标记汇总、快速开始 | active | 否 | 否 | 与 canonical 对齐；Batch 8 已补 document-inventory / docs-README 链接 |
| `docs/README.md` | docs/ 目录入口：文档地图与阅读顺序（审计 Prompt §14 交付物） | active | 否 | 否 | Batch 8 新建 |
| `docs/document-inventory.md` | 本文件：全仓文档登记表 | active | 否 | 持续维护 | Batch 8 新建（补齐审计交付物 A） |
| `docs/review-state.md` | 文档审计状态（可中断恢复），批次进度与冲突记录 | active | 否 | 持续维护 | 审计完成；后续文档变更在此追加批次记录 |
| `docs/repository-consistency-report.md` | 全仓审计最终报告：19 份文档扫描、14 项旧设计修正、MVP-A blocker 判定 | active | 否 | 否 | 结论：无 blocker，READY FOR MVP-A |
| `docs/open-questions.md` | 未决问题登记（OQ-01/02/03，均不阻塞 MVP-A） | active | 否 | 持续维护 | OQ-01 于 MVP-C 前验证；OQ-02 于 MVP-C 前补页码级引用 |
| `docs/product/PRD.md` | 产品需求：SPY 5m 单图、MVP-A/B/C/D、Predict First、no-lookahead | active | **是** | 否 | v0.3.0，四份 canonical 之一 |
| `docs/content-provenance-policy.md` | 内容来源策略：四层来源 × 优先级、source_confidence A/B/D、引用协议 | active | **是** | 否 | v0.2.0，来源分层唯一权威 |
| `docs/architecture/brooks-system-design-implications.md` | Brooks 体系 → 系统设计桥梁：世界观、Level 0-6、knowable_at、单图原则 | active | **是** | 否 | v0.3.0 |
| `docs/product/docs-consistency-review.md` | 一致性核对表：原文档冲突与修改记录、十五项跨文档核对 | active | **是** | 否 | v0.3.0 |
| `docs/architecture/architecture.md` | 系统架构：总体架构图、数据流、技术栈、设计原则 | active | 否 | 否 | Batch 8 修正旧里程碑编号表述 |
| `docs/architecture/domain-model.md` | 领域模型：Symbol/Bar/Candidate(event_at≠knowable_at)/ReplaySession 等 | active | 否 | 否 | Batch 8 将 detector-specs 引用改指 docs/concepts/ |
| `docs/architecture/data-contracts-and-api.md` | 数据合同与 API 草案：K线字段、Instrument Metadata、1m→5m session-aware 聚合、REST | active | 否 | 否 | Batch 8 修正 rule_source 来源分层表述 |
| `docs/architecture/adr-and-risks.md` | ADR 决策记录（ADR-001~008）与风险清单（12 项） | active | 否 | 否 | Batch 8 修正旧里程碑编号表述 |
| `docs/architecture/prior-art-survey.md` | 既有方案调研与选型决策（无可 fork 整体方案；组件级复用清单） | active | 否 | 否 | Batch 9 新增（ADR 性质） |
| `docs/architecture/project-structure-and-roadmap.md` | 仓库目录结构与 MVP-A/B/C/D → Later 路线图 | active | 否 | 否 | Batch 8 将目录树 docs/ 部分对齐实际结构 |
| `docs/concepts/README.md` | Concept Spec 强制流程与模板（detector 进入 Scanner 的唯一关卡） | active | 否 | 持续维护 | 索引表随新概念规格登记 |
| `docs/architecture/assumptions.md` | （历史）初版需求理解与默认值 | **deprecated** | 否 | — | 已被 PRD + content-provenance-policy 取代，顶部有 DEPRECATED 声明，仅作历史追溯 |

## 二、知识库参考资料（非设计文档，不审计）

> 以下为 Brooks 原书笔记与提取文本，属**学习资料**而非设计依据；引用时作为 `book_refs` 的核查来源。原书 PDF 位于仓库外（`AlBrooks书/`），不入库。
> Batch 9 起存放于 `data/knowledge/`（自 `docs/knowledge/` 迁入，与设计文档分离）。

| document | purpose | status | reason |
|---|---|---|---|
| `data/knowledge/00_Reading_Price_Charts_Bar_by_Bar_前置笔记.md` | 首书前言精读笔记（Brooks 哲学与术语约定） | active（参考） | 术语约定的权威来源之一 |
| `data/knowledge/01_核心术语表_Trading_Price_Action_Trends.md` | Trends 术语总表 | active（参考） | Concept Spec `book_refs` 核查来源 |
| `data/knowledge/02_知识体系笔记_Trading_Price_Action_Trends.md` | Trends 知识体系笔记 | active（参考） | 同上 |
| `data/knowledge/03_知识体系笔记_Trading_Price_Action_Trading_Ranges.md` | Ranges 知识体系笔记 | active（参考） | 同上 |
| `data/knowledge/03_知识体系笔记_Trading_Price_Action_REVERSALS.md` | Reversals 知识体系笔记 | active（参考） | 同上 |
| `data/knowledge/提取笔记-高潮反转-楔形三推反转-扩张三角形.md` | 复杂形态专题提取笔记 | active（参考） | Level 5 概念（Later）的实现依据 |
| `data/knowledge/notes/part1-ch7-10-reversals.md` | Reversals 第 7-10 章笔记 | active（参考） | 同上 |
| `data/knowledge/extracted/*.txt` | 三本书全文提取文本（trends/ranges/reversals） | active（参考） | OQ-02 页码级引用核查的数据源 |

## 三、计划中尚未创建的文档

| 计划文档 | 何时创建 | 依据 |
|---|---|---|
| `docs/concepts/<concept>.md`（各概念规格） | MVP-B/C 各 detector 实现前 | PRD §五、concepts/README.md 十步强制流程 |
| `docs/user-guide/`（用户手册） | MVP-A 可用后 | project-structure-and-roadmap.md 目录树 |

---

*本表由 Batch 8 补齐（原审计遗漏交付物 A）。下次全仓审计或新增文档时以此为基础增量更新。*
