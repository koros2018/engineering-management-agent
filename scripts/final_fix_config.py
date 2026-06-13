import json
import shutil

# 读取当前配置
with open('/home/kezhigang/.openclaw/openclaw.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

# 获取 ollama 模型配置
ollama = d['models']['providers']['ollama']

# 1. 移除所有无效键
valid_ollama_keys = {'api', 'apiKey', 'baseUrl', 'models'}
for key in list(ollama.keys()):
    if key not in valid_ollama_keys:
        del ollama[key]
        print(f"✅ 移除无效键: {key}")

# 2. 确保模型字段有效
valid_model_keys = {'id', 'name', 'contextWindow', 'input', 'reasoning', 'cost'}
for model in ollama['models']:
    for key in list(model.keys()):
        if key not in valid_model_keys:
            del model[key]
            print(f"✅ 从 {model['id']} 移除无效键: {key}")

# 3. 确保插件配置干净
if 'plugins' in d and 'entries' in d['plugins'] and 'ollama' in d['plugins']['entries']:
    ollama_plugin = d['plugins']['entries']['ollama']
    # 只保留 enabled
    d['plugins']['entries']['ollama'] = {"enabled": ollama_plugin.get('enabled', True)}
    print("✅ 清理 ollama 插件配置")

# 4. 备份
shutil.copy('/home/kezhigang/.openclaw/openclaw.json', '/home/kezhigang/.openclaw/openclaw.json.bak.final')

# 5. 保存
with open('/home/kezhigang/.openclaw/openclaw.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)

print("\n📁 最终配置已修复")
print("📁 备份: openclaw.json.bak.final")

# 验证
print("\n=== 最终验证 ===")
with open('/home/kezhigang/.openclaw/openclaw.json', 'r') as f:
    final = json.load(f)

ollama_final = final['models']['providers']['ollama']
print(f"模型数: {len(ollama_final['models'])}")
print(f"ollama 键: {list(ollama_final.keys())}")
for m in ollama_final['models']:
    print(f"  ✅ {m['id']}")

print("\n📊 配置完全有效，请重启 OpenClaw")
