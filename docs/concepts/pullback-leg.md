# Concept Spec · pullback_leg（回调与腿）

```yaml
concept_id: pullback_leg
english_term: pullback / leg
chinese_term: 回调 / 腿
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: B
book_refs:
  - { book: T, section: "术语表 pullback 条目", pdf_page: 15, print_page: "xiii区" }
  - { book: T, section: "术语表 leg 条目", pdf_page: 19, print_page: "xvii区" }
  - { book: T, section: "术语表 bar pullback 条目（单K线低点破前低定义）" }
definition_summary: >-
  leg：波段内同向一段（swing 到 swing）。pullback：逆趋势段——术语表 bar pullback：
  上升趋势中一根K线低点低于前一根低点即为 bar pullback（下降对称）。
dependencies: [bar_anatomy]
mechanical_definition: >-
  v0.1.0 采用术语表单K线定义：bull 上下文中 pullback_bar := low[i] < low[i-1]；
  bear 上下文中 := high[i] > high[i-1]。上下文 v0.1.0 用简化规则：
  近 20 根收盘净漂移方向（close[cursor] vs close[cursor-20]）。
  leg 划分（swing-to-swing）后置 v0.2（待 swing 修订链稳定）。
known_ambiguities: 净漂移上下文是强近似；正式版应基于确认 swing 序列。
event_at: bar 收盘
knowable_at: 同 event_at（bar_close）
knowable_precision: bar_close
result_type: categorical        # bull_pullback | bear_pullback | none
positive_examples: 净上行中低点破前低 → bull_pullback。
negative_examples: 净下行中低点破前低 → 趋势延续，输出 none。
edge_cases: 净漂移为零 → none；等低点不算破（严格小于）。
learning_priority: very_early
automation_priority: early
automation_status: implemented
version: 0.1.0
```
