# EMA v1.3.1 状态报告 — NVIDIA API RPM 计数器
**时间:** 2026-05-25 15:00 GMT+8  
**版本:** v1.3.1  
**Git:** main (待提交)

---

## 📊 服务状态

| 服务 | 端口 | 状态 |
|------|------|------|
| EMA API | 6188 | ✅ 正常运行 |
| EMA UI | 6189 | ✅ 正常运行 |
| NVIDIA RPM计数器 | - | ✅ 已实现并启用 |
| 每日监控Cron | 00:05 | ✅ 已配置 |

---

## 🔧 本次交付：NVIDIA API RPM计数器

### 1. 滑动窗口限速（model_registry.py）
| 功能 | 说明 |
|------|------|
| 单用户/单租户 RPM限制 | 40次/分钟 |
| 用户隔离 | 不同用户独立计数 |
| 自动过期 | 滑动窗口60秒，过期自动清理 |
| 峰值追踪 | 全局峰值，每日重置 |
| 超限行为 | 降级到本地模型 |

### 2. API端点

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/models/route` | 路由+返回nvidia_rpm统计数据 |
| GET | `/api/v1/models/nvidia-stats` | 获取当前RPM统计 |
| POST | `/api/v1/models/nvidia-stats/reset` | 重置峰值（每日cron调用） |

### 3. 每日监控Cron
- **时间:** 每日00:05（Asia/Shanghai）
- **行为:** 检查昨日峰值RPM
- **超限时:** 记录警告到memory + 通知刚哥
- **正常时:** 记录正常状态

---

## 🧪 测试验证

```bash
# 健康检查
curl http://127.0.0.1:6188/health
# → {"status": "ok"}

# 路由（含RPM统计）
curl http://127.0.0.1:6188/api/v1/models/route
# → nvidia_rpm: {"peak_rpm": 11, "alert": false, ...}

# RPM限速测试（40次内正常，第41次拒绝）
# → 验证通过
# → 超限时返回本地模型降级

# RPM统计
curl http://127.0.0.1:6188/api/v1/models/nvidia-stats
# → {"data": {"peak_rpm": 11, "limit": 40, ...}}
```

---

## 📋 功能完成度

| 模块 | 完成度 | 备注 |
|------|--------|------|
| NVIDIA RPM计数器 | ✅ 100% | 滑动窗口+用户隔离+峰值追踪 |
| 路由RPM集成 | ✅ 100% | 超限自动降级本地模型 |
| RPM统计端点 | ✅ 100% | GET stats + POST reset |
| 每日监控Cron | ✅ 100% | 00:05自动检查+告警 |
| Boss后台驾驶舱 | 95% | 含mock fallback |
| 模型配置 | 95% | toggle/add/toast全链路 |
| 日志统计 | 90% | 有fallback |
| 租户/预警/报告/建议 | 80% | mock数据，待真实API |
| 主界面聊天 | 90% | 文字回复正常 |

**综合完成度: ~91%** (+1% 新增NVIDIA RPM)

---

## 🔜 下一步

1. **真实数据接入** - 租户/预警/报告/建议接真实API（目前都是mock）
2. **文件上传实测** - DWG/DXF/PDF上传测试（chat界面）
3. **蓝图tour引导** - 引导用户完成首次体验
4. **模型切换功能** - index.html模型选择器实际切换路由
5. **登录页品牌升级** - 适配EMA工程管理主题

---

## 🗂️ 改动文件

```
src/model_registry.py    增加了NVIDIA RPM计数器（~80行）
src/api_server.py         增加了RPM相关端点（~30行）
docs/04-项目进展/         新增本报告
```
