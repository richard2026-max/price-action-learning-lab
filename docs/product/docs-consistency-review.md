# 文档一致性审查报告（docs-consistency-review）

> **版本**：0.3.0（Milestone 1 前最后一轮校正）
> **范围**：审查并修订 `PRD.md`、`brooks-system-design-implications.md`，参考最高优先级约束《项目开发具体要求》与《Milestone 1 前最后一轮文档校正 Prompt.md》。
> **本文档列出**：原文档冲突与修改、内容来源四层分类、开发优先级、Learning/Automation 区分、未决问题、以及跨文档一致性检查结果。

---

## 一、原文档存在的冲突与修改

| # | 原文档表述 | 冲突/问题 | 修订后 |
|---|---|---|---|
| 1 | 用单一 `Brooks Core` 标签同时表示来源/重要性/开发阶段 | 维度混淆 | 拆为两个维度：**Knowledge Provenance**（来源）× **Delivery Priority**（开发优先级），遵循 content-provenance-policy.md |
| 2 | "5m 主图 + 1h 背景同步"为第一阶段核心 | 违反忠实 Brooks（单一5m决策图） | 改为 **SPY 5m 单图**核心；1h 为 Research Extension |
| 3 | 加密/外汇/美股 + 三 provider 同时强调 | 第一阶段目标不是多市场架构 | 收敛为 **SPY**；provider abstraction 保留，不同时实现三 provider |
| 4 | H1/H2/L1/L2 归入"后期复杂 detector" | 与 Brooks 基础路线不符 | **归入 Level 3（基础）**，依赖 swing/leg/pullback |
| 5 | "detector 必须输出 0~1 score" | 概念混淆 | 支持多 result type（boolean/categorical/ordinal/continuous/count/evidence_set），不制造虚假 score |
| 6 | 防前视靠前端隐藏未来K线 | 前端隐藏不足 | **服务端权威 cursor**；集成测试证明；隐藏价格不模拟失忆 |
| 7 | "Level 5 复杂形态"标为 Research Extension | 错误归类 | **Level 5 = Brooks Source + Later**（wedge/climax/always-in 等是 Brooks 概念，非个人扩展） |
| 8 | "市场环境 detector 是软件第一阶段中枢" | 概念混淆 | 改为：**市场环境判断是 Brooks 学习的认知中枢**；其自动化 detector 属较晚 Mechanical Approximation |
| 9 | 要求 AI 必须给印刷页码 | 不同 PDF 未必有可靠印刷页码 | 改用**结构化引用**（pdf_page/print_page 可空），禁止编造页码 |

---

## 二、内容来源四层分类（Knowledge Provenance）

| 分类 | 含义 | 示例 |
|---|---|---|
| **Brooks Source** | Brooks 三本原书可查依据 | trend/range、bar-by-bar、20 EMA、signal bar、H1/H2、wedge、always-in、trader's equation |
| **Mechanical Approximation** | 程序化机械近似（≠ Brooks 完整主观判断） | trend score、swing 算法、H2 detector、pullback state machine |
| **Product / Engineering Design** | 为学习真实性/可复现性/安全/体验自行设计 | 服务端 cursor、sealed exam set、blind recheck、deterministic seed、PDF Figure extraction、Predict First |
| **Research Extension** | 超出 Brooks 学习核心的个人研究扩展 | 1h 多周期、crypto/外汇、volume 因子、AI 策略生成、非 Brooks 指标 |

**关键**：sealed exam set / blind recheck / MFE-MAE 属 Product 层，**不标 Brooks Source**。wedge/climax/always-in 是 Brooks Source，只是 Later。

---

## 三、开发优先级（Delivery Priority）与 Learning/Automation 区分

### 优先级：MVP / Early / Later / Research

### 产品递进（消除"一次性完成 Level 0-4"冲突）
- **MVP-A**：Replay Trainer（SPY 数据、1m→5m、RTH、20EMA、关键价位、服务端no-lookahead、Predict First、基础标注、保存/恢复）——**无复杂 detector 也可用**
- **MVP-B**：客观价格事实（bar anatomy、bull/bear、trend bar、doji、inside/outside、ii/iii/ioi、signal bar evidence）
- **MVP-C**：结构层（local extreme、swing、leg、pullback、trend line、channel line、bar counting）→ H1/H2、L1/L2、second entry
- **MVP-D**：Scanner（批量扫描、review、错题本、blind recheck）
- **Later**：always-in、wedge、spike and channel、climax、final flag、day type 复杂识别、完整交易管理、复杂成交模拟

### learning_priority vs automation_priority
- **核心原则：应该早学 ≠ 应该早自动化。**
- trend vs range、Always In、trader's equation：learning very_early，automation later（先靠人工标注）。
- inside bar：learning early，automation early（定义客观，易程序化）。
- H1/H2/L1/L2：learning early，automation middle（依赖结构层）。
- wedge/climax/always-in：Brooks Source，automation later。

---

## 四、当前剩余的未决问题

1. **Level 5 与 Level 3 的交集**（如 wedge pullback 与 pullback/bar counting）：实现到 Level 3 时把"是否进入 Level 5"作为待办决策点，不提前判定。
2. **H1/H2/L1/L2 精确实现边界**：依赖 swing/leg 结构层，需统一结构层建立后确定机械定义细节。
3. **封存考试集划分参数**：deterministic seed + stable hash + stratified split，具体参数待 Milestone 实现时定。
4. **知识库 Figure 提取**：依赖 PDF 图片层质量；OCR 作 fallback，具体策略待实际导入验证。
5. **SPY 5m 可迁移性**：Brooks 方法适用于 E-mini/期货，第一阶段按指令锁 SPY；未来扩展不改变 Brooks 学习内容。
6. **source confidence 精确标注**：单5m、SPY、day types、always-in 等关键判断的 book/chapter/page 依据，需在实现 detector 时逐条补充；当前资料不足的标 D/原书待核查。

---

## 五、跨文档一致性检查（十三项要求逐条核对）

| 要求 | 状态 |
|---|---|
| 产品目标：忠实 Brooks 学习，非量化盈利，非自动交易 | ✅ 三文档一致 |
| 图表：SPY + 5m + 20EMA + 单核心决策图 + 1h Research + 1m后台 | ✅ 一致 |
| 开发顺序：Replay Trainer 先于复杂 detector | ✅ 一致（MVP-A/B/C/D） |
| H1/H2：Brooks Source，learning early，依赖 swing/leg/pullback，非 Research | ✅ 一致 |
| wedge/climax/always-in：Brooks Source，automation Later，非 Research | ✅ 一致 |
| 防前视：server-authoritative cursor，API无未来，autoscale无未来，显示已知时间 | ✅ 一致 |
| AI：不先给答案，不做决策，不冒充 Brooks，原书不足标待核查 | ✅ 一致 |
| 来源分层：四层严格区分，不再用 Brooks Core 单一标签 | ✅ 一致（content-provenance-policy.md 为权威） |
| detector：多 result type + evidence + 版本 + knowable_at + Concept Spec 先行 | ✅ 一致 |
| trend/range：认知中枢，自动化为较晚 Mechanical Approximation | ✅ 一致 |
| 知识库引用：结构化引用，禁止编造页码 | ✅ 一致 |
| sealed exam set：Early，Product Design | ✅ 一致 |
| blind recheck：Later/Early-Later，数据模型预留 | ✅ 一致 |
| MFE/MAE：Product/Research Analytics，非 Brooks Source | ✅ 一致 |
| SPY 表述：项目选择，非"Brooks 只能用 SPY" | ✅ 一致 |

### 与《项目开发具体要求.md》的一致性
- 保留 provider abstraction、candidate detector、no-lookahead、版本化、可测试性。✅
- 第一阶段范围按本轮校正收窄为 SPY 5m 单图，是对《项目开发具体要求》"第一版不实盘/不自动交易"边界的进一步落实。✅
- 若《项目开发具体要求》与本轮校正 Prompt 冲突，**以本轮校正 Prompt 为最高优先级**（其为最终校正指令）。

---

## 六、结论

本轮校正完成，核心变更：
1. **来源与优先级拆为两维度**，废弃单一 `Brooks Core` 标签，新增 `docs/content-provenance-policy.md` 为权威策略。
2. **Level 5 修正归类**为 Brooks Source + Later。
3. **产品递进拆为 MVP-A/B/C/D**，第一件可用产品是 Replay Trainer。
4. **区分 learning_priority 与 automation_priority**。
5. **trend/range 为认知中枢**，自动化属较晚 Mechanical Approximation。
6. **知识库引用协议**改为结构化引用，禁止编造页码。
7. sealed exam set / blind recheck / MFE-MAE 归入 Product 层。
8. **SPY 表述更精确**（项目选择，非 Brooks 唯一）。
9. **source confidence A/B/D** 机制建立（C 已弃用，不作为原书证据等级，见 content-provenance-policy §三）。

**下一步**：等待用户审阅。确认后进入 Milestone 1。