# Concept Spec · double_top_bottom（双顶与双底）

```yaml
concept_id: double_top_bottom
english_term: double top / double bottom / micro double top-bottom
chinese_term: 双顶 / 双底 / 微型双顶双底
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: A
book_refs:
  - book: T
    section: "术语表 double bottom 条目"
    pdf_page: 13
    print_page: "xii区"
  - book: T
    section: "术语表 double top 条目"
    pdf_page: 14
    print_page: "xiii区"
definition_summary: >-
  double bottom：当前K线低点与先前某摆动低点大致相同（可相隔一根或20+根），
  不一定是日线最低，常见于多头旗形。double top 对称：当前高点与先前摆动高点大致相同。
dependencies:
  - swing
mechanical_definition: >-
  v0.1.0 基于已确认 Swing 序列的机械判定：
  tolerance = 近20根均幅的 25%（参数 double_top_bottom_tolerance_ratio）。
  double_bottom := 最近两个确认 swing_low 满足 |l2.price - l1.price| ≤ tolerance
                   且两低点间隔 ≥3 根K线。
  double_top   := 最近两个确认 swing_high 满足 |h2.price - h1.price| ≤ tolerance
                  且两高点间隔 ≥3 根。
known_ambiguities: >-
  "大致相同"量化为均幅的 25% 容差；间隔下限 3 根排除噪声；上限未设（原书允许 20+ 根）。
event_at: 第二个 swing 确认根的收盘
knowable_at: 同 event_at（bar_close，需第二个 swing 右侧确认后）
knowable_precision: bar_close
result_type: categorical   # double_bottom | double_top
positive_examples: >-
  swing_low1=100, swing_low2=100.5（tolerance=2.0），间隔5根 → double_bottom。
negative_examples: 两低点相差超过容差 → 不构成双底。
edge_cases: 双顶与双底可同时存在（宽幅区间）；微型双顶/双底（间隔≤5根）作为 evidence 子类型标注。
learning_priority: early
automation_priority: middle
automation_status: implemented
version: 0.1.0
```
