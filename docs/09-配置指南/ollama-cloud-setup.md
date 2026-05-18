# Ollama Cloud 云端模型配置指南

## 📦 Ollama Cloud 是什么？

Ollama Cloud 是 Ollama 的云端服务，允许你在没有强大 GPU 的情况下运行大型语言模型。

**重要**：Ollama Cloud **不是独立的 REST API**，而是通过本地 Ollama 服务调用的云端模型。

---

## 🔧 配置步骤

### 1️⃣ 登录 Ollama 账号

```bash
ollama signin
```

这会打开浏览器让你登录 ollama.com 账号。

---

### 2️⃣ 拉取云端模型

选择你想要的云端模型并拉取：

```bash
# 示例：拉取 GPT-OSS 120B 云端模型
ollama pull gpt-oss:120b-cloud

# 其他可用的云端模型
ollama pull llama3.1:70b-cloud
ollama pull qwen2.5:72b-cloud
ollama pull mixtral:8x7b-cloud
```

查看完整云端模型列表：https://ollama.com/search?c=cloud

---

### 3️⃣ 重启 Ollama 服务

```bash
# 停止现有服务（如果有）
pkill -f "ollama serve"

# 重新启动
ollama serve
```

---

### 4️⃣ 验证云端模型

```bash
# 查看已安装的模型（应该能看到带-cloud 后缀的）
ollama list

# 测试云端模型
ollama run gpt-oss:120b-cloud "你好，请用一句话介绍自己"
```

---

### 5️⃣ 在图纸 AI 助手中使用

1. 打开 http://127.0.0.1:5189
2. 进入 **个人设置 → 🧠 AI 模型设置**
3. 在"可用模型"列表中找到 `ollama:gpt-oss:120b-cloud` 等云端模型
4. 点击"添加"将其加入你的模型链
5. 调整优先级（拖拽或上下箭头）
6. 点击"💾 保存设置"

---

## ✅ 验证配置

### 测试云端模型响应时间

在"🧪 AI 模型设置"页面：
- 点击"🧪 测试当前首选模型"测试单个模型
- 或点击"📊 批量测试所有模型"查看所有模型的速度排名

### 预期结果

| 模型类型 | 响应时间 | 说明 |
|----------|----------|------|
| 本地模型（7B-9B） | 1-5 秒 | 取决于你的硬件 |
| 云端模型（70B-120B） | 5-15 秒 | 取决于网络和模型大小 |

---

## 🛠️ 故障排查

### 问题 1: `ollama signin` 失败

**原因**: 网络连接问题或 Ollama 版本过旧

**解决**:
```bash
# 检查 Ollama 版本
ollama --version

# 更新 Ollama（macOS）
brew upgrade ollama

# 更新 Ollama（Linux）
curl -fsSL https://ollama.com/install.sh | sh
```

---

### 问题 2: 拉取云端模型失败

**原因**: 网络问题或模型名称错误

**解决**:
```bash
# 检查网络连接
curl -I https://ollama.com

# 确认模型名称（必须带-cloud 后缀）
ollama pull llama3.1:70b-cloud  # ✅ 正确
ollama pull llama3.1:70b        # ❌ 这是本地模型
```

---

### 问题 3: 图纸 AI 助手看不到云端模型

**原因**: Ollama 服务未重启或 API 未刷新

**解决**:
```bash
# 1. 重启 Ollama 服务
pkill -f "ollama serve"
ollama serve &

# 2. 重启图纸 AI 助手 API
pkill -f "api_server.py"
cd /mnt/d/OpenClawDataworkspace/Projects/blueprint-ai
python3 src/api_server.py &

# 3. 刷新浏览器页面（Ctrl+F5 强制刷新）
```

---

## 💡 提示

- **本地优先**: 建议将本地模型（如 qwen3.5:9b）设为首选，云端模型作为备选
- **成本**: Ollama Cloud 目前免费，但未来可能收费
- **速度**: 云端模型比本地慢（网络延迟），但能力更强
- **隐私**: 敏感数据建议使用本地模型

---

## 📚 相关资源

- Ollama Cloud 文档：https://docs.ollama.com/cloud
- 云端模型列表：https://ollama.com/search?c=cloud
- Ollama 下载：https://ollama.com/download
