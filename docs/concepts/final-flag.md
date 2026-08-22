# Concept Spec · final_flag（终极旗形）

```yaml
concept_id: final_flag
english_term: final flag
chinese_term: 终极旗形
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: B        # Reversals 书中大量讨论（PDF p3 起），但无独立术语表条目
book_refs:
  - book: REV
    section: "Part I: Final Flag Reversal（全书核心主题）"
    pdf_page: 3
    print_page: null
definition_summary: >-
  终极旗形是趋势末端的旗形回调，通常出现在 climax（高潮）之后。
  市场先经历一段高潮式推进，随后进入一个看似正常的旗形回调（通常 3-10 根K线），
  但该旗形突破方向与原趋势相同却无法延续，最终反转为深度回调或反向趋势。
  本 detector 检测"climax 后 + 旗形结构"的组合。
dependencies:
  - climax
  - hl_counting
mechanical_definition: >-
  v0.1.0 两条件组合判定：
  1. 前置 climax：最近 10 根内出现过 climax 事件（复用 climax detector 输出）；
  2. 后续旗形：climax 后出现 3-8 根与 climax 方向相同的窄幅K线
     （body_ratio < 0.5 或 overlap > 60%），且价格未创显著新极值
     （距 climax 极值 < 0.5 × climax 位移）。
  当两条件同时满足时输出事件。
known_ambiguities: >-
  ①"窄幅"量化为 body_ratio < 0.5 是工程近似；②旗形突破失败（顺原方向）不构成 final flag；
  ③最终反转方向与幅度属 Level 6 交易决策，不在本 detector 范围。
event_at: 旗形最后一根K线收盘
knowable_at: 同 event_at（bar_close）
knowable_precision: bar_close
result_type: categorical   # bull_final_flag | bear_final_flag
positive_examples: >-
  连续大阳线 climax 后，3 根小K线在高位横盘（看似多头旗）→ bull_final_flag。
negative_examples: climax 后直接 V 反转（无旗形停顿）→ 不构成 final flag。
edge_cases: 旗形突破创新高 → final flag 失败（原趋势延续），输出 evidence 标注。
learning_priority: middle
automation_priority: later
automation_status: implemented
version: 0.1.0
```
