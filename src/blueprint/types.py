"""
src/blueprint/types.py - 共享数据类型

从 blueprint-ai/bp_types.py 迁移，保持API兼容。
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum


class FileType(Enum):
    """支持的图纸文件类型"""
    PDF = "pdf"
    DWG = "dwg"
    DXF = "dxf"
    UNKNOWN = "unknown"


@dataclass
class EntityInfo:
    """图纸实体信息"""
    type: str
    layer: str
    text: Optional[str] = None
    handle: Optional[str] = None
    geometry: Optional[Dict] = None
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LayerInfo:
    """图层信息"""
    name: str
    color: Optional[str] = None
    line_type: Optional[str] = None
    visible: bool = True


@dataclass
class ParseResult:
    """解析结果"""
    success: bool
    file_path: str
    file_type: FileType
    raw_text: str = ""
    entities: List[EntityInfo] = field(default_factory=list)
    layers: List[LayerInfo] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    ocr_confidence: Optional[float] = None

    def __str__(self):
        return (f"<ParseResult: {self.file_type.value} | "
                f"{len(self.entities)} entities | {len(self.layers)} layers | "
                f"text: {len(self.raw_text)} chars>")
