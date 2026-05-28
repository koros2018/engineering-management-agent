"""src/blueprint/ - EMA图纸解析模块（自研）"""

from .core import BlueprintParser
from .types import FileType, EntityInfo, LayerInfo, ParseResult

# AI模块
from .ai.classifier import smart_classify, batch_classify
from .ai.inference import analyze_blueprint, infer_drawing_type
from .ai.extractor import smart_extract, extract_material_specs, extract_design_params

# 审查模块
from .review.engine import (
    review_drawing,
    review_analysis,
    quick_review,
    review_summary_text,
    Severity,
)

# 文档生成模块
from .documents.generator import (
    generate_full_document_set,
    generate_design_description,
    generate_technical_disclosure,
    generate_quantity_list,
    generate_change_request,
    generate_bid_document,
)

__all__ = [
    "BlueprintParser",
    "FileType",
    "EntityInfo",
    "LayerInfo",
    "ParseResult",
    # AI
    "smart_classify",
    "batch_classify",
    "analyze_blueprint",
    "infer_drawing_type",
    "smart_extract",
    "extract_material_specs",
    "extract_design_params",
    # 审查
    "review_drawing",
    "review_analysis",
    "quick_review",
    "review_summary_text",
    "Severity",
    # 文档
    "generate_full_document_set",
    "generate_design_description",
    "generate_technical_disclosure",
    "generate_quantity_list",
    "generate_change_request",
    "generate_bid_document",
]
