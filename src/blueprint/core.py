"""
src/blueprint/core.py - 统一图纸解析器

从 blueprint-ai/core.py 迁移并增强。
自动识别文件类型并路由到对应解析器。
集成AI分类器和工程信息提取器。
"""

import os
from pathlib import Path
from typing import List, Optional

from .types import FileType, EntityInfo, LayerInfo, ParseResult
from .parsers.pdf_parser import PDFParser
from .parsers.dxf_parser import DXFParser
from .parsers.dwg_parser import DWGParser


class BlueprintParser:
    """
    EMA 统一图纸解析器

    支持 PDF / DWG / DXF 格式
    自动识别文件类型，路由到对应解析器
    可选AI增强分析（分类+信息提取）
    """

    EXT_TO_TYPE = {
        '.pdf': FileType.PDF,
        '.dwg': FileType.DWG,
        '.dxf': FileType.DXF,
    }

    def __init__(
        self,
        use_ocr: bool = True,
        ocr_dpi: int = 300,
        enable_ai: bool = True,
        use_llm: bool = True,
    ):
        self.use_ocr = use_ocr
        self.ocr_dpi = ocr_dpi
        self.enable_ai = enable_ai
        self.use_llm = use_llm
        self.pdf_parser = PDFParser(use_ocr=use_ocr, dpi=ocr_dpi)
        self.dxf_parser = DXFParser()
        self.dwg_parser = DWGParser()

    def parse(self, file_path: str) -> ParseResult:
        """解析图纸文件（自动识别类型）"""
        path = Path(file_path)

        if not path.exists():
            return ParseResult(
                success=False, file_path=str(path),
                file_type=FileType.UNKNOWN,
                errors=[f"File not found: {path}"]
            )

        ext = path.suffix.lower()
        file_type = self.EXT_TO_TYPE.get(ext, FileType.UNKNOWN)

        if file_type == FileType.PDF:
            return self.pdf_parser.parse(str(path))
        elif file_type == FileType.DXF:
            return self.dxf_parser.parse(str(path))
        elif file_type == FileType.DWG:
            return self.dwg_parser.parse(str(path))
        else:
            return ParseResult(
                success=False, file_path=str(path),
                file_type=FileType.UNKNOWN,
                errors=[f"Unsupported file type: {ext}"]
            )

    def dwg_to_dxf(self, dwg_path: str, output_dxf: str = None) -> str:
        """DWG → DXF 转换
        
        优先使用 ezdwg（纯Python），失败时返回空字符串。
        返回输出DXF路径，失败返回空字符串。
        """
        if output_dxf is None:
            output_dxf = os.path.splitext(dwg_path)[0] + ".dxf"
        
        # Method 1: ezdwg (pure Python)
        try:
            import ezdwg
            import ezdwg.convert as _cvt
            doc = ezdwg.read(dwg_path)
            _cvt.to_dxf(doc, output_dxf)
            if os.path.exists(output_dxf):
                return output_dxf
        except Exception:
            pass
        
        # Method 2: libredwg Node.js WASM (fallback)
        try:
            project_root = "/mnt/d/OpenClawDataworkspace/Projects/engineering-management-agent"
            wasm_dir = os.path.join(project_root, "node_modules/@mlightcad/libredwg-web/wasm")
            if os.path.exists(wasm_dir):
                import subprocess
                script = (
                    "import {LibreDwg} from '@mlightcad/libredwg-web';"
                    "import {readFileSync,writeFileSync} from 'fs';"
                    f"const buf=readFileSync('{dwg_path}');"
                    "const ld=LibreDwg.create();"
                    "ld.dwg_read_data(buf);"
                    "const dxf=ld.dwg_write_dxf();"
                    f"writeFileSync('{output_dxf}',Buffer.from(dxf));"
                    "console.log('OK');"
                )
                result = subprocess.run(
                    ["node", "-e", script],
                    capture_output=True, text=True, timeout=60,
                    cwd=project_root
                )
                if result.returncode == 0 and os.path.exists(output_dxf):
                    return output_dxf
        except Exception:
            pass
        
        return ""

    def parse_with_ai(self, file_path: str) -> dict:
        """
        解析图纸并进行AI增强分析

        返回完整结果，包含：
        - parse_result: 基础解析结果
        - drawing_type: AI图纸类型识别
        - layer_analysis: 图层语义分析
        - project_info: 工程信息提取
        - design_principles: 设计原则
        - construction_requirements: 施工要求
        - material_specs: 材料规格
        - design_params: 设计参数
        """
        # Step 1: 基础解析
        result = self.parse(file_path)
        if not result.success:
            return {
                'success': False,
                'errors': result.errors,
                'file_path': file_path,
            }

        # Step 2: AI分析（如果启用）
        if not self.enable_ai:
            return {
                'success': True,
                'parse_result': result,
                'ai_analysis': None,
            }

        # 延迟导入AI模块（避免启动时依赖）
        from .ai.classifier import smart_classify
        from .ai.inference import (
            analyze_layers,
            infer_design_principles,
            infer_construction_requirements,
        )
        from .ai.extractor import (
            smart_extract,
            extract_material_specs,
            extract_design_params,
        )

        file_name = Path(file_path).name
        layers = [l.name for l in result.layers]
        raw_text = result.raw_text

        # 图纸类型识别
        drawing_type = smart_classify(
            layers=layers,
            blocks=[],  # TODO: 从解析结果中提取blocks
            raw_text=raw_text,
            file_name=file_name,
            use_llm=self.use_llm,
        )

        # 图层语义分析
        layer_analysis = analyze_layers(layers)

        # 工程信息提取
        project_info = smart_extract(
            raw_text=raw_text,
            file_name=file_name,
            drawing_type=drawing_type.get('primary', ''),
            layers=layers,
            use_llm=self.use_llm,
        )

        # 设计原则
        design_principles = infer_design_principles(
            drawing_type.get('primary', ''),
            layers,
            raw_text,
        )

        # 施工要求
        construction_requirements = infer_construction_requirements(
            drawing_type.get('primary', ''),
            layers,
            raw_text,
        )

        # 材料规格
        material_specs = extract_material_specs(raw_text)

        # 设计参数
        design_params = extract_design_params(raw_text)

        return {
            'success': True,
            'file_path': file_path,
            'file_name': file_name,
            'file_type': result.file_type.value,
            'parse_result': {
                'layer_count': len(result.layers),
                'entity_count': len(result.entities),
                'raw_text_length': len(result.raw_text),
                'layers': [
                    {'name': l.name, 'color': l.color, 'visible': l.visible}
                    for l in result.layers
                ],
                'entities': [
                    {'type': e.type, 'layer': e.layer}
                    for e in result.entities
                ],
                'metadata': result.metadata,
                'ocr_confidence': result.ocr_confidence,
            },
            'ai_analysis': {
                'drawing_type': drawing_type,
                'layer_analysis': layer_analysis,
                'project_info': project_info,
                'design_principles': design_principles,
                'construction_requirements': construction_requirements,
                'material_specs': material_specs,
                'design_params': design_params,
            },
        }

    def batch_parse(self, directory: str, pattern: str = "*.*") -> List[ParseResult]:
        """批量解析目录中的图纸文件"""
        results = []
        path = Path(directory)
        for file_path in path.glob(pattern):
            if file_path.is_file():
                result = self.parse(str(file_path))
                results.append(result)
        return results
