"""EMA规范知识库facade层 - 从blueprint-ai/specs.py迁移 (Phase 7+1-C, 2026-05-28)

中国建筑/结构/机电等规范的关键字映射，用于从图纸图层/块名推断设计依据的规范条目。
实现已迁移至 spec_mapper.py，本模块保持向后兼容。
"""

from typing import Dict, List, Any
try:
    from .spec_mapper import (
        LAYER_TO_SPECS,
        BLOCK_TO_COMPONENT,
        lookup_specs_for_layer,
        lookup_component_info,
        get_layer_category,
    )
except ImportError:
    from spec_mapper import (
        LAYER_TO_SPECS,
        BLOCK_TO_COMPONENT,
        lookup_specs_for_layer,
        lookup_component_info,
        get_layer_category,
    )  # type: ignore

__all__ = [
    'LAYER_TO_SPECS',
    'BLOCK_TO_COMPONENT',
    'lookup_specs_for_layer',
    'lookup_component_info',
    'get_layer_category',
]
