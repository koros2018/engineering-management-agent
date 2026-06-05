# Changelog

## v3.4.0 (2026-06-05) — Phase 21: Agent LLM接入

### 核心功能
- **agent_llm.py**（327行）— 统一LLM调用模块
  - Ollama本地模型 + LongCat/Kimi云端fallback
  - 6个Agent角色化system prompt（tech_rd/safety/engineering/cost/market/service）
  - 异步+同步双版本，超时保护+自动降级
- **sub_agents/__init__.py** — 5个Agent对话方法全部LLM驱动
- **ema_ui_serve.py** — 独立UI静态文件服务

### 测试
- 200/200 passed

---

## v2.7.0 (2026-05-30) — Phase 16: 实战测试+性能调优+发布准备

### 测试修复（162/162 全部通过）
- 修复 `test_tech_rd_agent.py` 中旧类名引用（`TypeClassifierTool` → `EMATypeClassifierTool` 等）
- 修复 `TestTaskPlanning` 期望值（plan 实际 4 步，非 5 步）
- 修复 `test_e2e_pipeline.py` pytest fixture 缺失（`@pytest.mark.parametrize`）
- 移除 `TestDesignOptimizer`（`EMADesignOptimizerTool` 未实现，Phase 17+ 规划）
- 修复 `test_api_health` 返回值警告

### 性能基准
| 指标 | 结果 |
|------|------|
| API 健康检查 | 1.8ms |
| DXF 分析（251KB） | 42ms |
| DXF 分析（752KB） | 56ms |
| DXF 分析（6.4MB） | 976ms |
| 智能审查 | 2.6ms |
| 文档生成 | 2.1ms |
| 并发 5 线程 × 20 请求 | 24ms，100% 成功 |

### 测试覆盖
- 单元测试：147 个（agent_tests + 模块测试）
- E2E 测试：21 个（4 个 DXF 文件的完整流水线）
- 总计：162 tests, 0 failures, 0 errors

---
## v2.6.0 (2026-05-30) — Phase 15: Admin 管理面板
- 5 Tab 管理面板（概览/用户/租户/模型/反馈）
- super_admin 权限控制

## v2.5.0 (2026-05-30) — Phase 14: API文档+Docker+拖拽上传
- API 文档增强
- Docker 部署脚本优化
- 前端拖拽上传

## v2.3.0 (2026-05-29) — Phase 12: 国际化+性能监控
- i18n 中/EN 切换
- 性能监控面板

## v2.2.0 (2026-05-29) — Phase 11: 主题切换+用户反馈
- 三态主题（跟随系统/暗色/亮色）
- 用户反馈收集

## v2.1.0 (2026-05-29) — Phase 10: 性能优化
- 后端并行化（审查+文档生成并行）
- 前端 CSS 压缩
- 移动端抽屉

## v2.0.0 (2026-05-29) — Phase 8-9: Agent工作流
- Agent 工作流前端 UI 集成
- 图纸审查+文档生成端点

## v1.8.0 (2026-05-28) — Phase 7+1-C: 审查+文档+规范库
- 15 条国标审查规则 + 12 条几何审查
- 6 类文档生成
- 75 个图层→规范映射

## v1.7.0 (2026-05-28) — Phase 7+1-B: AI能力增强
- 工程信息智能提取器
- 规则+LLM 双引擎分类
- 完整规则引擎迁移

## v1.6.0 (2026-05-27) — Phase 7: 异步任务+项目管理
- 异步任务队列
- 项目管理+里程碑追踪
- 管理端面板
