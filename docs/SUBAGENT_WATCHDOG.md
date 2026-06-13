# Subagent 实时监督机制

> 创建时间：2026-05-07  
> 目的：Main-agent 主动监督子 agent 工作，防止罢工/卡顿（类比实时内存分配机制）

---

## 一、核心设计

类比操作系统的实时内存分配器：
- **被动等待**（旧机制）：主线程 spawn subagent 后等待完成事件，中途不知情况
- **主动监督**（新机制）：主线程定期轮询 subagent 状态，发现异常立即干预

---

## 二、监控指标

| 指标 | 正常 | 异常 |
|------|------|------|
| subagent 状态 | `running` | `stalled` / 无响应 |
| 运行时间 | < 5 分钟 | > 5 分钟无输出 |
| 进度描述 | 有更新 | 描述未变（疑似卡住） |
| Token 消耗 | 合理增长 | 长时间无增长 |

---

## 三、干预策略

### Level 1 — 轻量 nudge（< 5 分钟）
发送-steer 消息，推动 subagent 继续：
```
"继续执行，当前任务尚未完成，请继续写代码不要停止"
```

### Level 2 — 中度干预（5-10 分钟）
发-steer 消息并附上具体引导：
```
"任务超时风险，请立即输出已完成的部分（即使不完整），然后继续"
```

### Level 3 — 重启（> 10 分钟 or 连续 2 次 nudge 无效）
Kill 当前的 subagent，重新 spawn：
- 先 kill：`subagents(action=kill, target="ui-v02")`
- 再 spawn 新的 subagent，任务不变

---

## 四、信任边界

- subagent 运行 < 3 分钟：**不干预**，给足启动时间
- subagent 运行 3-5 分钟：**观察**，等待自然完成
- subagent 运行 > 5 分钟：**发起 Level 1 nudge**
- subagent 运行 > 10 分钟：**Level 3 kill + respawn**

---

## 五、当前活跃 Subagent

```
session_key: agent:main:subagent:08e6096d-2514-41a2-a963-f0accdf8a2fe
label: blueprint-ai-ui-v02
status: running
runtime: ~12s（截至14:26）
```

---

## 六、实时监督 Cron（每3分钟检查一次）

监督 cron job ID：`subagent-watch-001`

- 每 3 分钟检查活跃 subagent
- 如发现运行时间 > 5 分钟，执行 Level 1 nudge
- 如发现运行时间 > 10 分钟，执行 Level 3 kill + respawn

---

_最后更新：2026-05-07 14:26_
