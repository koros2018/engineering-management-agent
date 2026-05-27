"""
src/blueprint/core.py - 统一图纸解析器

从 blueprint-ai/core.py 迁移。
自动识别文件类型并路由到对应解析器。
"""

import os
from pathlib import Path
from typing import List

from .types import FileType, EntityInfo, LayerInfo, ParseResult
from .parsers.pdf_parser import PDFParser
from .parsers.dxf_parser import DXFParser
from .parsers.dwg_parser import DWGParser


class BlueprintParser:
    """
    EMA 统一图纸解析器

    支持 PDF / DWG / DXF 格式
    自动识别文件类型，路由到对应解析器
    """

    EXT_TO_TYPE = {
        '.pdf': FileType.PDF,
        '.dwg': FileType.DWG,
        '.dxf': FileType.DXF,
    }

    def __init__(self, use_ocr: bool = True, ocr_dpi: int = 300):
        self.use_ocr = use_ocr
        self.ocr_dpi = ocr_dpi
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

    def batch_parse(self, directory: str, pattern: str = "*.*") -> List[ParseResult]:
        """批量解析目录中的图纸文件"""
        results = []
        path = Path(directory)
        for file_path in path.glob(pattern):
            if file_path.is_file():
                result = self.parse(str(file_path))
                results.append(result)
        return results
