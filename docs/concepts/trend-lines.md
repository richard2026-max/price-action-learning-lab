# Concept Spec · trend_lines（趋势线与趋势通道线）

```yaml
concept_id: trend_lines
english_term: trend line / trend channel line
chinese_term: 趋势线 / 趋势通道线
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: A
book_refs:
  - { book: T, section: "术语表 trend line 条目", pdf_page: 16, print_page: "xiv区" }
  - { book: T, section: "术语表 trend channel line 条目", pdf_page: 16, print_page: "xiv区" }
  - { book: T, section: "Chapter 10: Trend Lines and Trend Channel Lines", pdf_page: 191, print_page: 159 }
definition_summary: >-
  趋势线（trend line）：朝趋势方向画的线。多头中向上斜、连摆动低点（支撑）；
  空头中向下斜、连摆动高点（阻力）。
  趋势通道线（trend channel line）：画在K线另一侧（多头高点之上、空头低点之下），
  常用于识别高潮、超冲（overshoot）与欠冲（undershoot）。
dependencies: [swing]
mechanical_definition: >-
  v0.1.0 机械规则（基于已确认 swing 序列，严格无前视）：
  1. 收集当前会话内**已确认**的 swing_low 序列（多头趋势线）与 swing_high 序列（空头趋势线）；
  2. 多头趋势线（bull trend line）：最近两个确认的 swing_low（要求后一个更高，HL），
     两点连线确定斜率与截距，并向右延伸至当前 cursor。
     如果当前 bar 的低点跌破该延伸线超过容差（tolerance），则标记为 trend_line_breakout；
  3. 空头趋势线（bear trend line）：最近两个确认的 swing_high（要求后一个更低，LH），
     两点连线向右延伸；当前 bar 高点升破线即报 trend_line_breakout；
  4. 趋势通道线（trend channel line）：过趋势线期间的最高/最低 swing 点作趋势线的平行线。
  输出 candidate 记录斜率、截距、当前K线与线的位置距离、是否发生触碰/突破。
known_ambiguities: 多点拟合与主观选点在程序化中收敛为"最近两点有效 swing 连线"。
event_at: bar 收盘
knowable_at: 同 event_at（连线所依赖的 swing 均已在此前被确认，延伸计算无前视）
knowable_precision: bar_close
result_type: evidence_set
positive_examples: 两个抬高的 swing_low 连线上行，当前K线回踩线附近反弹。
negative_examples: 两个低点未抬高（非上升序列）→ 不构造多头趋势线。
edge_cases: 确认 swing 少于 2 个 → 无有效趋势线；两点横向距离过短（<3根）→ 过滤。
learning_priority: early
automation_priority: middle
automation_status: implemented
version: 0.1.0
```
