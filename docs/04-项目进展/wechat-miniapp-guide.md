# 微信小程序申请与对接指南

> 本文档指导如何申请微信小程序，并将真实微信登录接入 EMA 系统。

---

## 一、申请微信小程序（5步）

### Step 1: 注册小程序账号

1. 打开 https://mp.weixin.qq.com
2. 点击"立即注册"
3. 选择"小程序"
4. 填写邮箱（未注册过微信公众平台的邮箱）+ 密码
5. 邮箱激活 → 完成注册

### Step 2: 实名认证

1. 登录 mp.weixin.qq.com
2. 左侧菜单 → "设置" → "基本设置"
3. 点击"微信认证"
4. 选择认证方式：
   - **企业**：提交营业执照 + 法人身份证 + 300元/年认证费
   - **个人**：无需费用，但功能受限（不支持支付、OAuth等）
5. ⚠️ **个人小程序不支持网页授权登录（OAuth2.0），必须用企业认证**

### Step 3: 获取 AppID + AppSecret

1. 登录 mp.weixin.qq.com
2. 左侧菜单 → "开发" → "开发管理"
3. 找到"开发设置"
4. 复制 **AppID** 和 **AppSecret**
5. ⚠️ AppSecret 只显示一次，务必保存好

### Step 4: 配置服务器域名

1. "开发设置" → "服务器域名"
2. 修改以下三项：
   - **request合法域名**：`https://你的服务器域名`
   - **socket合法域名**：`wss://你的服务器域名`
   - **uploadFile合法域名**：`https://你的服务器域名`
3. 如果是开发阶段，可以用 `http://localhost:6188`（需在微信开发者工具中勾选"不校验合法域名"）

### Step 5: 配置业务域名（网页授权用）

1. "开发设置" → "业务域名"
2. 添加你的服务器域名
3. 下载验证文件放到服务器根目录

---

## 二、EMA 接入配置（拿到 AppID 后）

### 方式 A：公众号 OAuth2.0（推荐，最简单）

适用场景：用户在**网页/浏览器**上扫码登录

#### 1. 后端配置

```bash
# 在服务器环境变量中设置
export WECHAT_MODE=real
export WECHAT_APP_ID=你的AppID
export WECHAT_APP_SECRET=你的AppSecret
export WECHAT_REDIRECT_URI=https://你的域名/api/v1/auth/wechat-callback
export EMA_HOST=你的域名:6189
```

#### 2. 重启 API

```bash
cd /path/to/engineering-management-agent
python3 -m uvicorn src.api_server:app --host 0.0.0.0 --port 6188
```

#### 3. 验证

打开 `http://你的域名:6189/login.html` → 点击"微信扫码" → 应该显示真实的微信二维码

---

### 方式 B：小程序 wx.login()

适用场景：用户在**微信小程序**内登录

#### 1. 小程序端代码（需要在微信开发者工具中开发）

```javascript
// 小程序端
wx.login({
  success(res) {
    if (res.code) {
      // 把 code 传给 EMA 后端
      wx.request({
        url: 'https://你的域名/api/v1/auth/wechat-minilogin',
        method: 'POST',
        data: {
          code: res.code,
          // 可选：用户信息
          nickName: userInfo.nickName,
          avatarUrl: userInfo.avatarUrl
        },
        success(result) {
          // 返回 access_token
          wx.setStorageSync('ema_token', result.data.access_token);
        }
      });
    }
  }
});
```

#### 2. 后端新增端点（需要 GDP影子 帮加）

在 `src/api_server.py` 中添加 `/api/v1/auth/wechat-minilogin` 端点，用 `jscode2session` API 换 openid。

---

## 三、两种方式对比

| 特性 | 公众号 OAuth2.0 | 小程序 wx.login() |
|------|----------------|-------------------|
| 适用场景 | 网页/浏览器扫码 | 小程序内登录 |
| 用户感知 | 扫码→确认→登录 | 静默登录 |
| 需要公众号 | ✅ 需要 | ❌ 不需要 |
| 需要小程序 | ❌ 不需要 | ✅ 需要 |
| 开发复杂度 | 低 | 中 |
| EMA 支持 | ✅ 已就绪 | ⚠️ 需新增端点 |

---

## 四、常见问题

### Q1: 个人能申请小程序吗？
可以，但**个人小程序不支持 OAuth 网页授权**，只能做小程序内登录（方式B）。

### Q2: 认证费用？
- 企业认证：300元/年
- 个人：免费（功能受限）

### Q3: 没有服务器域名怎么办？
开发阶段可以用：
- 微信开发者工具勾选"不校验合法域名"
- 用 ngrok 内网穿透：`ngrok http 6188`

### Q4: 测试环境怎么测？
EMA 默认是 **mock 模式**，无需微信账号即可测试整个流程。拿到真实 AppID 后改 `WECHAT_MODE=real` 即可切换。

---

## 五、下一步

1. 申请小程序/公众号
2. 拿到 AppID + AppSecret
3. 发给 GDP影子
4. 10 分钟完成接入
5. 线上验证

---

> 💡 **建议**：先用 mock 模式跑通全部流程 → 申请小程序 → 拿到 AppID → 一键切换真实模式。
