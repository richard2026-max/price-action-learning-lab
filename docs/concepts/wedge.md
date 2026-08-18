# Concept Spec · wedge（楔形与三推反转）

```yaml
concept_id: wedge
english_term: wedge / three pushes pattern
chinese_term: 楔形 / 三推形态
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: A
book_refs:
  - { book: T, section: "术语表 wedge / wedge flag / wedge reversal 条目", pdf_page: 25, print_page: "xxv区" }
  - { book: T, section: "Chapter 22: Wedges", pdf_page: 367, print_page: 335 }
definition_summary: >-
  传统上指三次推动、每次更远、趋势线与趋势通道线至少最小收敛、构成上升或下降
  楔形的形态。对交易者而言，任何三推形态都像楔形交易（three pushes）。
  楔形既可为反转形态（Wedge Reversal），也可为趋势中的回调（Wedge Flag / High 3 / Low 3）。
dependencies: [swing, hl_counting]
mechanical_definition: >-
  v0.1.0 基于确认 Swing 序列与 H/L 状态机组合检测：
  1. 上升楔形（Rising Wedge / 潜在顶部反转）：
     连续 3 个已确认的 swing_high 均创更高高点（HH1 < HH2 < HH3），
     且其间的两个 swing_low 也抬高（HL1 < HL2），且高点连线与低点连线呈现收敛
     （斜率 slope_high < slope_low，或高点推进距离缩窄：(HH3-HH2) < (HH2-HH1)）；
  2. 下降楔形（Falling Wedge / 潜在底部反转）：
     连续 3 个已确认的 swing_low 均创更低低点（LL1 > LL2 > LL3），
     且低点连线与高点连线收敛（低点推进距离缩窄：(LL2-LL3) < (LL1-LL2)）；
  3. 楔形旗（Wedge Flag）：多头回调中计出 H3（High 3）或空头回调中计出 L3（Low 3）。
known_ambiguities: 理想收敛与三推形态（three pushes）在程序化中收敛为三波极值推动与推进衰减。
event_at: 第三推极值K线确认时刻
knowable_at: 第三推 Swing 确认收盘时刻（严格无前视）
knowable_precision: bar_close
result_type: categorical   # rising_wedge | falling_wedge | wedge_flag_h3 | wedge_flag_l3
positive_examples: 连续三次向上冲顶，每次涨幅缩窄且 Swing 确认 → rising_wedge。
negative_examples: 只有两次推动（双顶）→ 判定为 double_top，非 wedge。
edge_cases: 第三推未能创新高（失败三推）→ 输出 failure_test 证据。
learning_priority: middle
automation_priority: later
automation_status: implemented
version: 0.1.0
```
