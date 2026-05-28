"""src/blueprint/ - EMA图纸解析模块（自研）"""

from .core import BlueprintParser
from .types import FileType, EntityInfo, LayerInfo, ParseResult

# AI模块（延迟导入，避免启动时依赖LLM）
# from .ai.classifier import smart_classify, batch_classify
# from .ai.inference import analyze_blueprint, infer_drawing_type
# from .ai.extractor import smart_extract, extract_material_specs, extract_design_params

__all__ = [
    "BlueprintParser",
    "FileType",
    "EntityInfo",
    "LayerInfo",
    "ParseResult",
]
