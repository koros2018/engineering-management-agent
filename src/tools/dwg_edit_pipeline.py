"""
dwg_edit_pipeline.py — EMA DWG 原地编辑管线 (LibreDWG + ezdxf)

架构:
  DWG → [LibreDWG WASM] → DXF → [ezdxf 编辑] → 编辑后DXF
  可选: DXF → [libredwg dxf2dwg CLI] → 编辑后DWG

已有能力 (继承 blueprint-ai):
  - DWG→DXF: LibreDwg WASM (LibreDwg.create().dwg_write_dxf)
  - DXF 编辑: dxf_editor.py (12项操作: 图层/文本/块属性/标注/实体)

新增能力:
  - 统一管线: 一站式 DWG→编辑→输出
  - DXF→DWG: 调用本机 libredwg dxf2dwg (如果已安装)
  - 回退: 无 libredwg CLI 时输出 DXF
"""

import json
import os
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any


class DwgEditPipeline:
    """DWG 原地编辑统一管线"""

    def __init__(self, api_base_dir: Path = None):
        self.base_dir = api_base_dir or Path(__file__).parent
        self._has_libredwg_cli = None

    @property
    def has_libredwg_cli(self) -> bool:
        """检查是否安装了 libredwg 命令行工具"""
        if self._has_libredwg_cli is None:
            self._has_libredwg_cli = shutil.which("dwgread") is not None and shutil.which("dxf2dwg") is not None
        return self._has_libredwg_cli

    def dwg_to_dxf(self, dwg_path: str) -> str:
        """
        DWG → DXF 转换

        优先使用 libreDWG CLI（更快），回退到 WASM（已有蓝图AI能力）
        """
        if self.has_libredwg_cli:
            dxf_path = dwg_path.rsplit(".", 1)[0] + "_converted.dxf"
            result = subprocess.run(
                ["dwgread", "-O", "DXF", "-o", dxf_path, dwg_path],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                return dxf_path
            raise RuntimeError(f"dwgread转换失败: {result.stderr[:200]}")

        # 回退: 蓝图AI WASM 方式
        import js
        buffer = Path(dwg_path).read_bytes()
        lib = js.LibreDwg.create()
        dxf_data = lib.dwg_write_dxf(buffer)
        if not dxf_data:
            raise RuntimeError("WASM DWG→DXF转换失败")

        dxf_path = dwg_path.rsplit(".", 1)[0] + "_converted.dxf"
        Path(dxf_path).write_text(dxf_data)
        return dxf_path

    def edit_dwg(
        self,
        dwg_path: str,
        operations: List[Dict[str, Any]],
        output_dwg: bool = True,
    ) -> Dict[str, Any]:
        """
        DWG 文件编辑主入口

        Args:
            dwg_path: 原始 DWG 文件路径
            operations: 编辑操作列表
                [
                    {"action": "add_layer", "params": {"name": "A-NEW-TEXT", "color": 7}},
                    {"action": "set_layer_property", "params": {"layer": "A-WALL", "color": 1}},
                    {"action": "delete_layer", "params": {"name": "A-OBSOLETE"}},
                    {"action": "add_text", "params": {"layer": "0", "text": "备注", "x": 10, "y": 20}},
                    {"action": "edit_text", "params": {"handle": "xxx", "new_text": "修改后"}},
                    {"action": "edit_block_attribute", "params": {"handle": "xxx", "tag": "TAG1", "value": "新值"}},
                    {"action": "move_entity", "params": {"handle": "xxx", "dx": 100, "dy": 200}},
                    {"action": "copy_entity", "params": {"handle": "xxx", "dx": 500, "dy": 0}},
                    {"action": "delete_entity", "params": {"handle": "xxx"}},
                    {"action": "set_color", "params": {"handle": "xxx", "color": 3}},
                    {"action": "set_linetype", "params": {"handle": "xxx", "linetype": "DASHED"}},
                    {"action": "edit_dimension", "params": {"handle": "xxx", "text": "新标注"}},
                ]
            output_dwg: True=输出DWG, False=输出DXF

        Returns:
            {"success": bool, "output_path": str, "format": "dwg"|"dxf", "operations_applied": int, "errors": [...], ...}
        """
        result = {
            "success": False,
            "output_path": "",
            "format": "dxf",
            "operations_applied": 0,
            "errors": [],
            "warnings": [],
        }

        if not os.path.exists(dwg_path):
            result["errors"].append(f"文件不存在: {dwg_path}")
            return result

        # 验证操作
        valid_actions = {
            "add_layer", "set_layer_property", "delete_layer",
            "edit_text", "edit_block_attribute", "replace_block_reference",
            "move_entity", "copy_entity", "delete_entity",
            "edit_dimension", "set_color", "set_linetype", "add_text",
        }
        for op in operations:
            if op.get("action") not in valid_actions:
                result["warnings"].append(f"未知操作: {op.get('action')}")

        try:
            import ezdxf
            from ezdxf import recover

            # Step 1: DWG → DXF（如果需要）
            ext = Path(dwg_path).suffix.lower()
            if ext == ".dwg":
                dxf_path = self.dwg_to_dxf(dwg_path)
                result["warnings"].append("DWG已转换为DXF进行编辑")
            else:
                dxf_path = dwg_path

            # Step 2: 读取 DXF + 编辑
            try:
                doc = ezdxf.readfile(dxf_path)
            except Exception:
                # 尝试恢复损坏文件
                doc, auditor = recover.readfile(dxf_path)
                result["warnings"].append(f"DXF文件已修复 (auditor errors: {len(auditor.errors)})")

            msp = doc.modelspace()

            applied = 0
            for op in operations:
                action = op["action"]
                params = op.get("params", {})

                try:
                    if action == "add_layer":
                        doc.layers.add(
                            name=params["name"],
                            color=params.get("color", 7),
                            linetype=params.get("linetype", "CONTINUOUS"),
                        )
                        applied += 1

                    elif action == "set_layer_property":
                        layer = doc.layers.get(params["layer"])
                        if layer:
                            if "color" in params:
                                layer.color = params["color"]
                            if "linetype" in params:
                                layer.dxf.linetype = params["linetype"]
                            if "on" in params:
                                layer.on = params["on"]
                            if "lock" in params:
                                layer.lock = params["lock"]
                            applied += 1
                        else:
                            result["warnings"].append(f"图层不存在: {params['layer']}")

                    elif action == "delete_layer":
                        layer = doc.layers.get(params["name"])
                        if layer:
                            # 只关闭图层（安全），不真删除
                            layer.off()
                            applied += 1

                    elif action == "add_text":
                        text = msp.add_text(
                            params["text"],
                            dxfattribs={
                                "layer": params.get("layer", "0"),
                                "height": params.get("height", 2.5),
                            },
                        )
                        text.set_pos((params.get("x", 0), params.get("y", 0)))
                        applied += 1

                    elif action == "edit_text":
                        handle = params.get("handle")
                        if handle:
                            entity = doc.entitydb.get(handle)
                            if entity and entity.dxftype() == "TEXT":
                                entity.dxf.text = params["new_text"]
                                applied += 1

                    elif action == "edit_block_attribute":
                        handle = params.get("handle")
                        tag = params.get("tag")
                        if handle:
                            entity = doc.entitydb.get(handle)
                            if entity and entity.dxftype() == "INSERT":
                                for attrib in entity.attribs:
                                    if attrib.dxf.tag == tag:
                                        attrib.dxf.text = params.get("value", "")
                                        applied += 1
                                        break

                    elif action == "move_entity":
                        handle = params.get("handle")
                        dx, dy = params.get("dx", 0), params.get("dy", 0)
                        if handle:
                            entity = doc.entitydb.get(handle)
                            if entity:
                                current = entity.dxf.insert if hasattr(entity.dxf, "insert") else None
                                if current:
                                    entity.dxf.insert = (current[0] + dx, current[1] + dy)
                                    applied += 1

                    elif action == "copy_entity":
                        handle = params.get("handle")
                        dx, dy = params.get("dx", 0), params.get("dy", 0)
                        if handle:
                            entity = doc.entitydb.get(handle)
                            if entity:
                                new_entity = entity.copy()
                                if hasattr(new_entity.dxf, "insert"):
                                    current = new_entity.dxf.insert
                                    new_entity.dxf.insert = (current[0] + dx, current[1] + dy)
                                msp.add_entity(new_entity)
                                applied += 1

                    elif action == "delete_entity":
                        handle = params.get("handle")
                        if handle:
                            entity = doc.entitydb.get(handle)
                            if entity:
                                msp.delete_entity(entity)
                                applied += 1

                    elif action == "set_color":
                        handle = params.get("handle")
                        if handle:
                            entity = doc.entitydb.get(handle)
                            if entity:
                                entity.dxf.color = params.get("color", 7)
                                applied += 1

                    elif action == "set_linetype":
                        handle = params.get("handle")
                        if handle:
                            entity = doc.entitydb.get(handle)
                            if entity and hasattr(entity.dxf, "linetype"):
                                entity.dxf.linetype = params.get("linetype", "CONTINUOUS")
                                applied += 1

                    elif action == "edit_dimension":
                        handle = params.get("handle")
                        if handle:
                            entity = doc.entitydb.get(handle)
                            if entity and entity.dxftype() in ("DIMENSION", "DIMLINEAR", "DIMALIGNED"):
                                entity.dxf.text = params.get("text", "")
                                applied += 1

                    elif action == "replace_block_reference":
                        handle = params.get("handle")
                        new_name = params.get("new_block_name")
                        if handle and new_name:
                            entity = doc.entitydb.get(handle)
                            if entity and entity.dxftype() == "INSERT":
                                entity.dxf.name = new_name
                                applied += 1

                except Exception as e:
                    result["warnings"].append(f"操作 {action} 失败: {str(e)[:100]}")

            result["operations_applied"] = applied

            # Step 3: 保存
            base_name = Path(dwg_path).stem
            output_dir = Path(dwg_path).parent

            if output_dwg and self.has_libredwg_cli:
                # DXF → DWG（需要 libredwg CLI）
                tmp_dxf = output_dir / f"{base_name}_tmp.dxf"
                doc.saveas(str(tmp_dxf))
                output_dwg_path = str(output_dir / f"edited_{base_name}.dwg")
                sub_run = subprocess.run(
                    ["dxf2dwg", str(tmp_dxf), "-o", output_dwg_path],
                    capture_output=True, text=True, timeout=30
                )
                tmp_dxf.unlink(missing_ok=True)

                if sub_run.returncode == 0:
                    result["output_path"] = output_dwg_path
                    result["format"] = "dwg"
                else:
                    result["warnings"].append(f"dxf2dwg失败，输出DXF: {sub_run.stderr[:100]}")
                    output_dxf_path = str(output_dir / f"edited_{base_name}.dxf")
                    doc.saveas(output_dxf_path)
                    result["output_path"] = output_dxf_path

            else:
                # 直接输出 DXF
                output_dxf_path = str(output_dir / f"edited_{base_name}.dxf")
                doc.saveas(output_dxf_path)
                result["output_path"] = output_dxf_path
                if output_dwg and not self.has_libredwg_cli:
                    result["warnings"].append("未安装libredwg CLI，输出DXF格式（安装后 sudo apt-get install libredwg-tools 即可输出DWG）")

            result["success"] = applied > 0

        except ImportError as e:
            result["errors"].append(f"缺少依赖: {e}")
        except Exception as e:
            result["errors"].append(f"编辑失败: {str(e)[:200]}")

        return result

    def get_supported_operations(self) -> List[Dict]:
        """获取所有支持的编辑操作"""
        return [
            {"action": "add_layer", "description": "新增图层", "params": ["name", "color", "linetype"]},
            {"action": "set_layer_property", "description": "修改图层属性", "params": ["layer", "color", "linetype", "on", "lock"]},
            {"action": "delete_layer", "description": "删除/关闭图层", "params": ["name"]},
            {"action": "add_text", "description": "新增文本", "params": ["layer", "text", "x", "y", "height"]},
            {"action": "edit_text", "description": "编辑文本内容", "params": ["handle", "new_text"]},
            {"action": "edit_block_attribute", "description": "编辑块属性", "params": ["handle", "tag", "value"]},
            {"action": "replace_block_reference", "description": "替换块引用", "params": ["handle", "new_block_name"]},
            {"action": "move_entity", "description": "移动实体", "params": ["handle", "dx", "dy"]},
            {"action": "copy_entity", "description": "复制实体", "params": ["handle", "dx", "dy"]},
            {"action": "delete_entity", "description": "删除实体", "params": ["handle"]},
            {"action": "set_color", "description": "修改颜色", "params": ["handle", "color"]},
            {"action": "set_linetype", "description": "修改线型", "params": ["handle", "linetype"]},
            {"action": "edit_dimension", "description": "修改标注文字", "params": ["handle", "text"]},
        ]


# 全局单例
_pipeline = DwgEditPipeline()

def get_dwg_edit_pipeline() -> DwgEditPipeline:
    return _pipeline
