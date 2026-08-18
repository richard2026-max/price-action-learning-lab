# Concept Spec · swing（摆动高低点）

```yaml
concept_id: swing
english_term: swing high / swing low
chinese_term: 摆动高点 / 摆动低点
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: B
book_refs:
  - { book: T, section: "术语表 swing 条目", pdf_page: 15, print_page: "xiii区" }
definition_summary: 局部极值：swing high 是高点高于前后各 N 根K线的K线（低点对称）。leg 与 bar counting 的结构基元。
dependencies: []
mechanical_definition: >-
  pivot 强度 N=3（参数 swing_lookback）：bar i 为 swing_high 当
  high[i] > high[j]（j∈[i-N,i-1]）且右侧已出现 ≥N 根均 high < high[i]。
  右侧未满 N 根不确认；右侧出现更高高点则该候选失效（superseded）。
  等高点（严格大于失败）保守不判。
known_ambiguities: N=3 为工程参数；原书 swing 判定主观。
event_at: 极值K线 ts_close_utc
knowable_at: 极值后第 N 根收盘（右侧确认）——晚于 event_at
knowable_precision: bar_close
result_type: categorical        # swing_high | swing_low（事件型）
positive_examples: 3 根右侧更低高点后确认 swing_high。
negative_examples: 右侧出现更高高点 → superseded，不发出。
edge_cases: 等高点不判；首尾不足 N 根不判。
learning_priority: very_early
automation_priority: early
automation_status: implemented
version: 0.1.0
```
