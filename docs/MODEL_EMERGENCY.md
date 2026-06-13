# 应急机制 — 模型切换预案

> 创建时间：2026-05-07  
> 更新：2026-05-07 14:16

---

## 一、当前模型状态

| 模型 ID | 类型 | 状态 |
|--------|------|------|
| `ollama/minimax-m2.7:cloud` | Cloud | ✅ 当前唯一可用 |
| `ollama/qwen3:8b` | 本地 | ❌ Gateway 白名单限制，不可切换 |

当前只有 minimax-m2.7:cloud 可用，无法通过 `session_status model=` 切换到其他模型。

---

## 二、实际可用策略（当前只有 minimax-m2.7:cloud）

### 策略1：Subagent 隔离（推荐）
- 主 session 只做协调、阅读、规划
- 重度任务（写代码、写文档）spawn isolated subagent
- subagent 有独立超时和 failover 机制
- 即使 subagent 超时失败，主 session 不受影响

### 策略2：分块执行
- 大文件分多次读写，每次不超过 500 行
- 长任务拆成多个短步骤
- 避免一次 tool_calls 超过 10 次

### 策略3：避免长等待
- exec 命令设置合理 timeout
- 不用 exec sleep 轮询，用 cron 做定时任务
- 等待子 agent 时用 sessions_yield

### 策略4：减少 token 消耗
- 只读需要的代码段，不要 read 整个大文件
- 回复简洁，不重复已知信息
- 使用 HEARTBEAT_OK 跳过无意义轮询

---

## 三、触发条件

模型在以下情况判定为"无响应/卡顿"：
1. 单次 LLM 请求超过 **120 秒** 无响应
2. 连续 **2 次** 超时
3. 报错 `FailoverError: LLM request timed out`

---

## 四、Subagent 应急执行流程

当主 session 检测到卡顿 or 大任务时，将重度任务 spawn 到 subagent：

```javascript
sessions_spawn({
  context: "isolated",
  mode: "run",
  runtime: "subagent",
  task: "具体任务描述..."
})
```

subagent 失败会自动重试 failover，不影响主 session。

---

## 五、监控与记录

每次模型/策略切换后，在 `memory/YYYY-MM-DD.md` 中记录：
- 触发原因
- 使用的策略（subagent / 分块 / 其他）
- 结果

---

## 六、预防措施

- 长任务（代码编写/文档生成）优先用 `sessions_spawn` 隔离
- 不要在主 session 直接跑大量 token 消耗任务
- 定期检查 `openclaw models list` 确认模型状态

---

_最后更新：2026-05-07 14:16_
