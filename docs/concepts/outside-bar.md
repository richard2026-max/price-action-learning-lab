# Concept Spec · outside_bar（外包线）

```yaml
concept_id: outside_bar
english_term: outside bar
chinese_term: 外包线 / 吞没线
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: A        # 术语表直接定义，机械定义与其逐字对应（含等于）
book_refs:
  - book: T
    section: List of Terms Used in This Book（outside bar 条目）
    pdf_page: null
    print_page: null
definition_summary: >
  高点高于或等于前一根高点、且低点低于或等于前一根低点的K线。
  分 outside up bar（收盘高于开盘）与 outside down bar。
dependencies: [bar_anatomy]
mechanical_definition: >
  outside := high ≥ prev_high 且 low ≤ prev_low（闭区间，与原书一致）；
  evidence.direction = outside_up（close>open）/ outside_down（close<open）/ neutral。
known_ambiguities: 外包后跟随行为（outside bar 后常现 inside bar，即 ioi 模式）不在本 detector 判定范围。
event_at: 该 bar 的 ts_close_utc（需收盘才能确认低点未被收回——机械上以收盘高低点为准）
knowable_at: 同 event_at（bar_close）
knowable_precision: bar_close
result_type: boolean
positive_examples: 前根 H=100/L=98，当前 H=100.5/L=97.5 → true。
negative_examples: 仅越过高点未跌破低点 → false（那是 breakout 范畴，非 outside）。
edge_cases: 与前根完全等幅（H==prev_H, L==prev_L）→ 同时为 inside 与 outside（见 inside-bar edge_cases）。
learning_priority: very_early
automation_priority: very_early
automation_status: implemented
version: 0.1.0
```
