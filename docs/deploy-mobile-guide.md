# 手机随时可用路线图：ICP 备案 + 上线部署

> 决策（2026-08-29）：走 ICP 备案路线，获得公网 HTTPS 域名 + 微信小程序体验版，
> 实现"随时在手机上用"。本文是执行手册。
>
> 核心事实：**备案免费、个人主体可办、材料半天完成，等待期约 1–2 周；
> 等待期间手机已经可以通过临时通道使用系统**。备案完成后切换正式通道，
> **代码零改动，只改配置**。

---

## 0. 全景时间线

| 阶段 | 时间 | 你能做什么 |
|---|---|---|
| 今天 | ~1 小时操作 | 注册小程序账号拿 AppID；买域名+服务器；提交备案 |
| 等待期 | 第 1–2 周 | 手机经"临时通道"正常使用（见 §2）；桌面版照常开发 |
| 备案通过 | +半天 | 配 HTTPS + 合法域名，上传正式体验版，永久通道生效 |
| 长期 | — | 任何网络下手机随时可用 |

费用合计约 **¥150–400/年**（域名 ¥50–100/年 + 轻量服务器 ¥100–300/年）。备案本身免费。

---

## 1. 今天要做的三件事

### 1.1 注册微信小程序账号（免费，立刻拿 AppID）

- 地址：mp.weixin.qq.com → 立即注册 → 小程序 → **个人主体**
- 需要：未绑定过的邮箱、手机号、身份证 + 人脸核验
- 注册完在「设置 → 基础设置」拿到 **AppID**；AppSecret 在「开发管理 → 开发设置」生成
- **注册不需要任何域名**，今天就完成
- 填入两处：
  - `apps/miniapp/project.config.json` 的 `appid`
  - 后端 `.env` 的 `PALL_WECHAT_APP_ID` / `PALL_WECHAT_APP_SECRET`

### 1.2 买域名 + 轻量云服务器

- 域名：任意注册商，`.com` 或 `.cn` 均可，¥50–100/年
- 服务器：腾讯云/阿里云**轻量应用服务器** 2C2G 即可（跑 FastAPI + SQLite + Parquet 绰绰有余），¥100–300/年
- 建议域名和服务器**买在同一家云厂商**（备案流程一体，体验最顺）
- 服务器选**中国大陆地域**（备案前提），系统 Ubuntu 22.04/24.04

### 1.3 提交 ICP 备案（免费，~半小时材料 + 1–2 周审核）

- 云厂商控制台都有「ICP 备案」入口，全程线上：身份证正反面 + 人脸 + 手机号核验
- 个人备案**网站名称是最大被驳回点**：用朴素、非商业字眼，
  例如「价格行为学习记录」「XX 的学习笔记」；**避免**「平台 / 系统 / 中心 / 交易 / 金融」字眼
- 首次备案期间域名不能对外解析提供服务——对本项目无影响（该域名本来就还没启用）
- 被驳回不用慌：改名重新提交即可，不影响其他材料

---

## 2. 备案等待期：手机现在就能用（两条临时通道）

微信的规则：**正式版**强制"HTTPS + 已备案域名 + 白名单"；但**开发版/体验版在手机上打开"开发调试"后，跳过域名校验**。这就是等待期的通道。

### 路线 A（推荐）：体验版 + 开发调试，走公网服务器

1. DevTools 导入 `apps/miniapp`（填 AppID）→ 上传 → 控制台设为体验版（你自动是体验成员）
2. 手机微信打开该体验版 → 右上角「···」胶囊 → **开发调试** → 确认开启
   （此后该会话不校验合法域名，HTTP/IP 均可请求）
3. 后端部署到云服务器，暂用纯 IP（见 §4，可先跳过 nginx/证书）：
   - `uvicorn` 监听 8000，安全组放行 8000 端口
   - `apps/miniapp/.env.development` 的 `TARO_APP_API_BASE` 改为 `http://<服务器IP>:8000/api/v1`
4. 登录即真实链路：`wx.login → /auth/wechat/login`（服务器配置 `PALL_WECHAT_APP_ID/SECRET`）
   - 首次登录如果不知道自己的 openid，`PALL_WECHAT_ALLOWED_OPENIDS` 先留空（=不限制；
     反正体验成员只有你自己）。登录一次后从 `users` 表查到 openid，
     再填进白名单收紧（`SELECT provider, subject, display_name FROM users;`）
5. 注意：服务器 `PALL_DEBUG=false` 时 `/auth/dev-login` 返回 404，这是预期行为（我们加的守卫）

> 临时开放 8000 到公网仅限备案等待期，且系统已带 Bearer 认证 + 用户隔离。
> 备案完成后收紧回 443。

### 路线 B（完全本地）：手机与电脑同一 WiFi

- 电脑跑 `start-backend.cmd`，`apps/miniapp/.env.development` 改为
  `TARO_APP_API_BASE=http://<电脑局域网IP>:8000/api/v1`（手机访问 127.0.0.1 指向手机自己，必须写电脑 IP）
- DevTools 勾选「不校验合法域名」→ 预览 → 手机扫码即用
- 离开 WiFi 即失效，仅适合家里练手；正式通道见 §3

---

## 3. 备案通过后：正式通道（半天，一次配好永久生效）

1. **DNS**：域名 A 记录 → 服务器公网 IP
2. **HTTPS**：云厂商免费 DV 证书（或 certbot/Let's Encrypt），绑定域名
3. **nginx 反代**：443 → uvicorn:8000（配置见 §4）
4. **小程序后台**：「开发管理 → 开发设置 → 服务器域名」把 `https://你的域名` 加入
   **request 合法域名**（此刻域名已备案，校验能过）
5. `apps/miniapp/.env.production` 改为 `https://你的域名/api/v1` → `npm run build:miniapp` → 上传体验版
6. **生产环境变量**（服务器 `.env`，缺 `PALL_AUTH_TOKEN_SECRET` 会拒绝启动——我们加的守卫）：

```text
PALL_DEBUG=false
PALL_AUTH_TOKEN_SECRET=<openssl rand -base64 48 生成，妥善保存>
PALL_LEGACY_LOCAL_USER_ENABLED=false
PALL_WECHAT_APP_ID=<AppID>
PALL_WECHAT_APP_SECRET=<AppSecret>
PALL_WECHAT_ALLOWED_OPENIDS=<你的openid>
PALL_DATA_DIR=/srv/app/data
PALL_SQLITE_PATH=/srv/app/data/app.sqlite
```

7. **备份**：cron 每日打包 `data/`（SQLite WAL 一并备份；恢复演练一次）
8. **可选**：AI Coach 原书图片若将来开放给小程序，同一域名再加 **downloadFile 合法域名**；
   个人自用阶段建议小程序端整体不开放该功能（版权边界，见 handoff §7）

---

## 4. 服务器部署要点

### 单机 docker compose（推荐形态）

```yaml
# compose.prod.yaml（服务器仓库根）
services:
  api:
    build: apps/api
    restart: unless-stopped
    ports: ["127.0.0.1:8000:8000"]
    volumes: ["./data:/srv/app/data"]
    env_file: [.env]

  nginx:
    image: nginx:stable
    restart: unless-stopped
    ports: ["80:80", "443:443"]
    volumes:
      - ./infra/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./infra/certs:/etc/nginx/certs:ro
    depends_on: [api]
```

```nginx
# infra/nginx.conf 关键段
server {
    listen 443 ssl;
    server_name 你的域名;
    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    location /api/ {
        proxy_pass http://api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 迁移与发布顺序（重要）

```bash
# 首次部署 / 每次升级：
cd apps/api
cp data/app.sqlite data/app.sqlite.bak-$(date +%F)   # 迁移前备份
alembic upgrade head                                   # 0001→0002→0003
docker compose -f compose.prod.yaml up -d --build
```

- 数据库文件在 volume 里，`--build` 重新部署不会丢
- 行情 Parquet 首次用 `python -m app.cli data seed`（服务器上临时 `PALL_DEBUG=true` 跑一次）
  或从本地 `data/` 打包上传，避免服务器上生成

---

## 5. 风险与注意

| 风险 | 说明 | 对策 |
|---|---|---|
| 备案被驳回 | 多因网站名称含敏感/商业字眼 | 改名重提，其余材料不受影响 |
| 正式发布审核（若将来公众开放） | 微信对金融类目极严，个人主体难拿 | 维持"学习工具 + 合成数据"定位；体验版白名单阶段无此问题 |
| 原书图片版权 | 公开放开即红线 | 小程序端不开放 Coach 图片功能；已有认证门槛 |
| 临时 IP+8000 暴露 | 等待期端口对外开放 | 已有 Bearer+隔离；备案后关闭 8000 只留 443 |
| 备案号展示 | 已备案域名要求底部标备案号 | 纯 API 域名影响小；如做落地页记得挂 |

---

## 6. 与现有文档的关系

- 架构不变更的论证与安全边界：`docs/handoff-miniapp-2026-08-29.md`
- 双端同步机制：`docs/miniapp-web-sync.md`
- 本文只涉及**部署与合规**，代码层面的工作照 handoff §6 优先级继续
