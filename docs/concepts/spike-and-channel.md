# Concept Spec · spike_and_channel（尖刺+通道）

```yaml
concept_id: spike_and_channel
english_term: spike and channel
chinese_term: 尖刺+通道
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: A
book_refs:
  - book: T
    section: "术语表 spike and channel 条目"
    pdf_page: 21
    print_page: "xx区"
  - book: T
    section: "Chapter 21: Spike and Channel Trend"
    pdf_page: 349
    print_page: 317
definition_summary: >-
  突破进入趋势、以通道形式跟随、动量较小且有双向交易的形态。
  第一段是急速的尖刺突破（spike），随后进入较缓的趋势通道（channel），
  通道阶段动量减弱但有双向交易。最终市场常在通道末端反转回尖刺起点附近。
dependencies:
  - bar_anatomy
  - trend_bar
mechanical_definition: >-
  v0.1.0 两阶段判定：
  Phase A（spike）：连续 ≥2 根同向 strong trend bar，总位移 ≥ 近20根均幅 × 2.0；
  Phase B（channel）：spike 后 ≥5 根 K 线，方向相同但 body_ratio 均值 < spike 阶段的
  60%（动量衰减），且价格保持在 spike 起始价与 spike 极值之间运行（通道约束）。
  当 Phase B 满足时输出事件。
known_ambiguities: >-
  ①"动量较小"量化为 body_ratio 均值衰减 60% 是工程近似；②通道末端的反转预测属 Level 6 交易决策，不在本 detector 输出范围。
event_at: channel 阶段最后一根K线收盘
knowable_at: 同 event_at（bar_close，需确认 spike 与 channel 两个阶段的全部数据）
knowable_precision: bar_close
result_type: categorical   # bull_spike_and_channel | bear_spike_and_channel
positive_examples: >-
  连续 3 根大阳线拉升 4 个点后，后续 8 根小阳/小阴K线在高位缓慢推进 → bull_spike_and_channel。
negative_examples: 全程匀速推进无动量差异 → 不构成 spike and channel。
edge_cases: spike 后立即 V 反转回起点 → 不构成 channel（通道约束失败）。
learning_priority: middle
automation_priority: later
automation_status: implemented
version: 0.1.0
```
