# ODA SDK 替代方案研究

## 一、ODA SDK 许可证现状

| 类型 | 费用 | 适用场景 | EMA可行性 |
|------|------|---------|-----------|
| Educational | 免费 | 大学教学/研究（非商业） | ❌ EMA是商业化项目 |
| Non-Commercial | 免费 | 2年内自用 | ⚠️ 可先用2年过渡 |
| Limited Commercial | 付费 | 有限商业用途 | ❌ 需购买 |
| Sustaining/Founding | 付费 | 商业+源码 | ❌ 需购买 |

**关键发现**: ODA提供 **Educational Membership 免费计划** 给高校，但EMA作为商业化项目不适用。

## 二、开源替代方案：LibreDWG + ezdxf 混合架构

### 2.1 技术路径

```
DWG原文件
  ↓ libredwg (dwgread → DXF)
DXF文件
  ↓ ezdxf (Python编辑：图层/文本/块/标注/实体)
编辑后的DXF
  ↓ libredwg (dxf2dwg / dwgwrite)
编辑后的DWG
```

### 2.2 各组件能力

| 能力 | LibreDWG 0.13.4 | ezdxf 1.4.3 | EMA已有 |
|------|----------------|-------------|---------|
| DWG 读取 | ✅ dwgread | ❌ | — |
| DWG→DXF 转换 | ✅ | ❌ | ✅ libredwg WASM |
| DXF→DWG 转换 | ✅ dxf2dwg | ❌ | ❌ |
| DXF 编辑 | ❌ | ✅ 12项操作 | ✅ dxf_editor.py |
| 图层操作 | — | ✅ | ✅ |
| 文本编辑 | — | ✅ | ✅ |
| 块属性编辑 | — | ✅ | ✅ |
| 标注修改 | — | ✅ | ✅ |
| 实体增删 | — | ✅ | ✅ |

### 2.3 安装 LibreDWG

```bash
# 方法1: apt (Ubuntu 22.04+)
sudo apt-get install -y libredwg-tools libredwg-dev

# 方法2: 从源码编译
git clone https://git.savannah.gnu.org/git/libredwg.git
cd libredwg
./autogen.sh
./configure --enable-tools
make
sudo make install

# 验证
dwgread --version
dwgwrite --version
dxf2dwg --version
```

### 2.4 完整 DWG 原地编辑流程

```python
# dwg_edit_pipeline.py - EMA DWG 原地编辑(无需ODA)
import subprocess, tempfile, os
from pathlib import Path

def dwg_edit(dwg_path: str, operations: list) -> str:
    """
    DWG 原地编辑 pipeline (LibreDWG + ezdxf)
    
    operations: [
        {"action": "add_layer", "params": {"name": "A-NEW-TEXT", "color": 7}},
        {"action": "set_layer_property", "params": {"layer": "A-WALL", "color": 1}},
        {"action": "add_text", "params": {"layer": "A-NEW-TEXT", "text": "修改说明", "x": 100, "y": 200}},
    ]
    
    Returns: 编辑后的 DWG 文件路径
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        
        # Step 1: DWG → DXF
        dxf_path = tmp / "temp.dxf"
        result = subprocess.run(
            ["dwgread", "-O", "DXF", "-o", str(dxf_path), dwg_path],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"dwgread failed: {result.stderr}")
        
        # Step 2: ezdxf 编辑
        import ezdxf
        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()
        
        for op in operations:
            action = op["action"]
            params = op.get("params", {})
            
            if action == "add_layer":
                doc.layers.add(name=params["name"], color=params.get("color", 7))
            elif action == "set_layer_property":
                layer = doc.layers.get(params["layer"])
                if layer and "color" in params:
                    layer.color = params["color"]
            elif action == "add_text":
                msp.add_text(
                    params["text"],
                    dxfattribs={"layer": params.get("layer", "0")}
                ).set_pos((params.get("x", 0), params.get("y", 0)))
            # ... 其他操作
        
        # Step 3: 保存 DXF
        edited_dxf = tmp / "edited.dxf"
        doc.saveas(str(edited_dxf))
        
        # Step 4: DXF → DWG
        output_dwg = str(Path(dwg_path).parent / f"edited_{Path(dwg_path).name}")
        result = subprocess.run(
            ["dxf2dwg", str(edited_dxf), "-o", output_dwg],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"dxf2dwg failed: {result.stderr}")
        
        return output_dwg
```

### 2.5 局限性

| 项目 | LibreDWG 限制 | 影响 |
|------|--------------|------|
| DWG 版本 | 最多到 DWG 2018 格式 | 新版 AutoCAD 文件可能失败 |
| 三维实体 | 不支持 ACIS 实体编辑 | 3D 实体需 ODA |
| 动态块 | 不支持动态块参数 | 动态块需 ODA |
| 代理对象 | 忽略/警告 | 自定义对象丢失 |
| DXF→DWG 精度 | 可能存在精度损失 | 基本图层/文本/标注影响不大 |

### 2.6 推荐策略

**短期（当前）**:
- 使用 LibreDWG + ezdxf 混合架构
- 支持所有已有的 12 项 DXF 编辑操作（图层/文本/块/标注/实体）

**中期**:
- ODA Non-Commercial 许可证（免费2年）→ 支持高级 DWG 编辑
- 同时维护 LibreDWG 分支作为开源备选

**长期**:
- 如商业化成功 → 购买 ODA 商业许可证
- 如开源策略 → LibDWG 社区持续改进

## 三、已有能力评估

EMA 现有的 `dxf_editor.py` 已实现 12 项操作：

| 操作 | 函数 | 状态 |
|------|------|------|
| 新增图层 | `add_layer()` | ✅ |
| 修改图层属性 | `set_layer_property()` | ✅ |
| 删除图层 | `delete_layer()` | ✅ |
| 修改文本内容 | `edit_text()` | ✅ |
| 修改块属性 | `edit_block_attribute()` | ✅ |
| 变更块引用 | `replace_block_reference()` | ✅ |
| 移动实体 | `move_entity()` | ✅ |
| 复制实体 | `copy_entity()` | ✅ |
| 删除实体 | `delete_entity()` | ✅ |
| 修改标注 | `edit_dimension()` | ✅ |
| 修改颜色 | `set_color()` | ✅ |
| 修改线型 | `set_linetype()` | ✅ |

**下一步**: 集成 `dwg_edit_pipeline.py` 到 EMA，实现 DWG 原地编辑闭环。

## 四、总结

| 路径 | 成本 | DWG编辑 | 3D支持 | 部署 |
|------|------|---------|--------|------|
| ODA SDK | $0(教育)~$商用 | ✅ 完整 | ✅ | C++/Java/.NET |
| LibreDWG+ezdxf | **$0** (GNU GPL) | ✅ 基本 | ❌ | C+Python |
| ezdxf only | $0 (MIT) | ❌(仅DXF) | ❌ | Python |

**推荐: LibreDWG + ezdxf** — 零成本实现 EMA 所需的 DWG 基本编辑功能。
