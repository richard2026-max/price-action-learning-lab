# Concept Spec · climax（高潮与通道线超冲反转）

```yaml
concept_id: climax
english_term: climax / trend channel line overshoot
chinese_term: 高潮 / 趋势通道线超冲反转
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: A
book_refs:
  - { book: T, section: "术语表 climax 条目", pdf_page: 14, print_page: "xii区" }
  - { book: T, section: "术语表 trend channel line overshoot 条目", pdf_page: 16, print_page: "xiv区" }
  - { book: T, section: "Chapter 15: Climaxes", pdf_page: 251, print_page: 219 }
definition_summary: >-
  走得过快过远后转向区间或反转的走势。多数高潮以趋势通道线超冲（overshoot）
  和反转结束；表现为连续多根大实体趋势棒或单根异动大K线远离 20EMA。
dependencies: [bar_anatomy, trend_bar, trend_lines]
mechanical_definition: >-
  v0.1.0 满足下列条件之一即判定为 climax 候选：
  1. 连续大趋势棒衰竭（Consecutive Trend Bars Climax）：
     连续 ≥3 根同向 strong trend_bar（收盘极值、相对均幅 ≥1.4），
     且价格远离 20 EMA（距离超过近 20 根平均 ATR 的 2.5 倍）；
  2. 极致大K线高潮（Single Exhaustion Bar）：
     单根 strong trend_bar 其实体和波幅超过近 20 根均值的 2.8 倍，伴随成交量激增；
  3. 通道线超冲（Channel Line Overshoot）：
     价格穿透趋势通道线并在当根或紧随下一根收出长影线反转棒。
known_ambiguities: 高潮常演化为交易区间（Trading Range）而非直接单边 V 反转，证据需提示 context。
event_at: 高潮K线收盘
knowable_at: 同 event_at（bar_close）
knowable_precision: bar_close
result_type: categorical   # buy_climax | sell_climax
positive_examples: 连续 4 根大阳线加速冲高、远离均线 3 倍 ATR → buy_climax。
negative_examples: 紧贴均线的缓慢小阳线推进 → 属通道或微通道，非 climax。
edge_cases: 开盘首根大K线 → 需结合前日收盘与跳空综合判断。
learning_priority: middle
automation_priority: later
automation_status: implemented
version: 0.1.0
```
