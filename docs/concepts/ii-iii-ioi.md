# Concept Spec · bar_pattern（ii / iii / ioi 序列模式）

```yaml
concept_id: bar_pattern
english_term: "ii (inside-inside) / iii (inside-inside-inside) / ioi (inside-outside-inside)"
chinese_term: 双重内包 / 三重内包 / 内包-外包-内包
concept_provenance: Brooks Source
implementation_provenance: Mechanical Approximation
source_confidence: A        # 术语表三者均有直接定义
book_refs:
  - book: T
    section: List of Terms Used in This Book（ii / iii / ioi 条目）
    pdf_page: null
    print_page: null
definition_summary: >
  ii：连续两根内包线（第二根包在第一根内），腿末端是突破模式，可成旗或反转形态；
  次可靠版本是"仅实体 ii"（忽略影线）。iii：连续三根内包线，比 ii 稍可靠。
  ioi：三根连续K线中第二根为外包线、第三根为内包线，常是突破模式。
dependencies: [inside_bar, outside_bar]
mechanical_definition: >
  在 bar i 收盘时判定（含等于语义与依赖 detector 一致）：
  ii    := inside(i) 且 inside(i-1)
  iii   := ii 且 inside(i-2)（iii 出现时同时报告 ii——iii 是 ii 的延伸，两者都为真）
  ioi   := inside(i) 且 outside(i-1) 且 inside(i-2)
  身体版（body-only）变体后置研究（参数 bodies_only=false 默认关闭）。
known_ambiguities: 原书"次可靠的仅实体 ii"提示影线版/实体版可靠性不同——v1 只做影线版。
event_at: 模式最后一根 bar 的 ts_close_utc
knowable_at: 同 event_at（bar_close；序列判定需要最后一根收盘）
knowable_precision: bar_close
result_type: categorical   # ii | iii | ioi（同一 bar 可同时触发 ii 与 iii，evidence 注明）
positive_examples: H/L 逐根收缩三连 → 第 3 根报 ii（第 3 根若也内包则 iii）。
negative_examples: 第 2 根突破第 1 根高点 → 序列中断，无事件。
edge_cases: 等幅（inclusive）序列同样计入；与前日最后一根的衔接判定在回放中只用当日 RTH 序列（跨日序列不判定，声明为已知边界）。
learning_priority: early
automation_priority: early
automation_status: implemented
version: 0.1.0
```
