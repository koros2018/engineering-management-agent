# 云端模型配置指南

## 当前状态

图纸 AI 助手的 LLM 模型分为三类：

| 类型 | 来源 | 启用条件 | 当前状态 |
|------|------|----------|----------|
| **本地模型** | Ollama 本地运行 | Ollama 已安装 | ✅ 已启用（4个） |
| **云端模型** | OpenAI / 兼容 API | 需配置 `LLM_CLOUD_KEY` | ❌ 未配置 |
| **规则引擎** | 内置逻辑 | 无需配置 | ✅ 永远可用 |

---

## 如何启用云端大模型

### 方案一：OpenAI API（推荐，最简单）

**1. 获取 API Key**
- 访问 https://platform.openai.com/api-keys
- 创建新 API Key

**2. 配置环境变量**

Linux/macOS:
```bash
export LLM_CLOUD_URL="https://api.openai.com/v1/chat/completions"
export LLM_CLOUD_KEY="sk-your-api-key-here"
export LLM_CLOUD_MODEL="gpt-4o-mini"  # 可选，默认 gpt-4o-mini
```

Windows (PowerShell):
```powershell
$env:LLM_CLOUD_URL="https://api.openai.com/v1/chat/completions"
$env:LLM_CLOUD_KEY="sk-your-api-key-here"
$env:LLM_CLOUD_MODEL="gpt-4o-mini"
```

**3. 重启 API 服务**
```bash
# 停止服务
pkill -f "api_server.py"

# 启动服务（自动加载环境变量）
cd /mnt/d/OpenClawDataworkspace/Projects/blueprint-ai
python3 src/api_server.py
```

**4. 验证**
```bash
curl http://127.0.0.1:5188/llm/models
# 应该看到新增了 cloud:gpt-4o-mini 和 cloud:gpt-4o
```

---

### 方案二：硅基流动（国内可用，额度免费）

**1. 注册硅基流动**
- 访问 https://account.siliconflow.cn
- 注册并获取 API Key

**2. 配置**
```bash
export LLM_CLOUD_URL="https://api.siliconflow.cn/v1/chat/completions"
export LLM_CLOUD_KEY="your-siliconflow-api-key"
export LLM_CLOUD_MODEL="Qwen/Qwen2.5-72B-Instruct"  # 或其他模型
```

---

### 方案三：阿里云百炼（国内可用）

**1. 获取 API Key**
- 访问 https://bailian.console.aliyun.com
- 创建 API Key

**2. 配置**
```bash
export LLM_CLOUD_URL="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
export LLM_CLOUD_KEY="your-aliyun-api-key"
export LLM_CLOUD_MODEL="qwen-plus"  # qwen-plus / qwen-max / qwen-turbo
```

---

## 启动脚本配置（持久化）

将环境变量写入启动脚本 `start.sh`，永久生效：

```bash
# 在 start.sh 的开头添加：
export LLM_CLOUD_URL="https://api.openai.com/v1/chat/completions"
export LLM_CLOUD_KEY="sk-your-key-here"
export LLM_CLOUD_MODEL="gpt-4o-mini"
```

或者创建一个 `.env` 文件：
```bash
# 在项目根目录创建 .env 文件
LLM_CLOUD_URL=https://api.openai.com/v1/chat/completions
LLM_CLOUD_KEY=sk-your-key-here
LLM_CLOUD_MODEL=gpt-4o-mini
```

然后在 `api_server.py` 开头添加：
```python
from pathlib import Path
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read().splitlines():
        if "=" in line:
            k, v = line.strip().split("=", 1)
            import os
            os.environ.setdefault(k, v)
```

---

## 配置后的预期效果

启用云端模型后，AI 模型设置页面将显示：

```
📡 可用模型
├── 🤖 本地 deepseek-r1:7b     [本地] 已选用
├── 🤖 本地 qwen3.5:9b         [本地] 
├── 🤖 本地 llama3.1:8b        [本地] 
├── 🤖 本地 minimax-m2.7:cloud [本地] 
├── ☁️  云端 GPT-4o-mini        [云端] ← 新增
├── ☁️  云端 GPT-4o             [云端] ← 新增
└── 📋 规则引擎 (无 AI)        [Fallback]
```

---

## FAQ

**Q: 云端模型收费吗？**
A: OpenAI 按 token 计费，GPT-4o-mini 非常便宜（约 $0.1/1M tokens）。硅基流动有免费额度。

**Q: 云端模型速度如何？**
A: 取决于网络，通常 2-10 秒响应，比本地 CPU 推理快很多。

**Q: 可以同时使用本地+云端吗？**
A: 可以！设置模型优先级链：[本地 qwen3.5:9b → 云端 GPT-4o-mini → 规则引擎]，本地优先，云端兜底。

**Q: minimax-m2.7:cloud 是云端模型吗？**
A: 不是。它是本地运行的模型，"cloud" 只是文件名/标签，不代表云端 API。

**Q: embedding 模型（nomic-embed）做什么用？**
A: 用于向量检索/相似度匹配，当前版本不需要，已主动过滤。
