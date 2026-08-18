# Concept Spec · bar_anatomy（K线解剖事实）

```yaml
concept_id: bar_anatomy
english_term: bar anatomy / bull bar / bear bar
chinese_term: K线解剖 / 多头K线 / 空头K线
concept_provenance: Brooks Source        # 概念源自原书
implementation_provenance: Mechanical Approximation  # 实现为机械近似
source_confidence: B                     # 多处一致支持，需概括（前言 bar-by-bar 方法论 + 术语表 bull/bear bar 条目）
book_refs:
  - book: T
    section: List of Terms Used in This Book（bull bar / bear bar / trend bar 条目）
    pdf_page: null
    print_page: "xiii–xxvii（术语表整体范围）"
definition_summary: >
  每根K线的客观几何事实：实体大小（body）、上下影线（tail/shadow）、波幅（range）、
  方向（bull: close>open / bear: close<open）、收盘位置（close location）、
  相对近期均值的波幅位置（relative_range）。
dependencies: []                          # 无前置依赖（最底层事实）
mechanical_definition: >
  range = high - low（range=0 时比率类字段为 null，标记 range_zero）；
  body = |close - open|；body_ratio = body / range；
  upper_tail = high - max(open, close)；lower_tail = min(open, close) - low；
  tail_ratio 各为 / range；direction = close>open→bull，close<open→bear，相等→neutral；
  close_location = (close - low) / range；
  relative_range = range / mean(此前 20 根 RTH 5m 的 range，不含当前根；不足 20 根为 null，
  可用前一日 RTH 数据预热)。
known_ambiguities: relative_range 的窗口长度 20 为本项目参数（对应 20 EMA 语境），原书无明确数值。
event_at: bar 的 ts_close_utc（bar 收盘即事实完成）
knowable_at: 同 event_at（bar_close 精度；比率计算只用当前与此前数据，无前视）
knowable_precision: bar_close
result_type: evidence_set                 # 客观事实集合，不输出"好坏"判断
positive_examples: 常规K线均有完整事实输出；direction 与实体颜色一致。
negative_examples: 不判断"这是好的信号K线"（那是 signal_bar_evidence 的证据 + 人工判断）。
edge_cases: high==low==open==close（零波幅K线）→ 比率 null + range_zero=true；前 20 根无历史 → relative_range=null。
learning_priority: very_early
automation_priority: very_early           # 定义客观，MVP-B 首批实现
automation_status: implemented
version: 0.1.0
```

> 引用注：术语表原文见 `data/knowledge/01_核心术语表_Trading_Price_Action_Trends.md`。页码级引用待补（OQ-02）。
