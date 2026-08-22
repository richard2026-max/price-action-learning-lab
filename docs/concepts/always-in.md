# Concept Spec · always_in（时刻在场方向状态机）

```yaml
concept_id: always_in
english_term: always in / always-in long / always-in short
chinese_term: 时刻在场方向
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: A        # 术语表直接定义 + Trends PDF p15 原文逐字核对
book_refs:
  - book: T
    section: "List of Terms Used in This Book（always in 条目）"
    pdf_page: 15
    print_page: "xv"
definition_summary: >-
  原书术语表（Trends PDF p15，印刷页 xv）原文：
  "If you have to be in the market at all times, either long or short, this is whatever
  your current position is (always in long or always in short). If at any time you are
  forced to decide between initiating a long or a short trade and are confident in your
  choice, then the market is in always-in mode at that moment. Almost all of these trades
  require a spike in the direction of the trend before traders will have confidence."
dependencies:
  - bar_anatomy
  - swing
  - pullback_leg
  - hl_counting
mechanical_definition: >-
  v0.1.0 状态机（Brooks 定义直译 + 结构层信号组合）：

  输入：当前K线收盘时的结构层上下文（_context_direction）、H/L 计数序列、swing 序列。

  判定规则（优先级从高到低）：
  1. 若最近 H/L 计数出现 H3/H4 且方向为 up → always_in_long；
  2. 若最近 H/L 计数出现 L3/L4 且方向为 down → always_in_short；
  3. 若已确认 swing 序列满足 HH+HL（连续两个更高高+更高低）→ always_in_long；
  4. 若已确认 swing 序列满足 LH+LL（连续两个更低高+更低低）→ always_in_short；
  5. 否则 → transition（不确定，即"非 always-in 模式"，对应区间/模糊地带）。

  状态翻转条件：当判定结果与上一状态不同时发出事件（event 型 detector）。
  连续同向不重复发事件；transition 不视为独立方向，仅作为重置标记。

known_ambiguities: >-
  ①原书强调 spike 是建立信心的前提——本近似以 strong trend_bar 或 H3/H4 计数代替，
  属于保守近似；②"有信心"是主观概念，机械化为结构层 HH/HL 或 LH/LL 的双确认。
event_at: 触发翻转的K线收盘
knowable_at: 同 event_at（bar_close）
knowable_precision: bar_close
result_type: categorical   # always_in_long | always_in_short | transition（事件型：仅翻转时发出）
positive_examples: >-
  连续 HH+HL 后出现 H2 → always_in_long；随后出现 LH+LL → always_in_short（翻转事件）。
negative_examples: 横盘区间内无明确方向 → 无事件输出（保持上一次状态直到新证据出现）。
edge_cases: 首根K线无历史 → 输出 transition 作为初始状态；上下文 flat 时维持上次状态不变。
learning_priority: very_early
automation_priority: later   # PRD 明确标注 later（依赖完整结构层），现已就绪
automation_status: implemented
version: 0.1.0
```
