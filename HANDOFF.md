# HANDOFF · 项目交接快照（2026-08-16 晚）

> 迁移后新会话必读。详细文档入口：仓库根 `README.md` → `docs/README.md`（文档地图）→ `docs/review-state.md`（Batch 0-14 全程日志）。设计权威 = 四份 canonical（`docs/product/PRD.md`、`docs/content-provenance-policy.md`、`docs/architecture/brooks-system-design-implications.md`、`docs/product/docs-consistency-review.md`）。

## 1. 项目一句话

Price Action Learning Lab：本地单用户 Al Brooks 价格行为学习平台（SPY 5m 单图，不实盘不自动交易）。核心闭环：真实数据 → 服务端权威 no-lookahead 回放 → Predict First 判断锁定 → detector 候选揭晓 → 标注复盘。路线 MVP-A/B/C/D → Later。

## 2. 启动与验证

```powershell
# 仓库根目录（Windows）
.\start-backend.cmd        # 后端+UI http://127.0.0.1:8000（单进程模式，伺服 apps/web/dist）
.\start-frontend.cmd       # 仅前端开发时用（5173 热更新）
# 测试：cd apps/api && .venv/Scripts/python -m pytest tests/   （当前 92 通过）
# 构建前端：cd apps/web && npm run build（改前端后必须 build，否则 8000 看不到更新）
```

## 3. 迁移必须手动携带（全部被 .gitignore 排除，不是 git 仓库也没有远程）

| 路径 | 内容 |
|---|---|
| `.env` | **HFDL API key**（用户私有，hfd_669e…，勿泄露） |
| `apps/api/.venv/` | Python 虚拟环境（或迁移后重建：`pip install -e ".[dev]"`） |
| `data/app.sqlite` | 回放会话/判断/标注 |
| `data/market/` | 已入库行情 Parquet+manifests |
| `data/imports/hfdl_SPY_clean.parquet` | HFDL 全量缓存（49.6MB，2026-08-15 版） |
| `data/knowledge/` | Brooks 原书笔记+全文提取（版权敏感，永不入库/上传） |
| 仓库外的 `AlBrooks书/`（4 本 PDF）与 `开发思路/`（冻结档案） | 也需拷贝 |

## 4. 当前进度（截至本快照）

| 里程碑 | 状态 |
|---|---|
| 文档体系（Batch 0-8 审计） | ✅ 四 canonical + 全仓一致，无 blocker |
| Phase 0 骨架 / MVP-A 回放训练器 | ✅ 前后端完成；**真实数据已入库**（HFDL 2019-2021 共 757 交易日） |
| MVP-B 客观K线事实 | ✅ 7 detector（anatomy/doji/trend_bar/inside/outside/ii-iii-ioi/signal_bar_evidence），判断提交后解锁 |
| MVP-C 结构层 | ✅ 第一批：swing（右侧N=3确认）/pullback_leg（净漂移上下文）/hl_counting（H1-H4·L1-L4 状态机，second_entry 标注）；profile=mvp-c-0.1.0；前端已构建；**92 测试全绿** |
| OQ-01/OQ-02 | OQ-01 已验证（成交量±1% 吻合）；OQ-02 已补 H1/H2 等页码级引用（见 open-questions.md） |

## 5. 下一批工作（按序）

1. MVP-C 收尾：trend line / channel line detector；leg 划分 v0.2（待 swing 修订链）；净漂移上下文升级为 swing 序列上下文；浏览器实测截图登记。
2. MVP-D Scanner（批量扫描/candidate review/错题本/blind recheck——数据模型已在 ORM 预留 supersedes/evolved_into 字段未建表）。
3. 后置：知识库（PDF 提取已有素材 data/knowledge/extracted/*.txt 带 PDFPAGE 标记）、AI provider 抽象（默认禁用）、sealed exam set（数据一入库就该建，**尽快补**——浏览即污染）。

## 6. 关键工程约束（不可违背）

- no-lookahead：服务端权威 cursor，API 永不返回 cursor 后数据；detector 只读 ctx[0..i]；swing 需右侧确认（knowable_at>event_at）。
- detector 流程：**先 Concept Spec（docs/concepts/）再代码**，十步准入；来源四层（Brooks Source/Mechanical/Product/Research）×优先级（MVP/Early/Later/Research）双维标注；概率档位 good/okay/bad，禁 0-100 分。
- 数据语义：HFDL=复权·仅RTH·无盘前（premarket 价位自动降级 None）；2022-03 前合并磁带（佳）/之后 IEX（谨慎）；manifest 记录一切。
- 嵌入式浏览器自动化点击偶发失效（用 dom_cua node_id / 键盘绕过），真实用户无此问题。

## 7. 常用命令速查

```powershell
cd apps/api
.venv\Scripts\python -m app.cli data seed --start 2024-01-02 --end 2024-03-28   # 合成数据
.venv\Scripts\python -m app.cli data ingest-hfdl --start 2005-01-03 --end 2018-12-31  # 真实数据（缓存秒级）
.venv\Scripts\python -m app.cli api            # 裸启动后端
# API：/api/v1/detectors（detector清单+参数）；/api/docs（Swagger）
```
