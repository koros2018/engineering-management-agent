# EMA 每日主动检查报告

**检查时间：** 2026-05-24 09:00 (Asia/Shanghai)  
**执行方式：** cron 触发 | `run_daily_checks()`

---

## 📊 检查结果汇总

| 检查项 | 数量 |
|--------|------|
| 订阅检查 (subscription_checks) | 6 |
| 订阅告警 (subscription_alerts) | **0** ✅ |
| 配额检查 (quota_checks) | 6 |
| 配额告警 (quota_alerts) | **0** ✅ |
| 规范更新 (standard_updates) | 0 |
| 错误 (errors) | **0** ✅ |

> **结论：** 所有检查项正常，无关键告警 🎉

---

## 🏢 租户状态

| 租户 ID | 名称 | 套餐 | 状态 |
|---------|------|------|------|
| tenant_boss | EMA平台管理 | private | active |
| tenant_876bd457cf4a | 测试设计院 | free | active |
| tenant_2b2ef652f43d | wx_d5000b89的个人空间 | free | active |
| tenant_80a4b0000930 | wx_f45b4800的个人空间 | free | active |
| tenant_793df9fb6960 | wx_e69f0d41的个人空间 | free | active |
| tenant_dbe3ed3b5be5 | wx_5be6abf3的个人空间 | free | active |
| tenant_fa62304a7238 | wx_4c9c9bf3的个人空间 | free | active |
| tenant_4108dfa3dd63 | testwx_user的个人空间 | free | active |
| tenant_7c0e744f6eb9 | test01的个人空间 | free | active |
| tenant_9d6c50854a9e | test_tester的个人空间 | free | active |

**共 10 个租户**，均为 active 状态。

---

## 📬 通知消息摘要

系统当前存在 **未读通知**，按租户分布如下：

| 租户 | 未读通知数 | 最新类型 |
|------|-----------|----------|
| t-008 | 15 | subscription_expiring |
| t-pay-001 | 15 | subscription_expiring |
| t-pay-002 | 15 | subscription_expiring |
| t-pay-003 | 15 | subscription_expiring |
| test_tenant | 1 | subscription_expiring |
| test_t | 1 | subscription_expiring |

> ⚠️ **注意：** 大量重复的"✅ 订阅激活成功"通知堆积（每个测试租户 15 条），说明通知去重或幂等机制可能未生效。建议后续清理。

---

## ✅ 关键告警

**无关键告警。**  
- `subscription_expired`: 0  
- `quota_warning`: 0  

---

## 📝 备注与建议

1. **通知堆积问题：** 测试租户（t-008, t-pay-001/002/003）积压大量重复订阅通知，建议清理历史通知或检查幂等逻辑。
2. **免费套餐租户较多：** 10 个租户中 9 个为 free 套餐，无配额预警触发记录。
3. **alerts.json 为空：** 告警模块当前无历史告警记录，检查逻辑正常。

---

*报告生成：GDP影子 | EMA cron job*