# Concept Spec · hl_counting（H1-H4 / L1-L4）

```yaml
concept_id: hl_counting
english_term: "High 1/2/3/4 · Low 1/2/3/4 · second entry"
chinese_term: 高点/低点计数 · 二次入场
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: B
book_refs:
  - { book: T, section: "术语表 high 1 条目", pdf_page: 19, print_page: xvii }
  - { book: T, section: "术语表 second entry 条目", pdf_page: 23, print_page: "xxi区" }
  - { book: T, section: "Introduction 回调讨论", pdf_page: 66, print_page: 34 }
  - { book: T, section: "Figure PI.1 Two-Legged Pullback", pdf_page: 83, print_page: 51 }
definition_summary: >-
  术语表原文：high 1 是多头旗或区间底部附近、高点高于前一根K线的K线；若随后有
  更低高点（可隔一根或数根），则此次修正中下一根高点高于前一根高点的K线是
  high 2。第 3、4 次为 high 3、4。low 1/2/3/4 对称。second entry 通常指 H2/L2。
dependencies: [bar_anatomy, pullback_leg]
mechanical_definition: >-
  上下文（pullback_leg 的净漂移方向）为 bull 时计 H 系，bear 时计 L 系：
  - H_n += 1 当 high[i] > high[i-1] 且自上次计数以来存在过至少一根更低高点
    （high[k] < high[k-1]）；发出 H1→H2→…事件，重置标记。
  - 连续更高高点只计第一次（Brooks：中间须有更低高点隔开）。
  - 上下文翻转 → 计数器归零。
  L 系对称（low[i] < low[i-1] 且其间存在过更高低点）。
  evidence 标注 second_entry=True（H2/L2）。
known_ambiguities: >-
  ①净漂移上下文为强近似；②"旗形/区间底部附近"的位置条件未纳入（需 swing 层，
  v0.2）；③术语表允许隔根计数，本实现即如此。
event_at: 计数K线收盘
knowable_at: 同 event_at（bar_close，计数即知，无右侧确认）
knowable_precision: bar_close
result_type: categorical        # H1..H4 / L1..L4（事件型）
positive_examples: 上行旗：低高、低高、更高高 → H1；再低高、更高高 → H2（second entry）。
negative_examples: 连续更高高三根 → 仅第一根计 H1。
edge_cases: 上下文翻转归零；等高/等低不触发（严格不等号）。
learning_priority: early
automation_priority: middle
automation_status: implemented
version: 0.1.0
```
