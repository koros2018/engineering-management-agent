# 工程管理智能体 - 微信小程序

基于 `uni-app` (Vue 3) 构建的微信小程序客户端。

## 📁 项目结构

```
mini-program/
├── App.vue              # 应用入口
├── main.js              # Vue 初始化入口
├── manifest.json        # uni-app 应用配置
├── pages.json           # 页面路由与 tabBar 配置
├── pages/
│   ├── index/           # 工作台 (Agent选择 + 对话)
│   ├── upload/          # 图纸上传分析
│   ├── review/          # 审图结果查看
│   └── mine/            # 个人中心
├── static/              # 静态资源 (图标等)
└── README.md
```

## 🔧 开发环境

### 前置依赖

- Node.js >= 16
- HBuilderX (推荐) 或 CLI 方式
- 微信开发者工具

### 安装依赖

```bash
cd mini-program
npm install
```

### 运行开发版

**方式一：HBuilderX（推荐）**
1. 打开 HBuilderX
2. 导入 `mini-program` 目录
3. 选择「运行」→「运行到小程序模拟器」→「微信开发者工具」

**方式二：CLI**

```bash
# 安装 cli
npm install -g @vue/cli @dcloudio/uni-cli

# 开发模式
npm run dev:mp-weixin

# 构建生产版
npm run build:mp-weixin
```

生成的微信小程序代码在 `dist/dev/mp-weixin/`，用微信开发者工具打开即可。

## 🚀 构建生产版本

```bash
# 微信小程序
npm run build:mp-weixin

# 输出的代码在 dist/build/mp-weixin/
```

将 `dist/build/mp-weixin/` 导入到微信开发者工具即可测试和发布。

## 📡 API 配置

小程序默认连接 `http://127.0.0.1:5188`（本地开发服务器）。

如需修改，编辑各页面 `src` 中的 `API_BASE` 常量：
```js
const API_BASE = 'http://127.0.0.1:5188';
```

生产环境部署时需改为实际的服务器地址（必须是 HTTPS 或合法 HTTP 域名）。

## 🔐 登录机制

- 支持微信一键登录（`wx.login` + 后端 `/api/v1/auth/wechat-qr`）
- 登录态存储：`uni.setStorageSync('token', token)`
- 所有 API 请求自动附加 `Authorization: Bearer {token}` 头

## 📋 功能说明

### 工作台 (index)
- 加载并展示可用智能体列表（`GET /api/v1/agents`）
- 选择智能体后发送消息（`POST /api/v1/main/chat`）
- 支持多轮对话，展示消息列表

### 图纸上传 (upload)
- 本地图片选择（`uni.chooseImage`）
- 上传并分析（`POST /api/v1/upload/analyze`）
- 支持选择图纸类型和关联项目
- 显示分析结果（评分、问题列表）

### 审图结果 (review)
- 查看当前报告详情（评分、摘要、问题列表）
- 历史报告列表切换
- 支持导出和分享（功能开发中）

### 个人中心 (mine)
- 微信一键登录（`wx.login` → `/api/v1/auth/wechat-qr`）
- 显示订阅套餐状态（`GET /api/v1/subscription/status`）
- 订阅方案展示与购买（`POST /api/v1/subscription/subscribe`）
- 基础菜单：使用记录、订单、设置、退出登录等

## 📌 注意事项

1. **不要使用 `window` / `document`** — 小程序无 DOM，直接用 `uni` API
2. **网络请求用 `uni.request`** — 不是 `axios` 或 `fetch`
3. **登录态用 `uni.getStorageSync` / `uni.setStorageSync`** — 不是 `localStorage`
4. **tabBar 图标** — 目前用 emoji，若需真实图标请在 `static/` 下放入 PNG 并在 `pages.json` 中配置路径
5. **微信开发者工具调试** — 需在项目详情中勾选「不校验合法域名」才能请求 `http://127.0.0.1`

## 🔗 相关 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/agents` | GET | 获取智能体列表 |
| `/api/v1/main/chat` | POST | 主对话接口 |
| `/api/v1/upload/analyze` | POST | 图纸分析 |
| `/api/v1/projects` | GET | 项目列表 |
| `/api/v1/conversations` | GET | 会话历史 |
| `/api/v1/subscription/plans` | GET | 订阅方案 |
| `/api/v1/subscription/status` | GET | 订阅状态 |
| `/api/v1/subscription/subscribe` | POST | 订阅购买 |
| `/api/v1/auth/wechat-qr` | POST | 微信登录 |
| `/api/v1/auth/me` | GET | 当前用户信息 |

> 详细 API 文档见 EMA 后端 `src/api_server.py`