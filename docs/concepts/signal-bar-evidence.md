# Concept Spec · signal_bar_evidence（信号K线证据集）

```yaml
concept_id: signal_bar_evidence
english_term: signal bar (evidence set)
chinese_term: 信号K线（证据集）
concept_provenance: Brooks Source        # 概念（signal bar 的角色）源自原书
implementation_provenance: Product / Engineering Design + Mechanical Approximation
  # "输出客观特征供人工判断好坏"这一产品机制是本项目设计，非原书内容
source_confidence: B                     # signal bar 条目为关系定义；"何为好信号"散见各章需概括
book_refs:
  - book: T
    section: List of Terms Used in This Book（signal bar / entry bar / reversal bar 条目）
    pdf_page: null
    print_page: null
definition_summary: >
  原书定义：signal bar 是入场单成交那根K线（entry bar）之前的一根K线，是形态的最后一根。
  注意这是**关系定义**——任何K线都可能成为信号K线，"好坏"依赖上下文（趋势方向、位置、
  相对前根行为）。因此本 detector 不判定"这是好的信号K线"，只输出供人工判断的客观特征证据。
dependencies: [bar_anatomy, inside_bar, outside_bar]
mechanical_definition: >
  每根 bar 收盘时输出证据集合：
  direction（bull/bear/neutral）、body_ratio、upper_tail_ratio、lower_tail_ratio、
  close_location（收盘在全程范围的位置 0~1）、dominant_tail（upper/lower/none）、
  relative_range、is_inside、is_outside。
  不输出 boolean/categorical 结论——evidence_set 类型。
known_ambiguities: >
  原书评估信号K线质量还依赖：与前几根的重叠、趋势方向一致性、是否二次入场位置、
  微通道强度等上下文——这些属于 Level 2+ 结构层，v1 不纳入。
event_at: bar 的 ts_close_utc
knowable_at: 同 event_at（bar_close）
knowable_precision: bar_close
result_type: evidence_set
positive_examples: 收盘位置 >0.8、下影长于上影的阳线 → 证据提示"多头接受价位的迹象"（供人工解读）。
negative_examples: 本 detector 永不输出"这是好的买点信号"（那需要 Level 2+ 上下文 + 人工确认）。
edge_cases: 零波幅K线 → 比率类证据为 null；首根K线 → is_inside/is_outside 为 null。
learning_priority: early
automation_priority: early
automation_status: implemented
version: 0.1.0
```
