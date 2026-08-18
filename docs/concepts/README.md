# 概念规格索引 · Concept Specs

> 本目录（`docs/concepts/`）是**每个要进入 Scanner 的 detector 都必须先有 Concept Spec（概念规格）**的唯一登记处。
> 规范依据：`docs/content-provenance-policy.md` 第九节（概念卡片模板）与 PRD 第五章、brooks-system-design-implications 第四章的 detector 强制流程。
> 相关计划批次：review-state.md Batch 4（concepts / detectors）。

---

## 一、为什么必须先写 Concept Spec

**不允许 AI 直接从自然语言概念跳到 production detector。**

任何 detector 在正式进入 Scanner 之前，必须依次经过下列 10 步强制流程：

1. **Concept Spec** → 2. 原书依据确认 → 3. Mechanical Definition → 4. 正例 → 5. 反例 → 6. 边界案例 → 7. knowable_at 定义 → 8. 单元测试 → 9. 人工图表验证 → 10. detector version freeze

第 1 步即为本目录的 `<concept>.md` 概念规格。没有通过本规格的 detector **不得**进入 Scanner（PRD §五、brooks-system-design-implications §四）。

> ⚠️ 概念规格不是可有可无的文档，而是实现与验证之间的**强制关卡**。

---

## 二、关键：两个来源字段必须区分

每个 Concept Spec 必须同时、且**明确区分**两个来源字段：

| 字段 | 含义 | 典型取值 |
|---|---|---|
| `concept_provenance` | **概念的来源**——这个概念源自哪里？ | `Brooks Source`（原书依据）/ `Mechanical Approximation` / `Product / Engineering Design` / `Research Extension` |
| `implementation_provenance` | **实现来源**——用于程序的这个机械化近似来自哪里？ | 多为 `Mechanical Approximation` |

> **核心原则**：`concept_provenance`（概念来源）与 `implementation_provenance`（实现来源）**不是同一件事**。
> 一个概念可以是 `Brooks Source`（来自原书），但其程序化实现属于 `Mechanical Approximation`（机械近似），**并不等于 Brooks 本人的完整主观判断**（见 content-provenance-policy §二）。

**反例（不允许）**：仅填 `provenance: Brooks Source` 就代表"概念来源 + 实现来源"都搞定——这是维度混淆，会跳过实现近似这一层。

---

## 三、Concept Spec 模板

每个 detector 在 `docs/concepts/<concept>.md`（例如 `docs/concepts/h2.md`）中至少包含以下字段（对应 content-provenance-policy.md 第九节）：

```yaml
concept_id:                # 唯一标识，如 h2
english_term:              # 英文术语，如 "H2" / "high 2"
chinese_term:              # 中文术语，如 "高点二"
concept_provenance:        # 概念的来源：Brooks Source / Mechanical Approximation / Product / Research
implementation_provenance: # 实现来源：多为 Mechanical Approximation
source_confidence:         # 仅对 Brooks Source 使用：A / B / D
book_refs:                 # 原书引用（Brooks Source 必填）：
                           #   book / chapter / section / figure / pdf_page / print_page(null) / chunk_id / chunk_hash
definition_summary:        # 概念定义摘要
dependencies:              # 依赖的其他概念 / 结构层（如 swing、leg、pullback）
mechanical_definition:     # 机械定义：程序如何判定，含已知歧义说明
known_ambiguities:         # 已知歧义 / 边界模糊处
event_at:                  # 事件发生时间定义（实际发生）
knowable_at:               # 系统首次可知时间（防前视，只能在此之后展示）
result_type:               # boolean / categorical / ordinal / continuous / count / evidence_set
positive_examples:         # 正例（原书或人工确认）
negative_examples:         # 反例
edge_cases:                # 边界案例
learning_priority:         # very_early / early / middle / later
automation_priority:       # very_early / early / middle / later
automation_status:         # 当前自动化状态
version:                   # 规格版本
```

**字段规则摘要（content-provenance-policy.md）：**

- `concept_provenance` 与 `implementation_provenance` 必须同时存在、明确区分。
- `source_confidence`（A / B / D）**只对** `Brooks Source` 使用，且必须同时提供 `book_refs`；`C` 不再用于 source_confidence。
- `book_refs` 中 `print_page` 只有在确定存在时才填写，否则为 `null`，**禁止编造印刷页码**；`pdf_page` 可用则记录。
- `learning_priority` 与 `automation_priority` 是**两个正交字段**：应该早学 ≠ 应该早自动化（如 trend vs range：learning very_early，automation later）。

---

## 四、进入 Scanner 的准入条件（Checklist）

- [ ] 已存在 `docs/concepts/<concept>.md`
- [ ] `concept_provenance` 与 `implementation_provenance` 均已明确区分
- [ ] `Brooks Source` 概念已提供 `book_refs` 且 `source_confidence ∈ {A, B, D}`
- [ ] 已定义 `knowable_at`（防前视）
- [ ] 已提供 positive / negative / edge cases
- [ ] 已通过原书依据确认 → Mechanical Definition → 单元测试 → 人工图表验证
- [ ] 已冻结 detector version（`detector version freeze`）

---

## 五、索引

> 此表由新概念规格加入时同步登记。

| concept_id | english_term | concept_provenance | automation_priority | automation_status | 规格文件 |
|---|---|---|---|---|---|
| bar_anatomy | bar anatomy / bull-bear bar | Brooks Source | very_early | implemented (v0.1.0) | `bar-anatomy.md` |
| doji | doji | Brooks Source | very_early | implemented (v0.1.0) | `doji.md` |
| trend_bar | trend bar | Brooks Source | very_early | implemented (v0.1.0) | `trend-bar.md` |
| inside_bar | inside bar | Brooks Source | very_early | implemented (v0.1.0) | `inside-bar.md` |
| outside_bar | outside bar | Brooks Source | very_early | implemented (v0.1.0) | `outside-bar.md` |
| bar_pattern | ii / iii / ioi | Brooks Source | early | implemented (v0.1.0) | `ii-iii-ioi.md` |
| signal_bar_evidence | signal bar (evidence set) | Brooks Source + Product Design | early | implemented (v0.1.0) | `signal-bar-evidence.md` |
| swing | swing high / swing low | Brooks Source | early | implemented (v0.1.0) | `swing.md` |
| pullback_leg | pullback / leg | Brooks Source | early | implemented (v0.1.0) | `pullback-leg.md` |
| hl_counting | High 1-4 / Low 1-4 | Brooks Source | middle | implemented (v0.1.0) | `hl-counting.md` |
| trend_lines | trend line / channel line | Brooks Source | middle | implemented (v0.1.0) | `trend-lines.md` |

---

*本文件是 `docs/concepts/` 目录的入口与强制流程说明。所有 detector 进入 Scanner 前必须先满足本节要求。*