import json

# 读取配置
with open('/home/kezhigang/.openclaw/openclaw.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

# 本地已验证可用的 cloud 模型
local_models = [
    {"id": "qwen3.5:cloud", "name": "Qwen 3.5 Cloud (推荐默认)", "contextWindow": 262144, "input": ["text", "image"], "reasoning": True, "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}},
    {"id": "minimax-m2.7:cloud", "name": "MiniMax M2.7 Cloud", "contextWindow": 131072, "input": ["text"], "reasoning": True, "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}},
    {"id": "kimi-k2.5:cloud", "name": "Kimi K2.5 Cloud", "contextWindow": 262144, "input": ["text", "image"], "reasoning": True, "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}},
    {"id": "glm-5:cloud", "name": "GLM-5 Cloud", "contextWindow": 204800, "input": ["text"], "reasoning": True, "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}},
    {"id": "deepseek-v4-pro:cloud", "name": "DeepSeek V4 Pro Cloud", "contextWindow": 1000000, "input": ["text"], "reasoning": True, "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}},
]

# 获取当前模型列表
existing = d.get('models', {}).get('providers', {}).get('ollama', {}).get('models', [])
existing_ids = {m['id'] for m in existing}

# 添加缺失的模型
added = []
for m in local_models:
    if m['id'] not in existing_ids:
        existing.append(m)
        added.append(m['id'])

if added:
    print(f"✅ 新增模型：{', '.join(added)}")

# 移除 gpt-oss:120b-cloud (无 API 授权)
before_count = len(existing)
existing = [m for m in existing if m['id'] != 'gpt-oss:120b-cloud']
removed = before_count - len(existing)
if removed > 0:
    print(f"✅ 移除 gpt-oss:120b-cloud（无 API 授权）")

# 更新
if 'models' not in d:
    d['models'] = {}
if 'providers' not in d['models']:
    d['models']['providers'] = {}
if 'ollama' not in d['models']['providers']:
    d['models']['providers']['ollama'] = {}
d['models']['providers']['ollama']['models'] = existing

# 添加 Ollama 路径配置
if 'plugins' not in d:
    d['plugins'] = {'entries': {}}
if 'ollama' not in d['plugins']['entries']:
    d['plugins']['entries']['ollama'] = {'enabled': True}
d['plugins']['entries']['ollama']['config'] = {
    "paths": {
        "windows": "D:\\ollama-ipex-llm\\ollama.exe",
        "linux": "/usr/local/bin/ollama",
        "darwin": "/usr/local/bin/ollama"
    },
    "autoDetect": True,
    "baseUrl": "http://127.0.0.1:11434",
    "timeout": 120
}

# 备份
import shutil
shutil.copy('/home/kezhigang/.openclaw/openclaw.json', '/home/kezhigang/.openclaw/openclaw.json.bak.20260515_1037')

# 保存
with open('/home/kezhigang/.openclaw/openclaw.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)

print(f"\n📊 总计：{len(existing)} 个模型")
for m in existing:
    print(f"  ✅ {m['id']}")
print("\n📁 备份：openclaw.json.bak.20260515_1037")
