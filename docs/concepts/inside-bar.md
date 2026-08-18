# Concept Spec · inside_bar（内包线）

```yaml
concept_id: inside_bar
english_term: inside bar
chinese_term: 内包线
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: A        # 术语表直接定义，且机械定义与其逐字对应（含等于）
book_refs:
  - book: T
    section: List of Terms Used in This Book（inside bar 条目）
    pdf_page: null
    print_page: null
definition_summary: >
  高点不高于（或等于）前一根K线高点、低点不低于（或等于）前一根K线低点的K线。
  常为市场暂停/蓄力；在趋势中可为旗形，在区间末端可为突破模式组成部分。
dependencies: []
mechanical_definition: >
  inside := high ≤ prev_high 且 low ≥ prev_low（闭区间，tie_policy=inclusive，
  与原书"或等于"表述一致）。首根K线（无前根）不判定。
known_ambiguities: 无（原书定义即含等于；本项目不做 strict 变体，如需研究再加参数）。
event_at: 该 bar 的 ts_close_utc（高低点在收盘时才最终确定）
knowable_at: 同 event_at（bar_close）
knowable_precision: bar_close
result_type: boolean
positive_examples: 前根 H=100/L=98，当前 H=99.5/L=98.2 → true。
negative_examples: 当前 H=100.2（越过前高）→ false。
edge_cases: 当前 H==prev_high 且 L==prev_L（完全等幅，同时也是 outside）→ inside=true 且 outside=true，二者并存由证据呈现，不强行互斥。
learning_priority: very_early
automation_priority: very_early
automation_status: implemented
version: 0.1.0
```
