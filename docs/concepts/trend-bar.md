# Concept Spec · trend_bar（趋势K线）

```yaml
concept_id: trend_bar
english_term: trend bar
chinese_term: 趋势K线
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: B        # 术语表直接定义但界限宽（"有实体"）；强度分层为工程近似
book_refs:
  - book: T
    section: List of Terms Used in This Book（trend bar / breakout bar 条目）
    pdf_page: null
    print_page: null
definition_summary: >
  有实体（收盘高于或低于开盘）、指示至少小幅价格移动的K线，是判断动能的基础单位。
  原书为频谱二分：非 doji 即 trend bar。强趋势K线（big trend bar）是更强版本，
  常为突破K线。
dependencies: [bar_anatomy, doji]
mechanical_definition: >
  trend_bar := body_ratio > 0.25（非 doji），方向分 bull_trend_bar / bear_trend_bar
  （close vs open；相等记 neutral_trend 不可能出现——实体为 0 必为 doji）。
  strong := body_ratio ≥ 0.6 且 relative_range ≥ 1.2（双条件；近似"大趋势K线"，
  参数可调，输出于 evidence.strong）。
known_ambiguities: strong 双阈值 0.6/1.2 为工程参数；relative_range 不足 20 根历史时 strong 无法判定（仅输出 body 条件）。
event_at: bar 的 ts_close_utc
knowable_at: 同 event_at（bar_close）
knowable_precision: bar_close
result_type: categorical   # bull_trend_bar | bear_trend_bar | none（doji 或零波幅）
positive_examples: body_ratio 0.8、range 为均量 1.5 倍的阳线 → bull_trend_bar + strong=true。
negative_examples: 十字星 → none（由 doji detector 负责 true）。
edge_cases: body_ratio 恰在 (0.25, 0.6) → trend_bar=true 但 strong=false（"弱趋势K线"）。
learning_priority: very_early
automation_priority: very_early
automation_status: implemented
version: 0.1.0
```
