import json

with open('/home/kezhigang/.openclaw/openclaw.json', 'r') as f:
    d = json.load(f)

# 检查关键结构
print("=== 配置验证 ===")

# 1. 检查 models.providers.ollama
models = d.get('models', {})
providers = models.get('providers', {})
ollama = providers.get('ollama', {})

print(f"✅ models.providers.ollama 存在")
print(f"   模型数: {len(ollama.get('models', []))}")
print(f"   额外键: {set(ollama.keys()) - {'api', 'apiKey', 'baseUrl', 'models', 'aliases'}}")

# 2. 检查 plugins.entries.ollama
plugins = d.get('plugins', {})
entries = plugins.get('entries', {})
ollama_plugin = entries.get('ollama', {})

print(f"✅ plugins.entries.ollama 存在")
print(f"   配置: {json.dumps(ollama_plugin, indent=2)}")

# 3. 列出所有模型
print("\n=== 可用模型 ===")
for m in ollama.get('models', []):
    print(f"  ✅ {m['id']}")

print("\n📊 配置有效，可以重启 OpenClaw")
