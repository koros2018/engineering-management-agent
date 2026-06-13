#!/usr/bin/env python3
"""
修复 Control UI 模型列表显示问题
确保 deepseek-v4-pro:cloud 等模型在 Control UI 中可见
"""

import json
import os

# 读取配置
config_path = '/home/kezhigang/.openclaw/openclaw.json'
with open(config_path, 'r', encoding='utf-8') as f:
    d = json.load(f)

# 1. 检查 models 结构
print("=== 当前 models 结构 ===")
if 'models' in d:
    print(f"  models 存在")
    if 'providers' in d['models']:
        print(f"  providers 存在")
        if 'ollama' in d['models']['providers']:
            print(f"  ollama 存在")
            ollama = d['models']['providers']['ollama']
            if 'models' in ollama:
                print(f"  models 列表存在：{len(ollama['models'])} 个")
                for m in ollama['models']:
                    print(f"    - {m['id']}")
            else:
                print("  ❌ models 列表不存在！")
        else:
            print("  ❌ ollama provider 不存在！")
    else:
        print("  ❌ providers 不存在！")
else:
    print("  ❌ models 不存在！")

# 2. 检查是否有 modelAliases
print("\n=== 检查 modelAliases ===")
if 'modelAliases' in d:
    print(f"  modelAliases 存在：{d['modelAliases']}")
else:
    print("  modelAliases 不存在")

# 3. 检查 defaultModels
print("\n=== 检查 defaultModels ===")
if 'defaultModels' in d:
    print(f"  defaultModels 存在：{d['defaultModels']}")
else:
    print("  defaultModels 不存在")

# 4. 确保 ollama provider 完整
ollama = d.get('models', {}).get('providers', {}).get('ollama', {})
if not ollama:
    d['models']['providers']['ollama'] = {
        "models": [],
        "aliases": {}
    }
    print("\n✅ 创建 ollama provider 结构")

# 5. 添加 alias 确保 Control UI 能找到
if 'aliases' not in d['models']['providers']['ollama']:
    d['models']['providers']['ollama']['aliases'] = {}

# 为 deepseek-v4-pro:cloud 添加短别名
d['models']['providers']['ollama']['aliases']['deepseek-v4'] = 'deepseek-v4-pro:cloud'
d['models']['providers']['ollama']['aliases']['deepseek'] = 'deepseek-v4-pro:cloud'
d['models']['providers']['ollama']['aliases']['glm5'] = 'glm-5:cloud'
d['models']['providers']['ollama']['aliases']['kimi'] = 'kimi-k2.5:cloud'

print("\n✅ 添加模型别名")

# 6. 保存
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(d, f, indent=2, ensure_ascii=False)

print(f"\n📁 配置已保存：{config_path}")
print("\n=== 下一步 ===")
print("请重启 OpenClaw 后，在 Control UI 中检查模型列表")
print("如果 deepseek-v4-pro:cloud 仍不可见，请检查：")
print("  1. OpenClaw 重启后是否正确加载了配置")
print("  2. Control UI 是否有独立的模型配置缓存")
print("  3. 查看 OpenClaw 日志确认模型加载情况")
