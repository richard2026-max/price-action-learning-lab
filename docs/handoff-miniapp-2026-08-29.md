# 微信小程序改造交接说明（2026-08-29）

## 0. 第二轮更新（同日晚）：双端契约统一 + 安全边界补齐

在第一轮交接之后，又完成了两块 P0 工作（均为未提交工作区改动）：

### 0.1 双端契约统一（解决"桌面版持续更新，小程序如何同步"）

- **Web 桌面端已切换到共享包**：`apps/web/src/api/client.ts` 的回放/判断类型
  （Bar/KeyLevels/SessionInfo/SessionDetail/Judgment/Candidate/Annotation/
  ReplaySessionSummary/JudgmentPayload/Provider）改为从
  `@price-action/api-contracts`、`@price-action/domain` 再导出，并保留旧名称
  别名（`Candidate`/`Judgment`/`Annotation`），桌面版其余代码零改动。
- **判断校验与文案两端统一**：`packages/domain/src/validation.ts` 新增
  `judgmentErrorMessages` 与 `firstJudgmentErrorMessage`；Web `JudgmentForm`
  与小程序 `PredictForm` 均调用同一 `validateJudgment`。
- **同步工作流手册**：新增 `docs/miniapp-web-sync.md` —— 桌面版改接口/改规则时
  小程序的四类跟进场景、统一验证命令、目录对照表、兼容约定、变更日志。
- **统一验证命令**：根 `package.json` 新增 `npm run check`
  （共享包测试+构建 → 两端 typecheck → 两端生产构建）。
- 小程序删除了 `utils/mock.ts`（本地假 K 线与 no-lookahead 纪律冲突且已无引用）。
- 小程序请求层（`services/request.ts`）增加 401/403 自动清 token → 重登 → 重试一次。

⚠️ 已知状态：`apps/web/src/replay/ReplayWorkbench.tsx` 与
`apps/web/src/chart/CandleChart.tsx` 存在**你本人正在进行的 ChartOverlays 接线**
（状态已声明、UI 未接完），完整 `tsc -b` 会报 3 个 unused 变量错误。
本轮契约改动已用隔离方式验证通过（client.ts + JudgmentForm.tsx 单独 typecheck OK，
`vite build` 打包 OK）。等你完成 overlays 后跑 `npm run check` 即可全绿。
不要回滚这两个文件。

### 0.2 安全边界补齐（handoff §6 P0 第二项，除 refresh 外全部完成）

- **Scanner 归属**：`scan_tasks.user_id`（迁移 `0003`，旧数据回填 legacy user，
  升级/回退冒烟通过）；任务、候选列表、候选审核全部按当前用户过滤；
  用户 B 对用户 A 的任务/候选一律 404。
- **Analytics 按用户过滤**：overview/trade-stats/recheck-queue/recheck 全部
  只统计当前用户的会话、判断、候选（候选经 scan_tasks 串联归属）。
- **Coach 鉴权**：所有 coach 路由要求认证；review/analogs/summary-review 先校验
  session 归属；相似走势图片接口要求认证。
- **知识库版权保护**：`/knowledge/page-image`、`/search`、`/concept/{term}`
  要求认证（原书/课件页面不再匿名可取）。
- **运维接口**：`POST /data/seed` 仅 debug 模式可用（生产 403）；seed 逻辑抽到
  `app/services/data_seed_service.py` 供路由与 CLI 共用（修掉 CLI 直调路由的
  mypy 错误）；`/data/datasets` 要求认证。
- **启动守卫**：`PALL_DEBUG=false` 且未配置 `PALL_AUTH_TOKEN_SECRET` 时
  `create_app` 直接 RuntimeError，拒绝静默随机密钥。
- **新增测试** `apps/api/tests/test_security_boundaries.py`（4 项）+
  `test_auth_and_replay_idempotency.py`（3 项）。

### 0.3 第二轮验证结果

- 后端：**106 项测试全绿**（原 98 + 安全边界 8），Ruff 0 违规，Mypy 0 错误（76 文件）。
- 共享包：16 项测试通过；Web（vite 打包）通过；小程序 typecheck+build 通过。
- 迁移链 `0001→0002→0003→0001` SQLite 升级/回退冒烟通过。

### 0.4 更新后的下一步优先级

1. 真机联调与真实微信登录（不变，见 §6 P0 第一项）。
2. Web 端 advance 接入幂等字段（`expected_cursor_version`/`request_id`），
   与小程序对齐（见 miniapp-web-sync.md 变更日志）。
3. 小程序指定日期训练、判断列表恢复锁定状态、Canvas 交互增强（§6 P1）。
4. Token refresh 机制（原 P0 项中唯一未做，当前以"401 重登"替代）。

---

## 1. 当前结论

本轮已经把“小程序版”的基础架构和第一版训练闭环代码搭好，并将现有本地单用户回放后端升级到具备基础身份、回放资源隔离和移动网络幂等能力的状态。

当前代码可作为下一轮继续开发的稳定起点：

- 后端全量测试：**98 passed**。
- Ruff：通过。
- Mypy：通过。
- 共享 TypeScript 包：**16 tests passed**。
- 现有 Web：生产构建通过。
- Taro 微信小程序：`build:weapp` 通过。
- Alembic：`0001 -> 0002 -> 0001` SQLite 升级/回退冒烟测试通过。

本轮没有提交 Git，也没有部署或上传微信体验版。

## 2. 已确定的技术路线

- 保留现有 React Web，不重写、不用 `web-view` 包装。
- 新增独立 `apps/miniapp`，技术栈为 Taro 4 + React + TypeScript + Zustand。
- 小程序 K 线使用 Canvas 2D，不复用依赖 DOM 的 Lightweight Charts。
- 市场数据和 no-lookahead 仍以 FastAPI `ReplayService` 为唯一权威边界。
- 移动网络失败时不得在客户端离线推进 K 线；客户端只能重新读取服务端游标。
- 第一版定位为个人体验版/少量白名单用户，仍保留向正式多用户版演进的所有权边界。

## 3. 新增工程结构

### 仓库 workspace

- `package.json`：npm workspaces 和统一 build/test/typecheck 命令。
- `package-lock.json`：统一 Node 依赖锁文件。
- `tsconfig.base.json`：共享 TypeScript 基础约束。

### 共享包

- `packages/domain`
  - Replay/Judgment 核心类型。
  - Two Reasons、多空 Entry/Stop/Target 验证。
  - 价格和美东时间格式化。
- `packages/api-contracts`
  - Replay 请求和响应 DTO。
  - `cursor_version`、推进幂等字段。
- `packages/chart-core`
  - 价格范围、窗口截取、K 线几何、关键价位几何。
- `packages/design-tokens`
  - 深色金融终端颜色、间距、字体、图表主题。

### 小程序

目录：`apps/miniapp`

已实现：

- 四个 Tab：训练、记录、统计、我的。
- 训练协议选择和随机训练创建。
- Replay 服务端游标页面。
- Canvas 2D K 线、EMA20、PDH/PDL/PDC。
- Predict First 四步表单。
- Two Reasons 和价格顺序共享验证。
- Advance 的 `expected_cursor_version + request_id`。
- Judgment 的 `client_request_id`。
- 历史会话列表与服务端恢复。
- 基础学习统计页面。
- 开发登录和生产微信登录调用入口。
- API 失败时不再使用本地 mock 推进未来 K 线。

开发 API 配置：

```text
apps/miniapp/.env.development
TARO_APP_API_BASE=http://127.0.0.1:8000/api/v1
```

生产域名仍是占位值，发布前必须修改：

```text
apps/miniapp/.env.production
TARO_APP_API_BASE=https://api.example.com/api/v1
```

## 4. 后端改造

### 身份

新增：

- `apps/api/app/api/routes/auth.py`
- `apps/api/app/schemas/auth.py`
- `apps/api/app/services/auth_service.py`
- `apps/api/app/repositories/user_repo.py`

接口：

- `POST /api/v1/auth/dev-login`
- `POST /api/v1/auth/wechat/login`
- `GET /api/v1/auth/me`

开发模式下，如果业务请求没有 Bearer token，仍可映射到 legacy local user，以保证现有 Web 和原测试兼容。

生产必须配置：

```text
PALL_AUTH_TOKEN_SECRET
PALL_WECHAT_APP_ID
PALL_WECHAT_APP_SECRET
PALL_WECHAT_ALLOWED_OPENIDS   # 个人体验版建议配置
PALL_DEBUG=false
PALL_LEGACY_LOCAL_USER_ENABLED=false
```

### 数据模型和迁移

迁移：

- `apps/api/alembic/versions/0002_auth_and_replay_idempotency.py`

增加：

- `users` 表。
- `replay_sessions.user_id`。
- `replay_sessions.cursor_version`。
- `replay_advance_requests` 幂等记录表。
- `judgments.client_request_id` 唯一幂等字段。
- 旧数据回填到 legacy local user。

### Replay 隔离和幂等

主要文件：

- `apps/api/app/api/routes/replay.py`
- `apps/api/app/replay/service.py`
- `apps/api/app/repositories/replay_repo.py`
- `apps/api/app/schemas/replay.py`

已完成：

- Replay session 创建、读取、推进、后退、删除、判断、标注都按当前用户校验。
- 用户 A 获取用户 B 的 session 返回 404。
- 相同 advance `request_id` 重试不会重复推进。
- 同一 `request_id` 配不同参数返回 409。
- `expected_cursor_version` 冲突返回 409。
- 相同 Judgment `client_request_id` 重试返回原记录。
- 原 no-lookahead 测试继续通过。

新增测试：

- `apps/api/tests/test_auth_and_replay_idempotency.py`

## 5. 立即可用的验证命令

从仓库根目录：

```bash
npm install
npm run test:packages
npm run build:packages
npm run build:web
npm run build:miniapp
```

后端：

```bash
cd apps/api
.venv/Scripts/python -m pytest tests/
.venv/Scripts/python -m ruff check app tests
.venv/Scripts/python -m mypy app
```

开发联调：

```bash
# 终端 1
cd apps/api
.venv/Scripts/python -m app.cli api

# 终端 2
cd apps/miniapp
npm run dev:weapp
```

然后使用微信开发者工具打开：

```text
apps/miniapp
```

`project.config.json` 中 AppID 仍需替换为真实 AppID；`project.private.config.json` 已由根 `.gitignore` 排除。

## 6. 下一模型应优先处理的事项

按顺序执行，不要先扩功能。

### P0：真机联调和认证闭环

1. 配置真实微信 AppID/AppSecret 和测试 openid 白名单。
2. 在微信开发者工具验证 `wx.login -> /auth/wechat/login`。
3. 在 iOS 和 Android 真机完成：登录、创建 session、提交判断、推进、退出后恢复。
4. 检查 Canvas 的 DPR、时间标签和页面返回后的重绘。
5. 将 API 域名加入微信 request 合法域名。

### P0：安全边界补齐

当前只完整隔离了 Replay 和通过 Replay 校验的 Trade 入口。正式对外前还需要：

- Analytics 查询按用户过滤。
- Scanner task/candidate 增加 user_id 和所有权。
- Coach、Reviews、知识图片接口增加身份和 session 所有权校验。
- 数据 seed/ingest 等运维接口增加管理员权限，生产不能给普通用户调用。
- 增加 token refresh 或重新登录策略。
- 生产环境若 `PALL_AUTH_TOKEN_SECRET` 缺失应直接启动失败，不能随机生成临时密钥。

### P1：小程序体验完善

- 训练首页增加指定日期选择，不只随机日期。
- 历史记录增加筛选和删除二次确认。
- Replay 页面加载判断列表，准确恢复当前 bar 是否已锁定，而不是只根据 candidates 推断。
- 回放结束状态和“完成训练”反馈。
- Canvas 增加点击 OHLC、已揭示历史左右拖动。
- 用共享 design tokens 替换小程序 SCSS 中剩余硬编码色值。
- 增加小程序组件测试和自动化 E2E。

### P1：统计口径

小程序统计页面目前调用现有 Analytics API。该 API 仍是本地单用户时期的全库口径；完成用户隔离前不能把它作为公开多用户版本的个人统计。

## 7. 已知风险

### npm audit

`npm audit --omit=dev` 当前报告：

- 10 moderate
- 1 high
- 3 critical

主要来自 Taro 间接依赖：Swiper、Webpack、esbuild、uuid、webpack-dev-server。自动建议的 `npm audit fix --force` 会把部分 Taro 包降到 3.x，属于破坏性变更，**不要直接执行**。

建议下一轮：

1. 先确认 Taro 4.2.x 是否已有修复版本或官方升级建议。
2. 使用微信小程序目标构建评估实际打包是否包含相关 Web-only 漏洞路径。
3. 单独升级 Webpack 可修复的非破坏性项，并完整重跑小程序构建和真机测试。

### 认证实现

当前 token 是轻量 HMAC 自包含 token，不是完整 JWT/refresh-token 体系。个人体验版足够做基础隔离，但公开正式版应补充密钥轮换、刷新、吊销和审计策略。

### 迁移与旧数据库

`0002` 已通过空 SQLite 的升级和回退测试，但尚未在用户真实 `data/app.sqlite` 上执行。操作真实库前必须先备份：

```text
data/app.sqlite
data/app.sqlite-wal
data/app.sqlite-shm
```

然后运行 `alembic upgrade head` 并检查旧 session 是否归入 legacy user。

## 8. 本轮明确未完成

- 未配置真实 AppID、AppSecret、HTTPS 域名。
- 未在微信开发者工具和真机进行视觉/交互验收。
- 未上传体验版或提交微信审核。
- 未部署公网 API。
- 未做 Scanner、Coach、Analytics 的完整用户隔离。
- 未实现 refresh token。
- 未建立 CI/CD。
- 未解决 Taro 依赖审计告警。
- 未提交 Git。

## 9. 工作区状态

所有改动都在未提交工作区。切换模型后先执行：

```bash
git status --short
git diff --stat
```

不要重置或清理未跟踪目录，尤其是：

```text
apps/miniapp/
packages/
apps/api/alembic/versions/0002_auth_and_replay_idempotency.py
apps/api/app/api/routes/auth.py
apps/api/tests/test_auth_and_replay_idempotency.py
package.json
package-lock.json
```

建议下一次稳定真机联调后再统一提交。当前最合适的下一步不是增加 Scanner/AI，而是完成真实微信登录与真机训练闭环验收。
