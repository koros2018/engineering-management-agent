# 全局隐患扫描报告

> **日期：** 2026-06-02
> **范围：** engineering-management-agent 项目全量文件 + 跨项目扫描
> **方法：** 基于本次 Bug 复盘，逐类排查同类隐患

---

## 扫描结果汇总

| 类别 | 发现 | 状态 |
|------|------|------|
| HTML/JS 语法完整性 | 0 个新问题 | ✅ 全部通过 |
| 文件截断 | 0 个新问题 | ✅ 无截断 |
| API 地址硬编码 | 3 处（已修复） | ✅ 动态适配 |
| Python 循环导入 | 0 个新问题 | ✅ 已修复 |
| data/*.json 完整性 | 0 个损坏 | ✅ 全部完整 |
| 跨项目隐患 | 0 个新问题 | ✅ 无扩散 |

---

## 详细扫描结果

### 1. HTML/JS 语法完整性

**扫描方法：** 提取所有 `<script>` 标签内容，用 `node --check` 验证语法

| 文件 | 结果 |
|------|------|
| ui/admin.html | ✅ 4 个 script 标签全部通过 |
| ui/index.html | ✅ 4 个 script 标签全部通过 |
| ui/index_debug.html | ✅ 4 个 script 标签全部通过 |
| ui/login.html | ✅ 通过 |
| ui/test_blank.html | ✅ 通过 |
| ui/test_debug_vue.html | ✅ 通过 |
| ui/test_minimal.html | ✅ 通过 |

### 2. 文件截断检查

**扫描方法：** `grep -rn "…" *.html`

**结果：** ✅ 无截断标记

### 3. API 地址硬编码

**扫描方法：** `grep -rn "localhost:6188" ui/*.html src/*.py`

| 文件 | 行 | 内容 | 状态 |
|------|-----|------|------|
| ui/login.html | 280 | `window.location.protocol === 'https:' ? '' : 'http://localhost:6188'` | ✅ 动态适配 |
| ui/admin.html | 597 | `window.location.protocol === 'https:' ? '' : 'http://localhost:6188'` | ✅ 动态适配 |
| ui/index.html | 1501 | `window.location.protocol === 'https:' ? '' : 'http://localhost:6188'` | ✅ 动态适配 |
| src/api_server.py | 244-249 | CORS allow_origins 配置 | ✅ 正常（CORS 白名单） |

### 4. Python 循环导入

**扫描方法：** 构建模块依赖图，检测双向依赖

**模块依赖图：**
```
main → api_server
payment → notifications
payment_sdk → payment
projects → notifications
security → auth_extended
specs_updater → notifications
```

**结果：** ✅ 无循环导入

**已修复的历史问题：**
- `auth/__init__.py` ↔ `auth_extended.py`：通过添加 `_lj`/`_sj` 别名修复
- `api_server.py` 模块级 `from auth import`：通过延迟导入修复

### 5. data/*.json 完整性

**扫描方法：** `json.load()` 验证所有 JSON 文件

**结果：** ✅ 23 个 JSON 文件全部完整

### 6. 跨项目扫描

**扫描范围：** `/mnt/d/OpenClawDataworkspace/Projects/` 下所有项目

**结果：** ✅ 无跨项目隐患扩散

---

## 遗留风险点

| # | 风险 | 位置 | 建议 |
|---|------|------|------|
| 1 | CORS 白名单硬编码 | `api_server.py:244-249` | 改为环境变量注入 |
| 2 | 编辑工具截断文件 | OpenClaw 工具层 | 需要工具层面修复 |
| 3 | 缺乏 CI/CD | 项目整体 | 引入自动化检查 |

---

## 结论

经过全量扫描，**当前项目无新增同类隐患**。所有已发现的问题均已修复，相关 Skill 已建立，预防机制已到位。
