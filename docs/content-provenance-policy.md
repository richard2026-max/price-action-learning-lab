# 内容来源策略 · Content Provenance Policy

> **版本**：0.3.0（与 PRD / brooks-system-design-implications 同轮校正，版本对齐）
> **用途**：正式定义本项目的**内容来源分层**、**source confidence 证据等级**、**learning/automation 优先级**与**引用规则**。
> **适用范围**：PRD.md、brooks-system-design-implications.md、docs-consistency-review.md 及本项目所有设计文档。

---

## 一、两个独立维度

本项目**不再**使用单一 `Brooks Core` 标签同时表示"内容来源"、"重要性"和"开发阶段"。

统一拆成两个正交维度：

1. **Knowledge Provenance / 内容来源**——这条内容来自哪里？
2. **Delivery Priority / 开发优先级**——这条内容什么时候开发？

一个概念可以同时是：
- `Brooks Source + Later`（例如 wedge：是 Brooks 原书概念，但第一阶段后置开发）
- `Product / Engineering Design + MVP`（例如服务端 replay cursor）

> **不能因为暂时不开发，就把它归为 Research Extension。**

---

## 二、内容来源四层分类（Knowledge Provenance）

### 1. `Brooks Source`
**定义**：能够直接从 Brooks 三本原书中找到依据的概念、交易方法、术语或原则。

**示例**：trend / trading range、bar-by-bar reading、20 EMA、signal bar、entry bar、H1/H2/L1/L2、wedge、always-in、spike and channel、final flag、trader's equation。

### 2. `Mechanical Approximation`
**定义**：为了让程序能够识别 Brooks 概念而建立的机械化近似。

**示例**：trend score、swing 算法、pullback state machine、H2 detector、always-in candidate detector、breakout strength evidence aggregation。

> **必须明确**：Mechanical Approximation **不等于** Brooks 本人的完整主观判断。

### 3. `Product / Engineering Design`
**定义**：项目为了学习真实性、可复现性、安全性和用户体验自行设计的机制。

**示例**：服务端 replay cursor、sealed exam set、blind recheck、deterministic seed、input_slice_hash、PDF Figure extraction、SQLite / DuckDB、Predict First Reveal Later、autoscale 防未来数据、30/60/90 天复习机制。

> 这些**不能标记为 Brooks Source**。

### 4. `Research Extension`
**定义**：明确超出当前 Brooks 学习核心的个人研究扩展。

**示例**：1小时多周期图、外汇/crypto 跨市场研究、volume 因子研究、AI 自动生成策略、forward statistics、其他交易体系、非 Brooks 指标。

> Research Extension = Brooks 原书核心之外的**个人实验**。

---

## 三、Source Confidence（证据等级）与设计依据

### 对 Brooks Source claim（原书证据状态）

只对 **Brooks Source** 使用 `source_confidence`，且**必须同时提供 `book_refs`**：

| 等级 | 含义 |
|---|---|
| `A` | 原书有明确直接表述 |
| `B` | 原书多处一致支持，需要概括 |
| `D` | 尚未完成充分核查（标记 `status: 原书待核查`） |

> `C` **不再用于 source_confidence**（避免让它看起来像原书证据等级）。

**示例**：
```yaml
claim: Brooks uses a 20 EMA
provenance: Brooks Source
source_confidence: A
book_refs:
  - book: T
    chapter: ...
    section: ...
    pdf_page: ...
    print_page: null
```

### 对 Product / Engineering Design（设计依据）

对 Product / Engineering Design 类内容，**不填 source_confidence**，改用：

```yaml
design_rationale:   # 设计理由
derived_from:       # 推导来源（列表）
```

**示例**：
```yaml
claim: server-authoritative replay cursor
provenance: Product / Engineering Design
design_rationale: prevent future-data leakage by construction
derived_from:
  - no-lookahead learning requirement
```

> 若希望保留"推导层级"，使用字段名 `derivation_level`（如 C），而**不是** `source_confidence`。

### 规则
- 对于"单5分钟图、SPY、premarket、day types、two reasons、always-in、trader's equation、probability terminology"等关键判断，应尽量附：book、chapter、section、figure、print/pdf page（可靠时）。
- 不得因为模型已有知识、旧文档写过或"看起来像 Brooks"而自动标 A/B。
- 当前资料不足时标记 `source_confidence: D` 且 `status: 原书待核查`，**不要自行补全**。

---

## 四、两个优先级字段

### `learning_priority`（学习内容顺序）
用户在学习路径上**何时应学到**该概念。

取值参考：`very_early` / `early` / `middle` / `later`

### `automation_priority`（自动化开发顺序）
程序在何时应**自动识别**该概念。

取值参考：`very_early` / `early` / `middle` / `later`

> **核心原则：应该早学，不等于应该早自动化。**
> 高度主观、依赖上下文的概念（如 trend vs trading range、Always In、trader's equation）应很早就学，但机械化识别应较晚——先积累人工标注。

**示例**：
```yaml
concept: trend_vs_trading_range
provenance: Brooks Source
learning_priority: very_early
automation_priority: later
reason: 高度依赖上下文，机械识别需要先积累人工标注
```
```yaml
concept: inside_bar
provenance: Brooks Source
learning_priority: early
automation_priority: early
reason: 定义客观，容易可靠程序化
```

---

## 五、知识库引用协议（结构化引用）

不简单要求"AI 必须给书名、章节、页码"——不同 PDF 未必存在可靠印刷页码。

统一使用结构化引用：

```json
{
  "book": "R",
  "chapter": 5,
  "section": "...",
  "figure": "5.7",
  "pdf_page": 118,
  "print_page": null,
  "chunk_id": "...",
  "chunk_hash": "..."
}
```

**规则**：
- `pdf_page`：PDF 物理页，可用则记录；
- `print_page`：只有确定存在时才填写；
- 不存在时必须为 `null`；
- **禁止 AI 编造印刷页码**；
- Figure 可单独引用；
- chunk 必须可追溯。

**回答展示优先顺序**：
`Book → Chapter → Section → Figure → Page（可靠时）`
而不是强迫任何回答都有印刷页码。

---

## 六、知识库 Figure 功能优先级

"Brooks 图文关联"设计正确，但**不阻塞 Replay MVP**。

### Early
- PDF 文本提取
- glossary
- chapter/section
- 基础引用

### Later
- Figure extraction
- chunk ↔ figure 自动关联
- 图表显示原书 Figure
- 原书案例历史行情重建

---

## 七、部分机制的归类修正

| 机制 | 正确归类 |
|---|---|
| sealed exam set | Product / Learning Design · Early（数据被浏览即污染，尽早建立保护） |
| blind recheck | Product / Learning Design · Later / Early-Later（数据模型早期预留 original_annotation / recheck_annotation / annotation_version / hidden_previous_answer；30/60/90 日调度后置） |
| MFE / MAE | Product / Research Analytics（复盘用，不代表 Brooks 核心术语体系；无明确原书依据则不标 Brooks Source） |

> 适用于所有现代量化统计字段：**若不能从原书找到明确依据，就不标记为 Brooks Source。**

---

## 八、SPY 表述精度（拆开 Provenance）

第一阶段锁定 **SPY + 5m**，不改变。但**不得把"SPY 5m 单图"整个组合直接标成 Brooks Source**。必须拆开：

### Brooks Source（原书可查依据）
Brooks 原书涉及的部分，例如：
- Brooks 对5分钟日内图的使用；
- 单一核心决策图的相关主张；
- 20 EMA；
- 与开盘、前日、盘前有关的 Brooks 概念（opening context、previous day levels、premarket、session behavior）。

### Product / Engineering Design（项目实施决策）
本项目第一阶段选择：
```text
SPY
```
作为首个正式训练品种，是**项目实施决策**，属 Product / Engineering Design。

**正确表达**：
> Brooks 的相关方法与美股指数日内语境为本项目提供学习依据；本项目选择 SPY 作为第一阶段训练品种，是 Product Design 决策，用于尽量贴近该语境，并不意味着 Brooks 方法只适用于 SPY。

**不要写成**："Brooks 体系只能用于 SPY。" 未来市场扩展不改变 Brooks 学习内容。

---

## 九、汇总：概念卡片模板（Concept Spec）

任何 detector 在正式进入 Scanner 之前，必须依次经过：
1. Concept Spec → 2. 原书依据确认 → 3. Mechanical Definition → 4. 正例 → 5. 反例 → 6. 边界案例 → 7. knowable_at 定义 → 8. 单元测试 → 9. 人工图表验证 → 10. detector version freeze

建立统一 `docs/concepts/<concept>.md`（例如 `docs/concepts/h2.md`），至少包含：

```yaml
concept_id:
english_term:
chinese_term:
concept_provenance:        # 概念的来源：Brooks Source / Mechanical Approximation / Product / Research
implementation_provenance: # 实现来源：多为 Mechanical Approximation
source_confidence:         # 仅对 Brooks Source 使用：A / B / D
book_refs:                 # 原书引用（Brooks Source 必填）
definition_summary:
dependencies:
mechanical_definition:
known_ambiguities:
event_at:
knowable_at:
result_type:
positive_examples:
negative_examples:
edge_cases:
learning_priority:         # very_early / early / middle / later
automation_priority:       # very_early / early / middle / later
automation_status:
version:
```

> **核心原则**：不允许 AI 直接从一个自然语言概念跳到 production detector。先写 Concept Spec，再写代码。

---

## 十、Source Confidence 判定清单（关键 Brooks 判断）

以下判断应按此规则标注证据等级；资料不足时标记 `D / 原书待核查`：
- 单5分钟图、SPY、premarket、day types、two reasons、always-in、trader's equation、probability terminology。

---

*本文档是内容来源分层的唯一权威。所有设计文档必须遵循本策略。*