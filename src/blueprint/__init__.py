"""
src/blueprint/__init__.py - EMA 图纸解析模块

Phase 7+1-A: 基础解析能力迁移
从 blueprint-ai 迁移并增强，作为 TechRdAgent 核心能力。

子模块:
  parsers/   - 文件解析器 (PDF/DWG/DXF)
  ai/        - AI推理 (图纸分类/信息提取)
  review/    - 智能审查 (国标规则引擎)
  editor/    - 图纸编辑 (DXF编辑)
  documents/ - 工程文档生成
  vector/    - 向量搜索 (ChromaDB)
"""

from .types import FileType, EntityInfo, LayerInfo, ParseResult
from .core import BlueprintParser

__all__ = [
    "FileType",
    "EntityInfo",
    "LayerInfo",
    "ParseResult",
    "BlueprintParser",
]
