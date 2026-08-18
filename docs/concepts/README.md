# 概念规格索引 · Concept Specs

> 本目录（`docs/concepts/`）是**每个要进入 Scanner 的 detector 都必须先有 Concept Spec（概念规格）**的唯一登记处。
> 规范依据：`docs/content-provenance-policy.md` 第九节（概念卡片模板）与 PRD 第五章、brooks-system-design-implications 第四章的 detector 强制流程。

---

## 一、为什么必须先写 Concept Spec

**不允许 AI 直接从自然语言概念跳到 production detector。**

任何 detector 在正式进入 Scanner 之前，必须依次经过下列 10 步强制流程：

1. **Concept Spec** → 2. 原书依据确认 → 3. Mechanical Definition → 4. 正例 → 5. 反例 → 6. 边界案例 → 7. knowable_at 定义 → 8. 单元测试 → 9. 人工图表验证 → 10. detector version freeze

---

## 二、Concept Specs 索引表 (Level 1-5 已登记 14 项)

| concept_id | english_term | concept_provenance | automation_priority | automation_status | 规格文件 |
|---|---|---|---|---|---|
| bar_anatomy | bar anatomy / bull-bear bar | Brooks Source | very_early | implemented (v0.1.0) | `bar-anatomy.md` |
| doji | doji | Brooks Source | very_early | implemented (v0.1.0) | `doji.md` |
| trend_bar | trend bar | Brooks Source | very_early | implemented (v0.1.0) | `trend-bar.md` |
| inside_bar | inside bar | Brooks Source | very_early | implemented (v0.1.0) | `inside-bar.md` |
| outside_bar | outside bar | Brooks Source | very_early | implemented (v0.1.0) | `outside-bar.md` |
| bar_pattern | ii / iii / ioi | Brooks Source | early | implemented (v0.1.0) | `ii-iii-ioi.md` |
| signal_bar_evidence | signal bar (evidence set) | Brooks Source + Product Design | early | implemented (v0.1.0) | `signal-bar-evidence.md` |
| swing | swing high / swing low | Brooks Source | early | implemented (v0.1.0) | `swing.md` |
| pullback_leg | pullback / leg | Brooks Source | early | implemented (v0.1.0) | `pullback-leg.md` |
| hl_counting | High 1-4 / Low 1-4 | Brooks Source | middle | implemented (v0.1.0) | `hl-counting.md` |
| trend_lines | trend line / channel line | Brooks Source | middle | implemented (v0.1.0) | `trend-lines.md` |
| wedge | wedge / 3 pushes | Brooks Source | later | implemented (v0.1.0) | `wedge.md` |
| climax | climax / exhaustion | Brooks Source | later | implemented (v0.1.0) | `climax.md` |
| micro_channel | micro channel / tight channel | Brooks Source | later | implemented (v0.1.0) | `micro-channel.md` |

---

*本文件是 `docs/concepts/` 目录的入口与强制流程说明。所有 detector 进入 Scanner 前必须先满足本节要求。*
