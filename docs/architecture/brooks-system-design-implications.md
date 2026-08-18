# Brooks 价格行为体系 · 对系统设计的核心启示

> **版本**：0.3.0（Milestone 1 前最后一轮校正）
> 本文档是把"先搞懂 Al Brooks 体系"落到"怎么开发系统"的关键桥梁。
> 依据已精读的三本书核心内容（Front Matter 前言哲学 + 三册统一术语表 + 各书核心章节逻辑）提炼。
> **内容分层遵循 `docs/content-provenance-policy.md`**：四层来源（Brooks Source / Mechanical Approximation / Product·Engineering Design / Research Extension）× 开发优先级（MVP/Early/Later/Research）。

---

## 〇、内容分层（遵循 Content Provenance Policy）

每个设计条目都标注两个维度：**Provenance（来源）** 与 **Delivery Priority（开发优先级）**。

- **Brooks Source**：能从 Brooks 三本原书找到依据的概念/方法/术语。
- **Mechanical Approximation**：为程序化建立的机械近似（≠ Brooks 完整主观判断）。
- **Product / Engineering Design**：为学习真实性/可复现性/安全/体验自行设计的机制。
- **Research Extension**：超出当前 Brooks 学习核心的个人研究扩展。

优先级：`MVP` / `Early` / `Later` / `Research`。

**关键点**：一个概念可以同时是 `Brooks Source + Later`（如 wedge）。不能因后置开发就标为 Research Extension。

---

## 一、Brooks 体系的世界观（认知框架）

### 1. 市场处于"趋势 ↔ 交易区间"的连续谱
- **Provenance**: Brooks Source · **Priority**: very_early (learning), later (automation)
- Brooks 把行情归结为趋势（trend）与交易区间（trading range）两种基本状态，是同一连续谱两端，互相转换。
- ⚠️ **重要区分（修正）**：
  - **市场环境判断是 Brooks 学习的认知中枢**。
  - **但其自动化 detector 属于较晚的 Mechanical Approximation**。
  - Brooks 强调这个判断 ≠ 软件必须立即有一个正确的 trend/range 自动分类器。
  - 学习早期**由用户先判断市场环境**（`user_context_label`）；之后随人工数据积累再开发 `mechanical_context_candidate`，再比较 user judgment vs mechanical candidate vs later review。
- **Source Confidence**: B（多处一致，需概括）
- **book_refs**: Trends 术语表 trend / trading range 条目；Ranges 序言与术语表。

### 2. 一切从"逐根K线"读取（bar by bar）
- **Provenance**: Brooks Source · **Priority**: MVP
- 逐根K线阅读，从每根 bar 的开高低收、实体影线、与前几根关系提取信息。每根 bar 都有信息，不可忽略。
- **Source Confidence**: A（原书核心方法论）
- **book_refs**: Trends 前言/引言 bar-by-bar 逐根阅读；书前术语表 price action 条目。
- 对系统启示：回放器逐根播放、无未来数据、每根暂停判断——回放训练器是 MVP-A 核心。

### 3. 概率思维，"灰色地带"交易
- **Provenance**: Brooks Source
- 交易**结果**只是概率倾向；固定词汇（probably≥60%、unlikely≤40%）。
- ⚠️ 区分：**"交易结果有概率性" ≠ "所有市场事实都必须是概率分数"**。
- 客观价格事实（如"这根是 inside bar"）可以是 boolean/categorical。
- **Source Confidence**: A（术语表明确）
- **book_refs**: Trends 书前术语表 probability/probably/likely/unlikely 条目。

### 4. 唯一保留的指标：20 EMA
- **Provenance**: Brooks Source · **Priority**: MVP
- 作者唯一保留20 EMA，其余信息来自价格行为本身。**Source Confidence**: A。
- **book_refs**: Trends 书前术语表 EMA / moving average 条目；前言（20-bar EMA 为唯一保留指标）。
- 系统提供20 EMA叠加，不把指标当信号来源。

### 5. 逆势是亏损主因
- **Provenance**: Brooks Source
- countertrend 对多数人是亏损策略；fade 只在区间边界有效。**Source Confidence**: B。
- **book_refs**: Trends 书前术语表 countertrend / fade / countertrend scalp 条目。
- 系统标注"市场背景与信号方向一致性"，逆势标为高风险。

---

## 二、第一阶段核心交易图（修正多周期表述）

### Brooks Source：单一 5 分钟决策图（MVP）
- **SPY 5分钟图**作为唯一核心决策图。
- 默认图表信息：5分钟K线、20 EMA、当日开盘价、前一交易日 H/L/C、盘前 H/L、必要的跨日趋势线/通道线/水平关键价位、当前 session 时间及 bar index。
- **不要求用户同时观察1小时图**。

### 1小时、多周期 → Research Extension（后置）
- 保留在长期架构中，标记为 Research Extension。
- 移出第一阶段 Must / 成功标准 / 核心验收。
- **删除**"Brooks 标准方法要求 5m+1h 同步分析"表述——**原书没有此要求**。Brooks 核心方法论是单一5分钟图（作者明确主张只读一个图、不降1分钟图、不依赖多周期切换）。
- **Source Confidence**: B（单5m图为 Brooks Source）
- **book_refs**: Trends 前言与第10章（作者主张只读5分钟单图）；"1h 属后续研究"为 Product 设计推断。
- **design_rationale（针对"1h 属后续研究"）**: 第一阶段为贴近 Brooks 语境锁单5m图；1h 属 Research Extension。

### 1分钟数据 → 后台基础（Mechanical / 工程基础）
- 底层从早期支持1分钟：`1m raw bars → 聚合 5m`。
- 用于：数据质量、5m聚合、stop/target 先后顺序解析、MFE/MAE、intrabar 复盘。
- **默认学习界面不显示1分钟图**。

### SPY 表述精度（项目选择，非 Brooks 唯一）
- 区分：①Brooks 核心日内交易方法；②Brooks 对 SPY 的相关使用；③本项目为初学训练选 SPY。
- **不要写**"Brooks 体系只能用于 SPY"。
- **正确表达**：本项目第一阶段选择 SPY，是为最大程度保持与 Brooks 所述美股指数日内交易语境、RTH、开盘行为、gap、日类型训练的一致性。未来市场扩展不改变 Brooks 学习内容。

---

## 三、概念体系与两个优先级（Learning / Automation）

> **Level 0-6 同时承担"学习课程顺序"与"detector 开发顺序"是概念混淆，必须分开。**
> 每个概念用 `learning_priority`（何时学）与 `automation_priority`（何时自动识别）两个字段。

### Level 0 市场时间与基础上下文（Provenance 混合，需区分）
条目如下，provenance 不完全相同：
- **Brooks Source / Brooks-related concepts**（原书明确讨论的）：opening context、previous day levels、premarket、session behavior
- **Product / Market Data Infrastructure**（软件字段与日历规则）：calendar implementation、session_id、session bar index 的软件字段、tick_size metadata、exchange calendar rules

> 不因表格简洁而把整层全部标成 Brooks Source。其中 opening price 属于 Brooks 概念（Brooks Source）；session bar index / tick_size / trading calendar 的具体实现属于 Product / Market Data Infrastructure。
- learning: very_early · automation: early

### Level 1 单根K线与信号K线
OHLC/body/tails、bull/bear bar、trend bar、doji、reversal bar、signal bar、entry bar、inside bar、outside bar、ii/iii/ioi
- Provenance: Brooks Source · learning: early · automation: early（定义客观，易程序化）

### Level 2 几何与市场结构
local extreme、swing high/low、leg、trend line、trend channel line、channel、horizontal key level、gap、measured move、EMA gap bars
- Provenance: Brooks Source · learning: early · automation: early/middle

### Level 3 回调、bar counting 与突破（**核心回调与二次入场逻辑**）
pullback、H1/H2/H3/H4、L1/L2/L3/L4、second entry、breakout、breakout pullback、failed breakout、double top/bottom、micro double top/bottom
- Provenance: Brooks Source · learning: early · automation: middle（**依赖 swing/leg/pullback 结构层**，不能脱离独立实现）
- ⚠️ H1/H2/L1/L2 **不属于后期复杂 detector，也不属于 Research Extension**。

### Level 4 市场环境
trend↔trading range spectrum、tight trading range、barbwire、breakout mode、opening context、day type、spike、always-in candidate
- Provenance: Brooks Source · learning: very_early · automation: later（高度主观，先靠人工标注）

### Level 5 复杂 Brooks 结构（修正归类）
wedge、micro channel、spike and channel、climax、final flag、expanding triangle、pattern evolution、failed patterns
- **Provenance = Brooks Source**
- **Delivery Priority = Later**
- ⚠️ **不能因后置开发写成 Research Extension**。这些是 Brooks 原书概念（如 wedge、always-in、climax、final flag），只是开发优先级为 Later。

### Level 6 交易计划
trader's equation、two reasons、entry、protective stop、target、scalp vs swing、trade management、probability self-estimation、MFE/MAE、post-trade review
- Provenance: Brooks Source（trader's equation、two reasons、scalp/swing、stop/target 等）+ Product Analytics（MFE/MAE）
- learning: early · automation: later

---

## 四、候选识别器（detector）统一规范

### 概念澄清
- 不支持"所有 detector 必须输出 0~1 score"。
- 支持多 result type：boolean / categorical / ordinal / continuous / count / evidence_set。
- 每个 detector 必有：evidence、rule_source（来源分层）、rule_version、structure_version、input_data_version、input_slice_hash、event_at、knowable_at。

| 示例 detector | result type |
|---|---|
| inside bar / outside bar | boolean |
| H2 / L2 | categorical / event |
| overlap | continuous |
| breakout strength | evidence_set |
| trend/range context | continuous / ordinal |
| Signs of Strength | evidence count |

### Detector 进入 Scanner 前的强制流程（收紧）
任何 detector 正式进入 Scanner 前，必须依次经过：
1. Concept Spec → 2. 原书依据确认 → 3. Mechanical Definition → 4. 正例 → 5. 反例 → 6. 边界案例 → 7. knowable_at 定义 → 8. 单元测试 → 9. 人工图表验证 → 10. detector version freeze

建立统一 `docs/concepts/<concept>.md`（如 `docs/concepts/h2.md`），至少包含：
concept_id / english_term / chinese_term / **concept_provenance** / **implementation_provenance**（两者必须区分，见 content-provenance-policy §九与 concepts/README.md）/ book_refs / definition_summary / dependencies / mechanical_definition / known_ambiguities / event_at / knowable_at / result_type / positive_examples / negative_examples / edge_cases / learning_priority / automation_priority / automation_status / version

> **核心原则**：不允许 AI 直接从自然语言概念跳到 production detector。先写 Concept Spec，再写代码。

---

## 五、防前视（no-lookahead）设计

**最高等级工程约束。Provenance: Product / Engineering Design · Priority: MVP**

- **Replay cursor 由服务端权威管理**：后端 API 永远不向当前 session 返回 cursor 之后价格数据。
- **集成测试证明**：整个 replay 中所有行情响应均不存在 `timestamp > cursor` 的 bar。
- **autoscale 只用当前已可见数据**。
- **不靠前端隐藏未来K线**——后端是权威防前视层。
- **隐藏未来价格，不模拟失忆**：用户看到当前市场时间、当前第几根5分钟K线、当前 session、距离收盘多久。

**Provenance**: Product / Engineering Design（不用 source_confidence）
**design_rationale**: 由服务端权威管理 cursor，从构造上防止未来数据泄露。
**derived_from**: no-lookahead learning requirement

---

## 六、统一结构计算层（模块化，非黑箱）

- **Provenance**: Brooks Source + Mechanical Approximation
- 所有 detector 共享 swing/leg/pullback/EMA/session/trend line/channel/bar counting 基础状态。
- **不写成巨型 MarketStructureEngine 类**：shared structure primitives + versioned structure profile + thin candidate detectors。
- 目标：定义统一，实现模块化。

---

## 七、知识库（图文关联，按价值递进）

- **Provenance**: Product / Engineering Design + Brooks Source（书籍内容）
- **引用协议**：结构化引用（见 Content Provenance Policy 第五章），禁止编造印刷页码，pdf_page/print_page/chunk 可追溯。
- **Figure 功能优先级**：
  - Early：PDF 文本提取、glossary、chapter/section、基础引用
  - Later：Figure extraction、chunk↔figure 关联、图表显示原书 Figure、原书案例历史行情重建
- **不阻塞 Replay MVP**。

---

## 八、交易计划 / 模拟交易（交易管理）

- **Provenance**: Brooks Source（trader's equation、entry/stop/target、scalp vs swing）+ Product Analytics
- 记录方向/入场/止损/目标/风险/理由；成交引擎；MFE/MAE。
- ⚠️ **MFE/MAE 归入 Product / Research Analytics**，非 Brooks Source（无明确原书依据则不标）。
- 复杂成交模拟 = Later。

---

## 九、Brooks 体系对"系统边界"的印证

Brooks 强调：不自动交易、不依赖指标、不预测、关注单一图表、交易日内不看新闻、不要花太多时间在 Magnets/Measured Moves。
- 与需求文档"不实盘、不自动交易、不保存券商密钥、AI 不做最终决策、不泄露未来"完全吻合。

---

## 结论

Brooks 体系为 Price Action Learning Lab 提供**坚实理论骨架**，遵循 Content Provenance Policy 两维度分层：
1. **SPY 5m 单图**是第一阶段核心决策图（Brooks Source, MVP）。
2. **Level 0-6** 区分 learning_priority 与 automation_priority。
3. **detector 支持多 result type + evidence**，Concept Spec 先行，不强制 score。
4. **服务端权威 cursor + knowable_at** 保障 no-lookahead，不模拟失忆。
5. **trend/range 谱**是认知中枢，自动化属较晚 Mechanical Approximation。
6. **交易边界**印证不实盘/不自动交易/AI 不做决策。

所有理论判断尽量附 source confidence（**A/B/D**，C 已弃用，见 content-provenance-policy §三）。**原书未充分覆盖处标记 source_confidence=D / 原书待核查，不自行补全。**

*本文档遵循 `docs/content-provenance-policy.md`。*