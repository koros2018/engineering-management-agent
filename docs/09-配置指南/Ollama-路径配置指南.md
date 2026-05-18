# 🔧 Ollama 路径配置指南

**版本**: v1.0
**更新时间**: 2026-05-15
**适用平台**: Windows (IPEX) + Ubuntu (WSL2)

---

## 一、问题背景

**问题**: AI 模型功能模块中 CLI 终端操作失败

**根本原因**: Ollama 可执行文件路径配置错误

| 平台 | 错误路径 | 正确路径 |
|------|---------|---------|
| Windows IPEX | `D:\ollama-ipex-llm\bin\ollama.exe` | `D:\ollama-ipex-llm\ollama.exe` |
| Ubuntu | - | `/usr/local/bin/ollama` |

---

## 二、配置方法

### 2.1 OpenClaw 配置 (主配置)

**文件位置**: `~/.openclaw/openclaw.json`

**配置项**:
```json
{
  "plugins": {
    "entries": {
      "ollama": {
        "enabled": true,
        "config": {
          "paths": {
            "windows": "D:\\ollama-ipex-llm\\ollama.exe",
            "linux": "/usr/local/bin/ollama",
            "darwin": "/usr/local/bin/ollama"
          },
          "autoDetect": true,
          "fallback": [
            "/usr/local/bin/ollama",
            "/usr/bin/ollama",
            "~/.local/bin/ollama",
            "ollama"
          ]
        }
      }
    }
  }
}
```

### 2.2 环境变量配置 (可选)

**Windows**:
```powershell
# PowerShell (用户级别)
[Environment]::SetEnvironmentVariable("OLLAMA_PATH", "D:\ollama-ipex-llm\ollama.exe", "User")

# 或系统级别
[Environment]::SetEnvironmentVariable("OLLAMA_PATH", "D:\ollama-ipex-llm\ollama.exe", "Machine")
```

**Ubuntu/WSL2**:
```bash
# ~/.bashrc 或 ~/.zshrc
export OLLAMA_PATH="/usr/local/bin/ollama"

# 或者添加到 PATH
export PATH="$PATH:/usr/local/bin"
```

---

## 三、自动检测逻辑

### 3.1 检测顺序

```
1. 环境变量 OLLAMA_PATH
2. 配置文件 ~/.openclaw/openclaw.json
3. 默认路径搜索:
   - /usr/local/bin/ollama (Linux/macOS)
   - /usr/bin/ollama (Linux)
   - ~/.local/bin/ollama (Linux)
   - D:\ollama-ipex-llm\ollama.exe (Windows)
   - C:\Program Files\Ollama\ollama.exe (Windows)
4. PATH 环境变量中的 ollama
```

### 3.2 平台检测

```python
import platform
import os
from pathlib import Path

def get_ollama_path():
    # 1. 环境变量优先
    if os.getenv("OLLAMA_PATH"):
        return os.getenv("OLLAMA_PATH")
    
    # 2. 平台特定路径
    system = platform.system()
    
    if system == "Windows":
        paths = [
            r"D:\ollama-ipex-llm\ollama.exe",
            r"C:\Program Files\Ollama\ollama.exe",
            r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe",
        ]
    elif system == "Darwin":  # macOS
        paths = [
            "/usr/local/bin/ollama",
            "/opt/homebrew/bin/ollama",
        ]
    else:  # Linux/WSL2
        paths = [
            "/usr/local/bin/ollama",
            "/usr/bin/ollama",
            os.path.expanduser("~/.local/bin/ollama"),
        ]
    
    # 3. 搜索第一个存在的路径
    for path in paths:
        if Path(path).exists():
            return path
    
    # 4. 回退到 PATH 中的 ollama
    return "ollama"  # 依赖系统 PATH
```

---

## 四、用户自定义配置

### 4.1 创建个人配置文件

**文件**: `~/.openclaw/ollama-config.json`

```json
{
  "ollama": {
    "enabled": true,
    "paths": {
      "windows": "D:\\ollama-ipex-llm\\ollama.exe",
      "linux": "/usr/local/bin/ollama",
      "darwin": "/opt/homebrew/bin/ollama"
    },
    "baseUrl": "http://127.0.0.1:11434",
    "timeout": 120,
    "retry": 3,
    "models": {
      "default": "qwen3.5:cloud",
      "fallbacks": [
        "deepseek-v4-pro:cloud",
        "kimi-k2.5:cloud",
        "minimax-m2.7:cloud"
      ],
      "specialized": {
        "coding": "qwen3-coder:480b-cloud",
        "reasoning": "deepseek-v3.1:671b-cloud",
        "agent": "glm-5:cloud",
        "multimodal": "qwen3.5:cloud"
      }
    }
  }
}
```

### 4.2 UI 配置界面 (建议)

在 OpenClaw 控制 UI 中添加设置页面:

```
设置 → AI 模型 → Ollama 配置

[ ] 启用自动检测
[ ] 使用自定义路径

自定义路径:
  Windows: [ D:\ollama-ipex-llm\ollama.exe ]
  Linux:   [ /usr/local/bin/ollama       ]
  macOS:   [ /opt/homebrew/bin/ollama    ]

API 地址：[ http://127.0.0.1:11434     ]
超时时间：[ 120 ] 秒
重试次数：[ 3   ] 次

[保存] [测试连接] [重置]
```

---

## 五、验证测试

### 5.1 路径验证

```bash
# Ubuntu/WSL2
which ollama
# 输出：/usr/local/bin/ollama

ollama --version
# 输出：ollama version is 0.21.2

# Windows PowerShell
Get-Command ollama | Select-Object -ExpandProperty Source
# 输出：D:\ollama-ipex-llm\ollama.exe

ollama --version
# 输出：ollama version is 0.21.2
```

### 5.2 服务验证

```bash
# 检查服务是否运行
ps aux | grep ollama

# 检查 API 是否响应
curl http://localhost:11434/api/version
# 输出：{"version":"0.21.2"}

# 测试模型列表
ollama list
```

### 5.3 模型测试

```bash
# 测试云端模型
ollama run qwen3.5:cloud "你好"
ollama run kimi-k2.5:cloud "你好"
ollama run minimax-m2.7:cloud "你好"

# 测试本地模型
ollama run qwen3.5:9b "你好"
ollama run deepseek-r1:7b "你好"
```

---

## 六、故障排查

### 6.1 CLI 执行失败

**错误**: `ollama: command not found`

**解决**:
```bash
# 1. 检查 PATH
echo $PATH | grep ollama

# 2. 创建符号链接 (Linux)
sudo ln -s /usr/local/bin/ollama /usr/bin/ollama

# 3. 或使用完整路径
/usr/local/bin/ollama list
```

### 6.2 服务无法启动

**错误**: `listen tcp 127.0.0.1:11434: bind: address already in use`

**解决**:
```bash
# 1. 查找占用端口的进程
lsof -i :11434

# 2. 停止旧进程
kill <PID>

# 3. 重启服务
ollama serve
```

### 6.3 云端模型拉取失败

**错误**: `dial tcp: network is unreachable`

**解决**:
```bash
# 1. 检查网络连接
ping registry.ollama.ai

# 2. 检查 IPv6/IPv4
curl -4 https://ollama.com

# 3. 使用代理 (如果需要)
export HTTP_PROXY="http://proxy:port"
export HTTPS_PROXY="http://proxy:port"
ollama pull glm-5:cloud
```

---

## 七、最佳实践

### 7.1 路径配置建议

1. **优先使用环境变量**: 便于跨平台管理
2. **配置文件备份**: `~/.openclaw/ollama-config.json.bak`
3. **自动检测 + 手动覆盖**: 默认自动，允许用户自定义

### 7.2 多平台同步

```json
{
  "ollama": {
    "sync": {
      "enabled": true,
      "platforms": ["windows", "linux"],
      "configFile": "~/.openclaw/ollama-config.json"
    }
  }
}
```

### 7.3 定期更新

```bash
# 每月检查更新
ollama --version

# 更新 Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# 更新 Ollama (Windows)
# 下载最新安装包运行
```

---

## 八、参考链接

- [Ollama 官方文档](https://docs.ollama.com)
- [Ollama Cloud](https://ollama.com/cloud)
- [OpenClaw Ollama 集成](https://docs.openclaw.ai/zh-CN/providers/ollama)

---

**配置状态**: ✅ 已完成
**下次审查**: 2026-06-15
