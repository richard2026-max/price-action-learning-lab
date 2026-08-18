# Open Questions · 未决问题登记

> 记录审计过程中无法确定、需要进一步原书核查或数据验证的问题。
> 若某项不影响 MVP-A → 不阻塞开发；若影响 no-lookahead / 数据模型 / Concept Spec → 标 blocker。
> 本文件是 Milestone 1 前全仓一致性审计（Batch 7 收尾）的未决问题结论。

```yaml
review_version: 0.2.0
audit_batch: batch-14
audit_status: closed
```

## 问题清单

### OQ-01：SPY 数据源/feed 的"一跳"级别价格行为研究能力

- **question**: 当前 SPY 数据源/feed 的 high/low 质量，是否足以支撑未来"一跳突破"、entry/stop 级别的价格行为训练？
- **why_it_matters**: Brooks 的微趋势线突破、一 tick 失败突破等依赖 high/low 数据精度；若数据被二次聚合或丢失单跳，机械近似会失真。
- **affected_documents**: data-contracts-and-api.md、MVP-A 数据摄取
- **current_claim**: 未确定（无证据证明当前 provider/feed 满足一跳精度）
- **source_status**: OPEN QUESTION / **DATA FIDELITY BLOCKER**
- **required_validation**:
  - 验证 Alpaca(SPY) feed 是否 consolidated（`feed_consolidated`）；
  - 是否含 RTH + 盘前盘后（premarket/postmarket）；
  - high/low 是否一跳级（tick-level）；
  - 是否需要 IEX / 其他 feed；
  - 是否需按 quote/trade semantics（`quote_side`：bid/ask/mid/last）处理；
  - 以上对应 data-contracts-and-api.md §1.2 Instrument Metadata 与 §1.4 Data Fidelity 声明。
- **blocking_milestone**: **已验证（Batch 14，2019-2021 语料）**——成交量交叉核对：2020-03-09 204.4M / 03-12 255.6M，与公开合并磁带记录吻合 ±1%；OHLC 违规 0、零波幅 0。结论：**5m 结构层（swing/leg/pullback/H-L counting）精度充足**。tick 级微观研究仍需 tick 数据源（后置）。

### OQ-02：部分 Brooks 关键判断缺精确 book_refs

- **question**: 以下 Brooks claims 缺少精确 pdf_page 引用（部分已有章节级依据、标 `source_confidence=B`，页码待补；完全未核查者标 `D`）：
  - 单5分钟图、premarket、day types、two reasons、always-in、trader's equation、probability terminology、不看新闻、1分钟图、多周期相关表述。
- **why_it_matters**: 项目最高目标是忠实 Brooks，需可追溯引用；精确页码需对照三本原书 PDF 实际页码，**禁止 AI 编造印刷页码**。
- **affected_documents**: brooks-system-design-implications.md 及各 detector Concept Spec
- **current_claim**: brooks 文档中已有章节级依据的条目标 `B` 并注 `book_refs`（章节级），其余标 `D / 原书待核查`；两者页码级引用均待补
- **source_status**: 原书待核查（source_confidence=D）
- **required_book_check**: 对照 Trends / Ranges / Reversals 原书 PDF 补充 `book_refs`（chapter / section / figure / pdf_page）
- **blocking_milestone**: **H1/H2 已补页码级引用（Batch 14）**：术语表定义 Trends PDF p19（印刷 xvii）；核心讨论 PDF p66（正文 p34）/p83（Figure PI.1）。second entry → 术语表 PDF p23；swing/pullback → p15；leg → p19；trend line → p16。其余概念待实现时逐条补。

### OQ-03：Level 5 复杂形态的机械定义边界

- **question**: wedge / always-in / climax 等列为 Brooks Source + Later，但其部分形态（如 wedge pullback）与 Level 3 的 pullback / bar counting 有交集，机械定义边界未完全明确。
- **why_it_matters**: 避免实现 Level 3 时误把 Level 5 复杂形态过早机械化。
- **affected_documents**: brooks-system-design-implications.md、docs/concepts/
- **current_claim**: Level 5 = Brooks Source + Later（非 Research Extension）
- **source_status**: 待实现 Level 3 时作为决策点
- **blocking_milestone**: **不阻塞 MVP-A**

---

## 结论

**No blocking open questions for MVP-A.**

现有 3 个 OQ 均为 Later / Research 阶段或 MVP-C 前需验证项，**不阻塞**第一阶段 Replay Trainer（MVP-A）开发：

| OQ | 类型 | 阻塞 MVP-A？ | 何时需解决 |
|---|---|---|---|
| OQ-01 | DATA FIDELITY BLOCKER（数据验证） | ❌ 否 | MVP-C 前 |
| OQ-02 | 原书待核查（source_confidence=D） | ❌ 否 | MVP-C（Concept Spec）前 |
| OQ-03 | 机械定义边界（决策点） | ❌ 否 | 实现 Level 3 时 |

> **Milestone 1 blocker：无。** 全仓文档审计（Batch 0-7）已完成，未发现阻塞 Milestone 1 的未决问题。