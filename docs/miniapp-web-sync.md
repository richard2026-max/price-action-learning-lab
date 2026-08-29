# 双端同步工作流（Web 桌面版 ↔ 微信小程序）

> 目标：桌面 Web 版持续迭代时，小程序版以最低成本保持逻辑与契约一致。
> 核心机制：**一个后端 + 一层共享包 + 一条统一验证命令**。

---

## 1. 架构原则

```text
apps/web ─────────┐
                  ├──> @price-action/api-contracts（DTO 契约）
apps/miniapp ─────┤──> @price-action/domain（类型 + 判断验证 + 格式化）
                  ├──> @price-action/chart-core（K线几何）
                  └──> @price-action/design-tokens（视觉令牌）
                          │
                          ▼
                  apps/api（唯一后端，唯一权威）
```

规则：

1. **业务逻辑只有一个权威**：后端 Pydantic 校验是提交时最终权威；共享包的
   `validateJudgment` 是两端一致的即时反馈层。文案统一取自
   `packages/domain/src/validation.ts` 的 `judgmentErrorMessages`。
2. **DTO 只定义一次**：回放/判断相关接口类型只在 `packages/api-contracts` 定义。
   Web 端 `apps/web/src/api/client.ts` 用 `export type { ... } from` 再导出；
   小程序端 `apps/miniapp/src/types/market.ts` 做同样映射。
3. **客户端不允许有第二份业务事实**：小程序不得本地推进游标、不得生成假 K 线
   （`utils/mock.ts` 已删除）、网络失败只能重新读服务端状态。
4. **桌面版特有模块**（Scanner 工作台、AI Coach 面板、Analytics 大屏、SimTrade、
   Data 管理）的类型暂留在 `apps/web/src/api/client.ts`；哪一天小程序要用，
   先把对应 DTO 上移到 contracts，再两端引用。

## 2. 桌面版改动后，小程序如何跟进

### 场景 A：后端接口加了字段（最常见）

1. 在 `packages/api-contracts`（或 `domain`）给对应 DTO 加字段。
   - 新增可选字段 → 两端零破坏，直接加。
   - 新增必填字段 → 先同时改两端消费代码，再收紧类型。
2. 根目录运行 `npm run check`（见 §3）。
3. 小程序页面需要展示新字段时，改 `apps/miniapp` 对应页面。

### 场景 B：后端加了新接口

1. contracts 加请求/响应类型。
2. Web 在 `client.ts` 加请求函数。
3. 小程序在 `apps/miniapp/src/services/` 加对应 service。
4. `npm run check`。

### 场景 C：改了判断规则 / 校验逻辑

1. 只改 `packages/domain/src/validation.ts`（规则 + 文案）。
2. `npm run test:packages` —— 共享包单测守门。
3. 两端自动继承，**禁止**在 `JudgmentForm.tsx`（Web）或
   `predict-form/index.tsx`（小程序）里各自加规则。

### 场景 D：后端改了行为语义（如模式规则、游标行为）

1. 先在后端改 + 加集成测试。
2. contracts 里同步注释/类型。
3. 在本文档末尾"变更日志"表追加一行。

## 3. 统一验证命令（每次同步必跑）

```bash
# Node 侧全量：共享包测试+构建、Web/小程序 typecheck、两端生产构建
npm run check

# 后端全量
cd apps/api
.venv/Scripts/python -m pytest tests/
.venv/Scripts/python -m ruff check app tests
.venv/Scripts/python -m mypy app
```

注意：`npm run check` 里的 Web `typecheck` 目前包含你正在进行的
`ChartOverlays` 接线改动；如果该文件未完成，可临时只跑：

```bash
npm run test:packages && npm run build:packages && npm run typecheck:miniapp && npm run build:miniapp
cd apps/web && npx tsc --noEmit --strict ... src/api/client.ts src/replay/JudgmentForm.tsx  # 见 handoff §第二轮
```

## 4. 小程序目录对照表

| 关注点 | Web 位置 | 小程序位置 | 共享来源 |
|---|---|---|---|
| 回放 DTO | `apps/web/src/api/client.ts`（再导出） | `apps/miniapp/src/types/market.ts` | `packages/api-contracts` |
| 判断类型 | 同上 | 同上 | `packages/domain` |
| 判断校验+文案 | `JudgmentForm.tsx` 调 `validateJudgment` | `predict-form/index.tsx` 调同一函数 | `packages/domain/src/validation.ts` |
| K线几何 | Lightweight Charts（DOM） | `components/candlestick-chart`（Canvas） | `packages/chart-core` |
| 请求层 | fetch（同源 `/api/v1`） | `services/request.ts`（Taro.request + Bearer + 401 重登） | — |
| 认证 | 本地 legacy（debug） | `services/auth.ts`（dev-login / wechat login） | 后端 `/auth/*` |
| 状态 | React state | `store/app-store.ts`（Zustand） | — |

## 5. 版本与兼容约定

- 后端对旧客户端保持向后兼容：新增字段可先下发；删除/改义字段必须经过
  "先加新、后弃旧"两步。
- 小程序是弱升级环境（用户可能长期停留在旧版本）：删除任何响应字段前，
  确认小程序已发版覆盖。
- `replay_sessions.cursor_version` / advance 幂等 / judgment 幂等是双端共用的
  并发协议，两端都不得绕过（Web 端 `advance` 目前未传幂等字段，属已知待办，
  见 handoff）。

## 6. 变更日志

| 日期 | 契约/规则变更 | 两端动作 |
|---|---|---|
| 2026-08-29 | `SessionInfo` 增加 `cursor_version`；advance 增加 `expected_cursor_version`/`request_id`；judgment 增加 `client_request_id` | 小程序已接入；Web 待接入幂等字段 |
| 2026-08-29 | 判断校验规则+中文文案统一到 `@price-action/domain` | Web `JudgmentForm`、小程序 `PredictForm` 均已切换 |
| 2026-08-29 | Web 切换到共享 contracts（Bar/KeyLevels/SessionInfo/SessionDetail/Judgment/Candidate/Annotation/Summary） | 完毕 |
| 2026-08-29 | Scanner 任务归属用户（`scan_tasks.user_id`）；Analytics/Coach/知识库按用户隔离 | 后端完成，两端无需改动（协议不变） |
