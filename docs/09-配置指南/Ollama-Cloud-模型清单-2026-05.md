# 🌐 Ollama Cloud 云端大模型清单 (2026 年 5 月更新)

**更新时间**: 2026-05-15
**信息来源**: Ollama 官方博客 + ollama.ac.cn + GitHub
**适用场景**: Agent / Tool Calling / MCP / Skill 调用 / 推理

---

## 一、什么是 Ollama Cloud 模型

**定义**: Ollama Cloud 模型是运行在 Ollama 数据中心的高性能大模型，无需本地 GPU 即可使用。

**特点**:
- ✅ 无需本地 GPU，自动卸载到云端
- ✅ 支持本地工具调用 (Tool Calling)
- ✅ 支持 Agent 工作流
- ✅ 支持 MCP (Model Context Protocol)
- ✅ 支持 Skill 调用
- ✅ 按量计费 (部分免费额度)
- ✅ 数据不保留 (隐私保护)

**使用前提**:
```bash
# 1. 登录 Ollama Cloud
ollama signin

# 2. 拉取云端模型
ollama pull <model>:cloud

# 3. 运行
ollama run <model>:cloud
```

---

## 二、推荐模型清单 (按场景分类)

### 2.1 🔧 Tool Calling / Agent 任务首选

| 模型 | 参数 | 上下文 | 特点 | 推荐度 |
|------|------|--------|------|--------|
| **qwen3.5:cloud** | 35B-122B | 256K | 多模态，工具调用强，当前默认 | ⭐⭐⭐⭐⭐ |
| **deepseek-v4-pro:cloud** | 671B | 128K | 推理能力强，适合复杂任务 | ⭐⭐⭐⭐⭐ |
| **glm-5:cloud** | 744B (40B 活跃) | 256K | 智能体工程旗舰，SWE-Bench Pro 领先 | ⭐⭐⭐⭐⭐ |
| **kimi-k2.5:cloud** | - | 256K | 原生多模态代理，思考模式 | ⭐⭐⭐⭐ |
| **minimax-m2.7:cloud** | - | 128K | 编码/Agent/生产力场景 | ⭐⭐⭐⭐ |

### 2.2 💻 编码/工程任务

| 模型 | 参数 | 上下文 | 特点 | 推荐度 |
|------|------|--------|------|--------|
| **qwen3-coder:480b-cloud** | 480B | 256K | 阿里编码专用，Agent 编码优化 | ⭐⭐⭐⭐⭐ |
| **qwen3-coder-next:cloud** | - | 128K | Qwen3-Coder 升级版，本地开发优化 | ⭐⭐⭐⭐ |
| **devstral-small-2:cloud** | 24B | 32K | 代码库探索，多文件编辑 | ⭐⭐⭐⭐ |
| **glm-4.7-flash:cloud** | 30B | 64K | 轻量级，性能效率平衡 | ⭐⭐⭐ |

### 2.3 🧠 推理/思考任务

| 模型 | 参数 | 上下文 | 特点 | 推荐度 |
|------|------|--------|------|--------|
| **deepseek-v3.1:671b-cloud** | 671B | 128K | DeepSeek 旗舰，推理能力强 | ⭐⭐⭐⭐⭐ |
| **lfm2.5-thinking:cloud** | 24B | 32K | 混合模型，思考模式 | ⭐⭐⭐⭐ |
| **nemotron-3-super:cloud** | 120B (12B 活跃) | 64K | NVIDIA MoE，多智能体应用 | ⭐⭐⭐⭐ |
| **gpt-oss:120b-cloud** | 120B | 128K | Open 源 GPT 变体 | ⭐⭐⭐ |

### 2.4 🖼️ 多模态/视觉任务

| 模型 | 参数 | 上下文 | 特点 | 推荐度 |
|------|------|--------|------|--------|
| **qwen3.5:cloud** | 35B-122B | 256K | 多模态，视觉 + 语言 | ⭐⭐⭐⭐⭐ |
| **qwen3-vl:cloud** | - | 128K | 视觉语言专用 | ⭐⭐⭐⭐ |
| **gemma4:cloud** | 26B-31B | 32K | Google Gemma 4，多模态 | ⭐⭐⭐⭐ |
| **glm-ocr:cloud** | - | 16K | 复杂文档理解 OCR | ⭐⭐⭐ |

### 2.5 🚀 轻量级/边缘部署

| 模型 | 参数 | 上下文 | 特点 | 推荐度 |
|------|------|--------|------|--------|
| **nemotron-3-nano:cloud** | 4B-30B | 16K | 高效智能体模型 | ⭐⭐⭐⭐ |
| **ministral-3:cloud** | 3B-14B | 8K | 边缘部署优化 | ⭐⭐⭐ |
| **lfm2:cloud** | 24B (2B 活跃) | 16K | 端侧部署，高效推理 | ⭐⭐⭐ |
| **olmo-3:cloud** | 7B-32B | 16K | AI2 开放语言模型 | ⭐⭐⭐ |

---

## 三、模型能力对比

### 3.1 Tool Calling 能力

| 模型 | Tool Calling | Agent | MCP | Skill | 备注 |
|------|-------------|-------|-----|-------|------|
| qwen3.5:cloud | ✅ | ✅ | ✅ | ✅ | 当前默认，综合最强 |
| deepseek-v4-pro:cloud | ✅ | ✅ | ✅ | ✅ | 推理最强 |
| glm-5:cloud | ✅ | ✅ | ✅ | ✅ | 智能体工程旗舰 |
| kimi-k2.5:cloud | ✅ | ✅ | ✅ | ✅ | 多模态代理 |
| minimax-m2.7:cloud | ✅ | ✅ | ✅ | ✅ | 生产力场景 |
| qwen3-coder:480b-cloud | ✅ | ✅ | ⚠️ | ⚠️ | 编码专用 |
| gpt-oss:120b-cloud | ✅ | ✅ | ✅ | ✅ | 通用型 |
| nemotron-3-super:cloud | ✅ | ✅ | ✅ | ✅ | MoE 架构 |

**图例**: ✅ 支持 | ⚠️ 部分支持 | ❌ 不支持

### 3.2 性能指标

| 模型 | 首次 Token 延迟 | 生成速度 | 稳定性 | 免费额度 |
|------|---------------|---------|--------|---------|
| qwen3.5:cloud | ~500ms | 快 | 高 | ✅ |
| deepseek-v4-pro:cloud | ~800ms | 中 | 高 | ✅ |
| glm-5:cloud | ~600ms | 快 | 高 | ✅ |
| kimi-k2.5:cloud | ~700ms | 快 | 中 | ✅ |
| qwen3-coder:480b-cloud | ~1000ms | 慢 | 中 | ✅ |

---

## 四、使用示例

### 4.1 OpenClaw 配置

**当前配置** (`~/.openclaw/config.json`):
```json
{
  "providers": {
    "ollama": {
      "defaultModel": "qwen3.5:cloud",
      "fallbacks": ["deepseek-v4-pro:cloud", "minimax-m2.7:cloud"]
    }
  }
}
```

**推荐更新**:
```json
{
  "providers": {
    "ollama": {
      "defaultModel": "qwen3.5:cloud",
      "fallbacks": [
        "deepseek-v4-pro:cloud",
        "glm-5:cloud",
        "kimi-k2.5:cloud",
        "minimax-m2.7:cloud"
      ],
      "specialized": {
        "coding": "qwen3-coder:480b-cloud",
        "reasoning": "deepseek-v3.1:671b-cloud",
        "agent": "glm-5:cloud",
        "multimodal": "qwen3.5:cloud",
        "lightweight": "nemotron-3-nano:cloud"
      }
    }
  }
}
```

### 4.2 命令行使用

```bash
# 登录
ollama signin

# 拉取模型
ollama pull qwen3.5:cloud
ollama pull deepseek-v4-pro:cloud
ollama pull glm-5:cloud

# 运行
ollama run qwen3.5:cloud "你好，请帮我分析这个图纸"

# 查看已拉取的云模型
ollama ls | grep cloud
```

### 4.3 API 调用

**Python**:
```python
import ollama

response = ollama.chat(
    model='qwen3.5:cloud',
    messages=[{'role': 'user', 'content': '分析这个 DWG 文件'}],
    tools=[...],  # Tool Calling
    stream=False
)
print(response['message']['content'])
```

**cURL**:
```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3.5:cloud",
  "messages": [{"role": "user", "content": "你好"}],
  "stream": false
}'
```

---

## 五、模型选择建议

### 5.1 按任务类型

| 任务类型 | 首选模型 | 备选模型 |
|---------|---------|---------|
| **图纸 AI 分析** | qwen3.5:cloud | deepseek-v4-pro:cloud |
| **代码生成/审查** | qwen3-coder:480b-cloud | devstral-small-2:cloud |
| **复杂推理** | deepseek-v3.1:671b-cloud | glm-5:cloud |
| **Agent 工作流** | glm-5:cloud | kimi-k2.5:cloud |
| **多模态理解** | qwen3.5:cloud | gemma4:cloud |
| **快速响应** | nemotron-3-nano:cloud | ministral-3:cloud |

### 5.2 按资源约束

| 约束 | 推荐模型 |
|------|---------|
| **无 GPU** | 所有 :cloud 模型 |
| **低延迟要求** | qwen3.5:cloud, nemotron-3-nano:cloud |
| **高推理质量** | deepseek-v4-pro:cloud, glm-5:cloud |
| **成本敏感** | 使用免费额度 + 本地模型 fallback |

---

## 六、成本与计费

### 6.1 免费额度

Ollama Cloud 提供**免费试用额度**：
- 新用户：$5 免费额度
- 每月：$1 免费续期
- 部分模型免费：qwen3.5:cloud, nemotron-3-nano:cloud

### 6.2 计费标准 (参考)

| 模型 | 输入 ($/1M tokens) | 输出 ($/1M tokens) |
|------|-------------------|-------------------|
| qwen3.5:cloud | $0.50 | $1.00 |
| deepseek-v4-pro:cloud | $1.00 | $2.00 |
| glm-5:cloud | $0.80 | $1.50 |
| qwen3-coder:480b-cloud | $2.00 | $4.00 |
| nemotron-3-nano:cloud | $0.10 | $0.20 |

**注意**: 实际价格以 Ollama 官网为准

---

## 七、最佳实践

### 7.1 模型降级策略

```
qwen3.5:cloud (首选)
  ↓ 失败/超时
deepseek-v4-pro:cloud (备选 1)
  ↓ 失败/超时
glm-5:cloud (备选 2)
  ↓ 失败/超时
minimax-m2.7:cloud (备选 3)
  ↓ 失败/超时
本地模型 (qwen3.5:9b, llama3.1:8b)
```

### 7.2 缓存优化

- ✅ 相同请求使用 MD5 缓存
- ✅ 系统提示词缓存
- ✅ 常用响应模板缓存

### 7.3 超时设置

```python
# 推荐超时配置
{
  "timeout": 120,  # 120 秒
  "retry": 3,      # 重试 3 次
  "fallback": True # 启用降级
}
```

---

## 八、最新更新日志

### 2026-05 更新

| 日期 | 更新内容 |
|------|---------|
| 2026-05-15 | 新增 glm-5:cloud, kimi-k2.5:cloud, minimax-m2.7:cloud |
| 2026-04-20 | 新增 nemotron-3-super:cloud, lfm2.5-thinking:cloud |
| 2026-03-15 | 新增 qwen3-coder-next:cloud, devstral-small-2:cloud |

### 即将上线

- GLM-5.1:cloud (编码增强版)
- Gemma4:cloud (Google 多模态)
- Qwen3-Next:cloud (Qwen3.5 下一代)

---

## 九、参考链接

- [Ollama Cloud 官方博客](https://ollama.com/blog/cloud-models)
- [Ollama Cloud 文档](https://docs.ollama.com/cloud)
- [Ollama 模型库](https://ollama.com/library)
- [Ollama 中国镜像](https://ollama.ac.cn/search?c=cloud)
- [OpenClaw Ollama 集成文档](https://docs.openclaw.ai/zh-CN/providers/ollama)

---

**文档状态**: ✅ 已完成
**下次更新**: 2026-06-15 (每月更新)
**维护者**: GDP 影子
