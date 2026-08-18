# 仓库一致性审计报告 · Repository Consistency Report

> **批次**：Batch 7（最终交付 / Final Cross-check + Reports）
> **范围**：Milestone 1 前全仓文档一致性审计的收尾报告，汇总 Batch 0-6 的审查结果。
> **目的**：证明全仓设计文档已与四份 canonical 文档一致，并列出扫描范围、修改/废弃/发现、未决问题与 Milestone 1 blocker 判定。

---

## 一、扫描范围（审查了哪些文档）

审计共覆盖 **19 份 Markdown 文档**，分布于 7 个批次（Batch 0-6）。Brooks 笔记/原书文本（时为 `docs/knowledge/`，Batch 9 已迁至 `data/knowledge/`）仅作参考、不审计（非设计文档）。

### 批次清单与审查文档

| 批次 | 审查文档 | 结果 |
|---|---|---|
| Batch 0 | `content-provenance-policy.md`、`brooks-system-design-implications.md`、`PRD.md` | 修正（B0） |
| Batch 1 | `adr-and-risks.md`、`architecture.md`、`assumptions.md`、`domain-model.md`、`project-structure-and-roadmap.md` | 审阅/对齐；`assumptions.md` 标记 DEPRECATED |
| Batch 2 | `data-contracts-and-api.md` | 审阅/对齐 |
| Batch 3 | replay / API / no-lookahead 相关（架构层已覆盖） | 审阅/对齐 |
| Batch 4 | `concepts/`（detector 规范） | 新建 `concepts/README.md` |
| Batch 5 | roadmap / milestone / tasks（`project-structure-and-roadmap.md`） | 审阅/对齐 |
| Batch 6 | AI / knowledge base / analytics（`architecture.md` 等） | 修正（B6） |
| Batch 7 | 全仓最终交叉核对 + 本报告 + `open-questions.md` + `README.md` | 收尾 |

**实际落盘的文档**（docs/ 树）：

- `content-provenance-policy.md`（canonical）
- `review-state.md`（审计状态）
- `open-questions.md`（未决问题）
- `repository-consistency-report.md`（本报告，新建）
- `architecture/adr-and-risks.md`、`architecture/architecture.md`、`architecture/assumptions.md`、`architecture/brooks-system-design-implications.md`（canonical）、`architecture/data-contracts-and-api.md`、`architecture/domain-model.md`、`architecture/project-structure-and-roadmap.md`
- `concepts/README.md`
- `product/docs-consistency-review.md`（canonical）、`product/PRD.md`（canonical）
- `knowledge/**`（Brooks 笔记/原文，仅参考不审计）

---

## 二、修改了哪些文档

| 文档 | 状态 | 修改内容要点 |
|---|---|---|
| `docs/content-provenance-policy.md` | **修改**（canonical） | 拆两个正交维度（来源×优先级）；source_confidence A/B/D（弃 C）；design_rationale/derivation_level；Concept Spec 模板；SPY 表述拆开 |
| `docs/architecture/brooks-system-design-implications.md` | **修改**（canonical） | Level 0 区分 Brooks vs Product；design_rationale；补 5 处 book_refs；Level 5 修正归类 |
| `docs/product/PRD.md` | **修改**（canonical） | Predict First "关键位置"补无未来偏差触发规则 + candidate-sampled sampling_bias；Level 0 Provenance 混合；detector 多 result type |
| `docs/architecture/architecture.md` | **修改** | 补远程模型书籍片段隐私/版权策略；知识库 2.4 Early/Later + OCR fallback |
| `docs/architecture/adr-and-risks.md` | 对齐 | 对齐 SPY 5m 单图、1h Research、MVP-A/B/C/D、多 result type |
| `docs/architecture/domain-model.md` | 对齐 | event_time≠knowable_time、rule_source 四层、detector 多 result type |
| `docs/architecture/data-contracts-and-api.md` | 对齐 | session-aware 聚合、Instrument Metadata、Data Fidelity 声明、sealed exam set Early |
| `docs/architecture/project-structure-and-roadmap.md` | 对齐 | 产品递进 MVP-A/B/C/D 取代旧 M0-9；H1/H2 属 MVP-C |
| `docs/architecture/assumptions.md` | **DEPRECATED** | 标记 DEPRECATED，历史追溯 |
| `docs/concepts/README.md` | **新建** | detector 进入 Scanner 的强制流程、concept_provenance vs implementation_provenance |

---

## 三、废弃了哪些文档

- **`docs/architecture/assumptions.md` → 标记 DEPRECATED**
  - 其旧表述（多市场 外汇/加密/美股、5m 主图 + 1h 背景、三 provider 并行、detector 统一 score、Level 1-5、Milestone 0-9 一次性路线）已过时。
  - 权威以 `PRD.md`、`content-provenance-policy.md`、`brooks-system-design-implications.md` 为准；保留仅用于历史追溯。
  - 其技术栈与"不实盘/不自动交易/不泄露未来"边界仍有参考价值。

---

## 四、发现的旧设计（Batch 0-6 修正项汇总）

审计中发现并修正了以下旧设计/表述冲突：

1. **5m + 1h 双图同步分析** → 修正为 **SPY 5m 单图**（唯一核心决策图）；1h 归 Research Extension。
2. **三 provider / 多市场并行**（Binance/Dukascopy/Alpaca 同时强调） → 收敛为 **SPY**；provider abstraction 保留，不同时接入。
3. **detector 强制输出 0~1 score** → 改为支持多 result type（boolean/categorical/ordinal/continuous/count/evidence_set），evidence 比 score 重要。
4. **H1/H2 被放到后期（M8 / Later 复杂 detector）** → 修正为 **H1/H2/L1/L2 属 Level 3 基础路线**（Brooks Source，learning early · automation middle，依赖 swing/leg/pullback），非 Research。
5. **Level 5 复杂形态误标 Research Extension** → 修正为 **Level 5 = Brooks Source + Later**（wedge/always-in/climax/final flag 是 Brooks 原书概念）。
6. **source_confidence C 混用于 Product Design** → 弃用 C；对 Product/Engineering Design 改用 `design_rationale` / `derivation_level`。
7. **关键 Brooks claims 缺 book_refs**（单5m、premarket、day types、two reasons、always-in、trader's equation、probability terminology） → 已在 brooks 文档补 book_refs，不足者标 `source_confidence=D / 原书待核查`。
8. **Predict First 无 sampling bias 定义** → 补无未来偏差触发方式（用户主动/每根 bar/固定 N 根/预置规则）+ candidate-sampled 会话必须标 `sampling_mode: candidate_based / sampling_bias: true`。
9. **缺 instrument metadata** → 补 Instrument Metadata（tick_size/feed_consolidated/quote_side/calendar_id 等），"one tick" 依据的 detector 必须依赖。
10. **巨型 MarketStructureEngine 类** → 改为 shared structure primitives + versioned structure profile + thin candidate detectors（模块化，非黑箱）。
11. **单一 `Brooks Core` 标签**同时表示来源/重要性/开发阶段 → 拆为 Knowledge Provenance × Delivery Priority 两维度。
12. **防前视靠前端隐藏未来K线** → 改为**服务端权威 replay cursor**；集成测试证明；隐藏价格不模拟失忆。
13. **sealed exam set / blind recheck / MFE-MAE 误标 Brooks Source** → 归入 Product / Learning / Research Analytics 层。
14. **SPY 组合直接标 Brooks Source** → 拆开：Brooks 方法（Brooks Source）+ SPY 选择（Product Design）。

---

## 五、未决问题

- **3 个 open questions**，均在 `docs/open-questions.md`：
  - **OQ-01**：SPY feed "一跳"精度（DATA FIDELITY BLOCKER，MVP-C 前验证）
  - **OQ-02**：部分 Brooks claims 缺精确 book_refs（source_confidence=D，MVP-C 前补齐）
  - **OQ-03**：Level 5 复杂形态机械定义边界（实现 Level 3 时决策）
- **均不阻塞 MVP-A**。

---

## 六、Milestone 1 blocker

**无。** 全仓文档审计未发现任何阻塞 Milestone 1 的 blocker：

- no-lookahead / 数据模型 / Concept Spec 相关约束均已明确；
- 3 个 open questions 均为 MVP-A 之后（MVP-C / Later / Research）的验证项；
- 四份 canonical 文档互相一致。

---

## 七、最终结论

> **全仓文档已与四份 canonical 文档一致。**

四份 canonical 文档：

1. `docs/product/PRD.md`（产品需求）
2. `docs/content-provenance-policy.md`（内容来源策略）
3. `docs/architecture/brooks-system-design-implications.md`（Brooks 体系设计启示）
4. `docs/product/docs-consistency-review.md`（一致性核对表）

所有设计文档（架构、ADR、领域模型、数据合同、路线图、concepts）已对齐上述 canonical；过时文档（assumptions.md）已标记 DEPRECATED；未决问题已登记且不阻塞 MVP-A。**Milestone 1 可进入。**