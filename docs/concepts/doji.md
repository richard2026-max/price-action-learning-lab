# Concept Spec · doji（十字星）

```yaml
concept_id: doji
english_term: doji
chinese_term: 十字星
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: B        # 术语表直接定义，但"小实体"的量化界限原书按 tick 数与图型主观给出
book_refs:
  - book: T
    section: List of Terms Used in This Book（doji 条目）
    pdf_page: null
    print_page: null
definition_summary: >
  实体很小或没有实体的K线；多空均未控制该K线。原书：所有K线非趋势K线即 doji（二分频谱）。
  5分钟图上实体仅 1-2 个 tick 即看似无实体。
dependencies: [bar_anatomy]
mechanical_definition: >
  doji := body_ratio ≤ 0.25（参数 doji_body_ratio_max；含 range=0 的零波幅K线）。
  ⚠️ 近似声明：原书界限远比 0.25 紧（约 1-2 tick / range），0.25 是保守的宽近似，
  介于 0.25 与 trend_bar 下限之间的K线输出为 trend_bar（弱），与原书二分法一致但边界更宽松。
known_ambiguities: 阈值 0.25 为工程参数；tick 数判据待 instrument tick_size 精细化（MVP-C 前调整）。
event_at: bar 的 ts_close_utc
knowable_at: 同 event_at（bar_close）
knowable_precision: bar_close
result_type: boolean
positive_examples: 实体占比 0.1 的长影线K线 → doji=true。
negative_examples: body_ratio 0.6 的光头大阳线 → doji=false（同时 trend_bar=true）。
edge_cases: 零波幅K线（O=H=L=C）→ doji=true + range_zero 标记；body_ratio 恰等于 0.25 → 计入 doji（闭区间）。
learning_priority: very_early
automation_priority: very_early
automation_status: implemented
version: 0.1.0
```
