# Concept Spec · breakout（突破与突破回抽）

```yaml
concept_id: breakout
english_term: breakout / breakout pullback / failed breakout
chinese_term: 突破 / 突破回抽 / 失败突破
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: A
book_refs:
  - book: T
    section: "术语表 breakout 条目"
    pdf_page: 10
    print_page: "x区"
  - book: T
    section: "术语表 breakout pullback / failed failure 条目"
    pdf_page: 11
    print_page: "xi区"
definition_summary: >-
  breakout：当前K线高或低超越了某个有意义的先前价位（如摆动高低点）。
  breakout pullback：突破后数根K线内的小回抽（1-5根），预期突破恢复。
  failed breakout：突破后价格反转回到原区间，被困者被迫亏损离场。
dependencies:
  - swing
mechanical_definition: >-
  v0.1.0 基于已确认 Swing 序列的机械判定：
  1. bull_breakout := close[i] > 最近确认的 swing_high.price
     （且前一根 close ≤ swing_high，即"本次穿越"而非持续穿越）
  2. bear_breakout := close[i] < 最近确认的 swing_low.price
     （且前一根 close ≥ swing_low）
  3. failed_bull_breakout := bull_breakout 发出后 ≤3 根内 close 跌回 swing_high 之下
  4. failed_bear_breakout := bear_breakout 发出后 ≤3 根内 close 升回 swing_low 之上
known_ambiguities: "有意义先前价位"收敛为最近确认 swing 极值；趋势线突破由 trend_lines detector 单独覆盖。
event_at: bar 收盘（穿越确认时刻）
knowable_at: 同 event_at（bar_close）；failed 需等待后续 bar 收盘确认
knowable_precision: bar_close
result_type: categorical   # bull_breakout | bear_breakout | failed_bull_breakout | failed_bear_breakout
positive_examples: >-
  前日高点为确认 swing_high=110，当前 close=111 且前一根 close≤110 → bull_breakout。
negative_examples: 价格持续在 swing_high 上方运行多根后才检查 → 不触发（非首次穿越）。
edge_cases: >-
  恰好等于 swing_high → 不算突破（需严格大于/小于）；
  failed 判定窗口 3 根可调。
learning_priority: early
automation_priority: middle
automation_status: implemented
version: 0.1.0
```
