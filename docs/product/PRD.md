# PRD · 产品需求文档
### Price Action Learning Lab — 价格行为学习与训练平台

> **版本**：0.3.0（Milestone 1 前最后一轮校正）
> **最高原则**：忠实学习和复刻 Al Brooks 本人的价格行为交易方法。不是量化盈利系统，不是自动交易机器人。
> **内容分层遵循 `docs/content-provenance-policy.md`**。

---

## 〇、内容来源与开发优先级（两维度分层）

本文档所有功能/设计用两个独立维度标记（遵循 Content Provenance Policy）：

**A. Provenance（内容来源）**
- `Brooks Source`：Brooks 三本原书可查依据。
- `Mechanical Approximation`：为程序化建立的机械近似（≠ Brooks 完整主观判断）。
- `Product / Engineering Design`：为学习真实性/可复现性/安全/体验自行设计的机制。
- `Research Extension`：超出 Brooks 学习核心的个人研究扩展。

**B. Delivery Priority（开发优先级）**
- `MVP` / `Early` / `Later` / `Research`

> **一个概念可同时是** `Brooks Source + Later`（如 wedge）。不能因后置开发就归为 Research Extension。

---

## 一、产品背景与定位

### 1.1 用户画像
- 半职业交易员，正在系统学习 Al Brooks 价格行为学，初学阶段。
- 具备较扎实 Python 编程能力。
- **第一阶段聚焦 SPY 日内交易语境**；外汇、加密货币后置。
- 单用户，本地运行。

### 1.2 核心痛点
1. 价格行为概念高度依赖上下文。
2. 事后分析带后见之明，无法训练逐根判断。
3. 概念庞杂难成体系。
4. 缺个人案例库。
5. 难发现认知盲点。

### 1.3 产品定位
**核心原则：系统帮助用户建立认知，而不是取代用户思考。系统输出永远是"候选"。**

服务三个过程：**学习** / **训练**（逐根回放判断）/ **研究**（扫描候选人工复核）。

---

## 二、第一阶段核心（Brooks Source, MVP）

### 2.1 核心决策图：SPY 5 分钟单图
- **唯一核心决策图**：SPY 5分钟图。
- 默认图表信息：5分钟K线、20 EMA、当日开盘价、前一交易日 H/L/C、盘前 H/L、跨日趋势线/通道线/水平关键价位、当前 session 时间及 bar index。
- **不要求用户同时观察1小时图**。

### 2.2 核心训练模式：Predict First, Reveal Later（Product Design, MVP）
在**触发时刻**，系统**先要求用户回答**：
1. 当前市场更接近 trend 还是 trading range？
2. 若是趋势，方向是什么？
3. 当前处于什么结构？
4. 是否存在 pullback？
5. 当前 bar counting 是什么？
6. 是否考虑交易？
7. 若交易，方向是什么？
8. 至少写出两个理由。
9. 入场、止损、目标在哪里？
10. 自己估计成功概率是多少？

**提交后锁定答案。** 之后才能查看 system candidate / 原书定义 / 后续行情 / 复盘。
> **不要让 AI 先告诉用户答案。**

**"关键位置 / 触发时刻"的定义（防 sampling bias）**

> ⚠️ 当 MVP-A 尚无可靠 detector 时，**不得根据当日后续行情、最终结果或未来 detector output 来决定"何时是关键时刻"**（否则产生严重 hindsight / sampling bias）。

**MVP-A 阶段**，默认允许以下**无未来偏差**的触发方式：
- 用户主动点击"做一次判断"；
- 每根 bar 都可回答；
- 固定每 N 根 bar 提示一次；
- 根据当前已可见信息设置的预先规则触发。

**Detector 已上线后**，可以生成 `candidate-sampled training session`（根据 candidate detector 挑选训练案例），但**必须明确标记**：
```yaml
sampling_mode: candidate_based
sampling_bias: true
detector_id:
detector_version:
```
不能与随机盲测成绩混在一起。

### 2.3 市场环境判断：认知中枢，非软件中枢
- **市场环境判断是 Brooks 学习的认知中枢**；其自动化 detector 属较晚的 Mechanical Approximation。
- 学习早期**由用户先判断市场环境**（`user_context_label`）。
- 随人工数据积累再开发 `mechanical_context_candidate`，再比较 user judgment vs mechanical candidate vs later review。
- **不要把 trend/range 自动识别过早做成系统"中枢真相"。**

### 2.4 第一阶段产品闭环
```
SPY历史数据 → 1m底层 → 聚合5m → Brooks 5m单图 → 20EMA+关键价位
→ 服务端严格无未来回放 → 用户逐根判断 → 用户先提交判断
→ 再揭晓 candidate detector / 原书解释 → 标注与复盘
→ swing/leg/pullback → H1/H2/L1/L2 → 候选扫描 → 人工确认 → 错题本 → blind recheck
```

---

## 三、产品递进（MVP-A/B/C/D → Later）

> **消除"第一阶段一次性完成 Level 0-4 全部 detector"的冲突。拆成产品递进，保证第一件可用产品是 Replay Trainer。**

### MVP-A：先把训练器做出来
必须完成（Brooks Source + Product Design）：
- SPY 数据
- 1m raw data
- 1m → 5m 聚合
- 交易日历 / RTH
- 20 EMA
- opening price
- previous day H/L/C
- premarket H/L
- 服务端 no-lookahead replay
- Predict First, Reveal Later
- 基础标注
- 保存 / 恢复

> **这一阶段完全可以没有复杂 detector。目标：用户能真正进行 Brooks 风格 bar-by-bar 历史训练。**

### MVP-B：客观价格事实
加入（Brooks Source, mechanical，低歧义、易验证）：
- bar anatomy、bull/bear bar、trend bar、doji、inside/outside、ii/iii/ioi、基础 signal bar evidence

### MVP-C：结构层
加入：
- local extreme、swing、leg、pullback、trend line、channel line、bar counting 基础结构
- 然后实现：H1/H2、L1/L2、second entry

> **目标：系统第一次能辅助用户学习 Brooks 最核心的回调与二次入场逻辑。**

### MVP-D：Scanner
- 批量扫描、candidate review（confirmed/rejected/uncertain）、错题本、blind recheck
> **只有 detector 已可人工验证后，才增加。**

### Later
- always-in、wedge、spike and channel、climax、final flag、day type 复杂机械识别、完整交易管理、复杂成交模拟

---

## 四、学习内容顺序 vs 软件开发顺序（区分两维度）

**Level 0-6 不代表开发顺序。** 用两个字段：

- `learning_priority`：用户何时应学到（very_early/early/middle/later）
- `automation_priority`：程序何时自动识别（very_early/early/middle/later）

> **核心原则：应该早学，不等于应该早自动化。**

| 概念 | Provenance | learning | automation |
|---|---|---|---|
| trend vs trading range | Brooks Source | very_early | later（先靠人工标注） |
| Always In | Brooks Source | very_early | later |
| trader's equation | Brooks Source | very_early | later |
| inside bar | Brooks Source | early | early（定义客观，易程序化） |
| H1/H2/L1/L2 | Brooks Source | early | middle（依赖 swing/leg/pullback） |
| wedge / climax / always-in | Brooks Source | middle | later（非 Research Extension） |

### Level 分级（学习顺序；Provenance 见各条）
- **Level 0 市场时间与基础上下文**（**Provenance 混合，需区分**）：
  - **Brooks Source / Brooks-related concepts**（原书讨论的）：opening context、previous day levels、premarket、session behavior、opening price
  - **Product / Market Data Infrastructure**（软件字段与日历规则）：calendar implementation、session_id、session bar index 软件字段、tick_size metadata、exchange calendar rules
- **Level 1 单根K线与信号K线**：OHLC/body/tails、bull/bear bar、trend bar、doji、reversal bar、signal bar、entry bar、inside/outside、ii/iii/ioi
- **Level 2 几何与市场结构**：local extreme、swing high/low、leg、trend line、channel line、channel、horizontal key level、gap、measured move、EMA gap bars
- **Level 3 回调、bar counting 与突破**：pullback、H1/H2/H3/H4、L1/L2/L3/L4、second entry、breakout、breakout pullback、failed breakout、double top/bottom、micro double top/bottom
- **Level 4 市场环境**：trend↔range spectrum、tight trading range、barbwire、breakout mode、opening context、day type、spike、always-in candidate
- **Level 5 复杂 Brooks 结构**：wedge、micro channel、spike and channel、climax、final flag、expanding triangle、pattern evolution、failed patterns
  - **Provenance = Brooks Source · Delivery Priority = Later**（非 Research Extension）
- **Level 6 交易计划**：trader's equation、two reasons、entry、protective stop、target、scalp vs swing、trade management、probability self-estimation、MFE/MAE、post-trade review

---

## 五、候选识别器（detector）规范

### 概念澄清
- 不支持"所有 detector 必须输出 0~1 score"。
- 支持 result type：boolean / categorical / ordinal / continuous / count / evidence_set。
- 每个 detector 必有：evidence、rule_source、rule_version、structure_version、input_data_version、input_slice_hash、event_at、knowable_at。

| 示例 detector | result type |
|---|---|
| inside/outside bar | boolean |
| H2 / L2 | categorical / event |
| overlap | continuous |
| breakout strength | evidence_set |
| trend/range context | continuous / ordinal |
| Signs of Strength | evidence count |

### Detector 进入 Scanner 前强制流程
1. Concept Spec → 2. 原书依据确认 → 3. Mechanical Definition → 4. 正例 → 5. 反例 → 6. 边界案例 → 7. knowable_at → 8. 单元测试 → 9. 人工图表验证 → 10. detector version freeze

建立 `docs/concepts/<concept>.md`（如 `h2.md`）。**先写 Concept Spec，再写代码。**

---

## 六、防前视（no-lookahead）设计

**最高等级工程约束（Product Design, MVP）。**
- **Replay cursor 由服务端权威管理**：后端 API 永远不返回 cursor 之后数据。
- **集成测试证明**：replay 中所有行情响应无 `timestamp > cursor` 的 bar。
- **autoscale 只用当前已可见数据**。
- **不靠前端隐藏未来K线**——后端是权威防前视层。
- **隐藏未来价格，不模拟失忆**：用户看到当前市场时间、第几根5分钟K线、当前 session、距收盘多久。

---

## 七、重要设计（按优先级）

### 1. 1分钟数据：后台基础（Mechanical, MVP）
- `1m raw bars → 聚合 5m`。用于数据质量/聚合/stop-target顺序/MFE-MAE/intrabar复盘。
- **默认学习界面不显示1分钟图。**

### 2. Instrument metadata（Product, MVP）
instrument_id、symbol、provider、tick_size、price_precision、tick_value、contract_multiplier、quote_currency、calendar_id、session_definition、quote_side、feed_consolidated。
以 "one tick" 为依据的 detector 必须依赖此元数据。

### 3. 封存考试集 sealed exam set（Product Design, **Early**）
- 数据被浏览即污染，**应尽早建立保护机制**。
- deterministic seed + stable hash + stratified split，多年份保留封存样本。
- 普通浏览/Scanner/搜索不可访问；服务端强制保护；解封记录。

### 4. 统一结构计算层（模块化，非黑箱）
- shared structure primitives + versioned structure profile + thin candidate detectors。
- 不写巨型 MarketStructureEngine 类。

### 5. 知识库（图文关联，按价值递进，不阻塞 Replay MVP）
- **Early**：PDF 文本提取、glossary、chapter/section、基础引用
- **Later**：Figure extraction、chunk↔figure 关联、图表显示原书 Figure、原书案例历史行情重建
- 引用协议：结构化引用（见 Content Provenance Policy 第五章），禁止编造印刷页码。

### 6. blind recheck（Product / Learning Design, Later/Early-Later）
- 数据模型早期预留：original_annotation、recheck_annotation、annotation_version、hidden_previous_answer。
- 30/60/90 日复习调度后置。

### 7. 形态演化
- 标注模型加入：supersedes、evolved_into、invalidated_at、outcome。

### 8. MFE / MAE（Product / Research Analytics, Later）
- 用于复盘，**非 Brooks Source**（无明确原书依据则不标）。

---

## 八、暂时不要实现 / 降低优先级（Research Extension 或 Later）

- 1小时同步图（Research）
- BTC/crypto 正式训练（Research）
- 外汇正式训练（Research）
- 三个 provider 同时实现（Research）
- 完整撮合引擎（Later）
- 复杂1分钟动画（Research）
- 自动交易、券商连接（绝不）
- forward stats、收益优化（Research）
- AI 自动生成策略（Research）
- wedge / always-in 等复杂 detector（Later, Brooks Source）
- 自动识别并重放书中 Figure 历史行情（Later）
- 云部署、Redis/Kafka/Celery、多用户（绝不）

---

## 九、非功能性需求

- 可复现性：同数据版本+detector版本+参数+随机种子+软件版本 ⇒ 相同结果。
- 可解释性：每个候选可展开查看依据，不强制神秘分数。
- 可测试性：核心领域逻辑不依赖 FastAPI 路由或 React UI。
- 可扩展性：保留 provider abstraction / 结构层接口。
- 性能：普通PC上，单日5m近即时加载、逐根播放流畅、扫描用 Polars/DuckDB 批量计算。
- 本地优先：AI 关闭时核心功能正常。
- 边界：不实盘、不自动交易、不保存券商密钥；数据 API 密钥与交易 API 密钥分离。

---

## 十、验收标准（Milestone 0）
- 本 PRD 与 brooks-system-design-implications.md、docs-consistency-review.md、content-provenance-policy.md 四方一致。
- 跨文档一致性：第一正式品种 SPY、核心周期5m、1h非核心、1m后台、H1/H2为基础路线、不实盘、不自动交易、AI不做决策、服务端no-lookahead、来源四层分层。
- 用户审阅确认后，进入 Milestone 1。

---

*本文档依据《项目背景、个人情况与核心诉求.md》《项目开发具体要求.md》《用于修订 PRD 与 Brooks 系统设计文档的提示词v1.md》《Milestone 1 前最后一轮文档校正 Prompt.md》编写。遵循 Content Provenance Policy。*