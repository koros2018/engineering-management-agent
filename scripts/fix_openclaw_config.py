import json

# 读取当前配置
with open('/home/kezhigang/.openclaw/openclaw.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

# 1. 移除 plugins.entries.ollama.config 中的无效属性
if 'plugins' in d and 'entries' in d['plugins'] and 'ollama' in d['plugins']['entries']:
    ollama_plugin = d['plugins']['entries']['ollama']
    if 'config' in ollama_plugin:
        # 保留 enabled，移除自定义 config
        del ollama_plugin['config']
        print("✅ 移除 plugins.entries.ollama.config (无效属性)")

# 2. 移除 models.providers.ollama.aliases
if 'models' in d and 'providers' in d['models'] and 'ollama' in d['models']['providers']:
    ollama_models = d['models']['providers']['ollama']
    if 'aliases' in ollama_models:
        del ollama_models['aliases']
        print("✅ 移除 models.providers.ollama.aliases (无效键)")

# 3. 确保模型列表只包含有效字段
valid_keys = {'id', 'name', 'contextWindow', 'input', 'reasoning', 'cost'}
if 'models' in ollama_models:
    for model in ollama_models['models']:
        # 移除任何额外的键
        extra_keys = set(model.keys()) - valid_keys
        for key in extra_keys:
            del model[key]
            print(f"✅ 从 {model['id']} 移除无效键: {key}")

# 4. 备份
import shutil
shutil.copy('/home/kezhigang/.openclaw/openclaw.json', '/home/kezhigang/.openclaw/openclaw.json.bak.fix')

# 5. 保存
with open('/home/kezhigang/.openclaw/openclaw.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)

print("\n📁 配置已修复并保存")
print("📁 备份: openclaw.json.bak.fix")

# 验证
print("\n=== 验证 ===")
print("plugins.entries.ollama:", json.dumps(d.get('plugins', {}).get('entries', {}).get('ollama', {}), indent=2))
print("\nmodels.providers.ollama:", json.dumps(d.get('models', {}).get('providers', {}).get('ollama', {}), indent=2)[:500])
