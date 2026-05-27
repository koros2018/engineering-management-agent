# Phase 7+1：图纸解析功能EMA自研重构

> 创建时间：2026-05-27
> 优先级：P0（核心能力）
> 负责人：刚哥 + GDP影子

## 📋 变更背景

**现状：** EMA的图纸解析功能完全依赖blueprint-ai项目的`blueprint_parser`模块，通过`sys.path.insert`硬编码路径引用。

**问题：**
1. **架构耦合** — EMA无法独立部署，必须依赖blueprint-ai项目目录存在
2. **能力受限** — blueprint-ai是独立项目，EMA无法针对工程管理场景优化解析逻辑
3. **AI能力弱** — 当前解析是纯规则引擎，缺乏LLM驱动的语义理解
4. **维护困难** — 两个项目同步困难，bug修复和功能迭代互相阻塞

**目标：** 将图纸解析能力从blueprint-ai迁移到EMA项目内，作为TechRdAgent（技术研发中心）的核心能力，并升级为AI增强型解析。

## 🔍 需求调研

### blueprint-ai现有能力盘点

| 模块 | 功能 | 行数 | 迁移优先级 |
|------|------|------|-----------|
| `core.py` | 统一解析入口（PDF/DWG/DXF路由） | ~150 | P0 |
| `pdf_parser.py` | PDF文本提取+OCR | ~200 | P0 |
| `dxf_parser.py` | DXF解析（ezdxf） | ~180 | P0 |
| `dwg_extractor.py` | DWG二进制字符串提取 | ~250 | P0 |
| `inference.py` | 图层语义推理+图纸类型识别 | ~300 | P1 |
| `documents.py` | 5类工程文档生成 | ~400 | P1 |
| `review.py` | 智能审查（国标规则引擎） | ~350 | P1 |
| `dxf_editor.py` | DXF编辑（12项操作） | ~300 | P2 |
| `dxf_geometry.py` | 几何计算 | ~200 | P2 |
| `layout_analyzer.py` | 布局分析 | ~150 | P2 |
| `knowledge_base.py` | 知识库 | ~250 | P2 |
| `vector_search.py` | 向量搜索 | ~180 | P2 |
| `llm_integration.py` | LLM集成 | ~200 | P1 |
| `specs.py` | 国标规范库 | ~500 | P1 |
| `export.py` | 数据导出 | ~150 | P3 |
| `version_compare.py` | 版本对比 | ~200 | P3 |
| `budget.py` | 预算造价 | ~250 | P2 |
| `material_prices.py` | 材料单价 | ~180 | P2 |

### EMA需求分析

**核心场景：**
1. 用户上传DWG/DXF/PDF图纸 → 自动解析图层、文字、几何信息
2. AI识别图纸类型（建筑/结构/机电/给排水/电气/总图）
3. AI提取工程信息（建筑面积、层数、结构形式、设计参数）
4. 智能审查（对照国标规范自动检查）
5. 生成工程文档（设计说明/工程量清单/技术交底）
6. AI改图（自动修正图层/文本/标注）

**与blueprint-ai的差异：**
- EMA需要更强的AI能力（LLM驱动），而非纯规则引擎
- EMA需要与项目管理、成本估算、审查流程深度集成
- EMA需要支持多租户、用户隔离
- EMA需要异步处理大文件

## 🏗️ 架构设计

### 新模块结构

```
src/blueprint/                    # 新模块（EMA自研）
├── __init__.py                   # 包入口
├── types.py                      # 共享数据类型
├── core.py                       # 统一解析器入口
├── parsers/
│   ├── __init__.py
│   ├── pdf_parser.py             # PDF解析（PyMuPDF + OCR）
│   ├── dxf_parser.py             # DXF解析（ezdxf）
│   └── dwg_parser.py             # DWG解析（二进制提取 + libredwg WASM）
├── ai/
│   ├── __init__.py
│   ├── inference.py              # AI图纸语义理解（LLM驱动）
│   ├── classifier.py             # 图纸类型分类
│   └── extractor.py              # 工程信息提取
├── review/
│   ├── __init__.py
│   ├── engine.py                 # 审查引擎
│   ├── rules.py                  # 审查规则
│   └── specs.py                  # 国标规范库
├── editor/
│   ├── __init__.py
│   └── dxf_editor.py             # DXF编辑
├── documents/
│   ├── __init__.py
│   └── generator.py              # 工程文档生成
└── vector/
    ├── __init__.py
    └── search.py                 # 向量搜索（ChromaDB）
```

### 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| PDF解析 | PyMuPDF + tesseract.js | 文本提取 + OCR |
| DXF解析 | ezdxf | 完整DXF读写 |
| DWG解析 | libredwg WASM + 二进制提取 | 双模式降级 |
| AI推理 | LLM (Ollama/云端API) | 图纸语义理解 |
| 向量库 | ChromaDB | 规范检索 + 知识库 |
| 审查引擎 | 规则引擎 + LLM | 国标审查 |
| 异步处理 | ThreadPoolExecutor | 大文件后台解析 |

### 迁移策略

**分阶段迁移，确保平稳过渡：**

- **Phase 7+1-A**：基础解析能力迁移（P0）
  - 迁移pdf_parser.py、dxf_parser.py、dwg_extractor.py
  - 统一入口core.py
  - 保持API兼容，前端无需改动
  
- **Phase 7+1-B**：AI能力增强（P1）
  - 迁移inference.py + llm_integration.py
  - AI图纸类型识别升级
  - 工程信息智能提取
  
- **Phase 7+1-C**：审查+文档生成（P1）
  - 迁移review.py + specs.py
  - 迁移documents.py
  
- **Phase 7+1-D**：高级功能（P2）
  - DXF编辑、布局分析、预算造价
  - 版本对比、数据导出

## 📝 实施计划

### Phase 7+1-A：基础解析迁移（预估2-3天）
1. 创建`src/blueprint/`目录结构
2. 迁移`types.py`（数据类型定义）
3. 迁移`pdf_parser.py`（PDF解析）
4. 迁移`dxf_parser.py`（DXF解析）
5. 迁移`dwg_extractor.py`（DWG解析）
6. 重写`core.py`（统一入口）
7. 更新`api_server.py`中的import路径
8. 测试验证：上传DWG/DXF/PDF → 解析结果一致

### Phase 7+1-B：AI能力增强（预估2-3天）
9. 迁移`inference.py`（图层语义推理）
10. 迁移`llm_integration.py`（LLM集成）
11. 新增`ai/classifier.py`（AI图纸分类）
12. 新增`ai/extractor.py`（工程信息提取）
13. 测试验证：AI识别准确率 > 90%

### Phase 7+1-C：审查+文档（预估2-3天）
14. 迁移`review.py` + `specs.py`
15. 迁移`documents.py`
16. 集成到EMA工作流
17. 测试验证：审查规则命中、文档生成

### Phase 7+1-D：高级功能（预估3-5天）
18. DXF编辑、布局分析
19. 预算造价、材料单价
20. 版本对比、数据导出
21. 知识库、向量搜索

## ⚠️ 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 迁移期间服务中断 | 高 | 分阶段迁移，每阶段独立测试 |
| DWG解析兼容性 | 中 | 保留libredwg WASM + 二进制提取双模式 |
| AI推理准确率不足 | 中 | LLM + 规则引擎混合，逐步优化 |
| 性能下降 | 低 | 异步处理 + 缓存 + 线程池 |
| 代码量激增 | 低 | 模块化设计，按需加载 |

## ✅ 验收标准

- [ ] DWG/DXF/PDF解析结果与blueprint-ai一致
- [ ] AI图纸类型识别准确率 > 90%
- [ ] 智能审查规则命中率 > 80%
- [ ] 文档生成功能正常
- [ ] 上传→分析→审查→文档 全流程端到端验证
- [ ] 性能不低于blueprint-ai（解析时间差异 < 20%）
- [ ] 所有单元测试通过
