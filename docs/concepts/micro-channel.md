# Concept Spec · micro_channel（微型通道）

```yaml
concept_id: micro_channel
english_term: micro channel / tight channel
chinese_term: 微型通道 / 极窄通道
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: A
book_refs:
  - { book: T, section: "术语表 micro channel 条目", pdf_page: 20, print_page: "xviii区" }
  - { book: T, section: "Chapter 21: Micro Channels", pdf_page: 349, print_page: 317 }
definition_summary: >-
  极强趋势的表现形态：多头微型通道指连续多根K线（≥4 根）其低点不破前一根K线低点
  （无任何回调，甚至无单K线低点回调）；空头微型通道指连续高点不破前一根高点。
  微通道内顺势力量极强，首个逆势突破通常会失败演化为顺势买点。
dependencies: [bar_anatomy, pullback_leg]
mechanical_definition: >-
  v0.1.0 机械判定规则：
  1. 多头微型通道（Bull Micro Channel）：
     连续 ≥4 根 K 线满足 low[k] >= low[k-1]（无任何一根跌破前低），
     输出 bull_micro_channel，记录连续不破低根数（channel_length）；
  2. 空头微型通道（Bear Micro Channel）：
     连续 ≥4 根 K 线满足 high[k] <= high[k-1]（无任何一根升破前高），
     输出 bear_micro_channel，记录连续不破高根数。
known_ambiguities: 4 根阈值可由参数 micro_channel_min_bars 调整（默认 4）。
event_at: 满足长度时的每根 Bar 收盘
knowable_at: 同 event_at（bar_close，无前视）
knowable_precision: bar_close
result_type: categorical   # bull_micro_channel | bear_micro_channel
positive_examples: 连续 6 根阳线，每根低点均高于或等于前低 → bull_micro_channel (length=6)。
negative_examples: 第 3 根跌破前低 1 个 tick → 序列中断，不构成微通道。
edge_cases: 包含内包线（low[k] >= low[k-1]）依然满足不破低条件，属于合法微通道。
learning_priority: middle
automation_priority: later
automation_status: implemented
version: 0.1.0
```
